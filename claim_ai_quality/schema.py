import logging
import traceback

import graphene
from django.dispatch import dispatcher

from claim.gql_mutations import SubmitClaimsMutation
from claim.models import Claim
from claim_ai_quality.ai_evaluation.mutation_evaluation import AiMutationValidationException
from core.models import User
from core.schema import signal_mutation_module_after_mutating, signal_mutation_module_validate
from .ai_evaluation import ClaimEvaluationOrganizer
from .apps import ClaimAiQualityConfig
from .gql_mutations import EvaluateByAIMutation
from .models import ClaimAiQualityMutation
from .utils import add_json_ext_to_all_submitted_claims

logger = logging.getLogger(__name__)


class Mutation(graphene.ObjectType):
    send_claims_for_ai_evaluation = EvaluateByAIMutation.Field()


def _get_uuids(payload):
    uuids = payload['data'].get('uuids', [])
    if not uuids:
        uuid = payload['data'].get('claim_uuid', None)
        uuids = [uuid] if uuid else []
    return uuids


def on_claim_ai_evaluation_mutation(sender, **kwargs):
    uuids = _get_uuids(kwargs)
    impacted_claims = Claim.objects.filter(uuid__in=uuids).all()
    for claim in impacted_claims:
        ClaimAiQualityMutation.objects.create(claim=claim, mutation_id=kwargs['mutation_log_id'])
    return []


def on_claim_submit_mutation(sender: dispatcher.Signal, **kwargs):
    mutation_type = sender._mutation_class
    if not mutation_type == SubmitClaimsMutation._mutation_class:
        return []

    uuids = _get_uuids(kwargs)
    claims = Claim.objects.filter(uuid__in=uuids)
    add_json_ext_to_all_submitted_claims(claims)
    if ClaimAiQualityConfig.event_based_activation:
        ClaimEvaluationOrganizer.evaluate_selected_claims(claims)
    return []


def after_claim_ai_evaluation_validation(sender: dispatcher.Signal, **kwargs):
    def _send(claims_):
        try:
            ClaimEvaluationOrganizer.evaluate_selected_claims(claims_)
        except AiMutationValidationException as exc:
            logger.error(F"AiMutationValidationException exception occurred during AI Evaluation Mutation, error: {exc}")
            return [{'message': str(exc.message), 'detail': str(exc)}]
        except User.DoesNotExist as a:
            logger.error(f"User with username {ClaimAiQualityConfig.claim_ai_username} does not exit. "
                         f"User with this username is required to perform evaluation related operations on database.")
            raise a
        except Exception as e:
            logger.error(F"Unknown exception occurred during AI Evaluation Mutation, error: {e}")
            logger.debug(traceback.format_exc())
            return [{'message': str(e)}]
        return []

    mutation_type = sender._mutation_class
    if not mutation_type == EvaluateByAIMutation._mutation_class:
        return []

    uuids = _get_uuids(kwargs)
    claims = Claim.objects.filter(uuid__in=uuids)
    logger.info(F"Claims evaluated: {[claim.uuid for claim in claims]}")
    return _send(claims)


def bind_signals():
    signal_mutation_module_validate["claim_ai_quality"].connect(on_claim_ai_evaluation_mutation)
   # signal_mutation_module_after_mutating["claim_ai_quality"].connect(after_claim_ai_evaluation_validation)
    signal_mutation_module_after_mutating["claim"].connect(on_claim_submit_mutation)
