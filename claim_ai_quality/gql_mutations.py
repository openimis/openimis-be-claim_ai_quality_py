import asyncio
import logging
import threading

import graphene
import traceback
from core.schema import OpenIMISMutation
from core.gql.gql_mutations import MutationValidationException

from claim.apps import ClaimConfig
from claim.models import Claim
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from claim_ai_quality import utils
from claim_ai_quality.ai_evaluation import create_base_communication_interface, send_claims as send_to_ai_server

logger = logging.getLogger(__name__)


class AiMutationValidationException(Exception):
    def __init__(self, mutated_object, invalidation_reason):
        self.mutated_object = mutated_object
        self.message = invalidation_reason


class EvaluateByAIMutation(OpenIMISMutation):
    _mutation_module = "claim_ai_quality"
    _mutation_class = "EvaluateByAIMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(ClaimConfig.gql_mutation_submit_claims_perms):
            raise PermissionDenied(_("unauthorized"))

        errors = []
        try:
            _evaluate_claims(user, **data)
        except AiMutationValidationException as exc:
            return [{
                'message': str(exc.message),
                'detail': str(exc)
            }]

        except Exception as e:
            return [{
                'message': str(e)
            }]

        logger.debug("EvaluateByAIMutation: claim evaluation done, errors: %s", len(errors))
        return []


def _evaluate_claims(user, **data):
    claims = []
    for claim_uuid in data["uuids"]:
        claim = _get_claim_by_uuid(claim_uuid)
        if not claim:
            _raise_claim_not_exists_exception(claim_uuid)

        _validate_claim_for_evaluation(claim)
        claims.append(claim)

    # Actual evaluation is called in signal after EvaluateByAIMutation
    # send_claims_to_evaluation(claims)


def send_claims_to_evaluation(claims):
    try:
        for claim in claims:
            __reset_claim_ai_quality_json(claim)
        __send_to_websocket(claims)
    except AiMutationValidationException as exc:
        return [{
            'message': str(exc.message),
            'detail': str(exc)
        }]
    except Exception as e:
        logger.exception(F"Unknown exception ocurred during AI Evaluation Mutation, error: {e}")
        logger.debug(traceback.format_exc())
        return [{'message': str(e)}]

    return []


def __send_to_websocket(claims):
    try:
        communication_interface = create_base_communication_interface()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        asyncio.get_event_loop() \
            .run_until_complete(send_to_ai_server(communication_interface, claims))
    except Exception as exc:
        _raise_ai_server_exception(claims, error_msg=exc)


def _validate_claim_for_evaluation(claim):
    if claim.status != Claim.STATUS_CHECKED:
        _raise_invalid_status_exception(claim)


def _claim_not_exits_msg(claim_uuid):
    return {
        'title': claim_uuid,
        'list': []
    }


def _get_claim_by_uuid(claim_uuid):
    return Claim.objects.filter(
        uuid=claim_uuid,
        validity_to__isnull=True) \
        .first()


def __reset_claim_ai_quality_json(claim):
    if not claim.json_ext:
        claim.json_ext = {}
    claim.json_ext['claim_ai_quality'] = utils.get_base_claim_ai_json_extension()
    claim.save()


def _raise_claim_not_exists_exception(claim_uuid):
    raise AiMutationValidationException(
        claim_uuid,
        _build_claim_not_exits_uuid_err_msg(claim_uuid)
    )


def _raise_invalid_status_exception(claim):
    raise AiMutationValidationException(
        claim.code,
        _build_claim_invalid_status_err_msg(claim)
    )


def _raise_ai_server_exception(claims, error_msg):
    codes = [claim.code for claim in claims]
    raise AiMutationValidationException(
        'Claim AI Exception', _ai_evaluation_err_msg(codes, error_msg)
    )


def _build_claim_not_exits_uuid_err_msg(claim_uuid: str):
    return _("Claim %(id)s does not exit") % {'id': claim_uuid}


def _build_claim_invalid_status_err_msg(claim: Claim):
    return _("Claim %(id)s cannot be evaluated as it's not in checked state") % {'id': claim.code}


def _ai_evaluation_err_msg(claim_codes,  ai_connection_error: str):
    return _("Exception occurred during connecting with AI server: %(ai_connection_error)s") % \
                   {'ai_connection_error': ai_connection_error, 'claim_codes': str(claim_codes)}
