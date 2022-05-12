import logging
import traceback

from django.utils.translation import gettext as _
from graphql_jwt.exceptions import PermissionDenied

from claim.apps import ClaimConfig
from claim.models import Claim

logger = logging.getLogger(__name__)


class AiMutationValidationException(Exception):
    def __init__(self, mutated_object, invalidation_reason):
        self.mutated_object = mutated_object
        self.message = invalidation_reason


class EvaluationFromMutation:
    def __init__(self, evaluation_organizer):
        self._evaluation_organizer = evaluation_organizer

    def evaluate(self, *args, **kwargs):
        """
        Method used for creating mutation log and handling request.
        Actual evaluation is called in signal after EvaluateByAIMutation.send_claims_to_evaluation(claims)
        """
        logger.debug(F'Evaluating bundle using manual evaluation execution, bundle: {kwargs}')
        return self._evaluate_claims_from_mutation(*args, **kwargs)

    def _evaluate_claims_from_mutation(self, user, **data):
        if not user.has_perms(ClaimConfig.gql_mutation_submit_claims_perms):
            logger.info(F"Unauthorized user {user} attempted to evaluate claim bundle, permission denied raised.")
            raise PermissionDenied(_("unauthorized"))

        try:
            claims = []
            for claim_uuid in data["uuids"]:
                claim = Claim.objects.filter(uuid=claim_uuid, validity_to__isnull=True).first()
                if not claim:
                    self._raise_claim_not_exists_exception(claim_uuid)
                self._validate_claim_for_evaluation(claim)
                claims.append(claim)
            logger.debug(F"Claims to be send using mutation: {claims}")
            self._send_claims(claims)
        except AiMutationValidationException as exc:
            logger.error(
                F"AiMutationValidationException exception occurred during AI Evaluation Mutation, error: {exc}")
            return [{'message': str(exc.message), 'detail': str(exc)}]
        except Exception as e:
            logger.error(F"Unknown exception occurred during AI Evaluation Mutation, error: {e}")
            logger.debug(traceback.format_exc())
            return [{'message': str(e)}]

        logger.debug("EvaluateByAIMutation: claim evaluation done.")
        return []

    @classmethod
    def _validate_claim_for_evaluation(cls, claim):
        if claim.status != Claim.STATUS_CHECKED:
            cls._raise_invalid_status_exception(claim)

    @classmethod
    def _raise_invalid_status_exception(cls, claim):
        raise AiMutationValidationException(
            claim.code,
            cls._build_claim_invalid_status_err_msg(claim)
        )

    @classmethod
    def _raise_claim_not_exists_exception(cls, claim_uuid):
        raise AiMutationValidationException(
            claim_uuid,
            cls._build_claim_not_exits_uuid_err_msg(claim_uuid)
        )

    @classmethod
    def _build_claim_not_exits_uuid_err_msg(cls, claim_uuid: str):
        return _("Claim %(id)s does not exit") % {'id': claim_uuid}

    @classmethod
    def _build_claim_invalid_status_err_msg(cls, claim: Claim):
        return _("Claim %(id)s cannot be evaluated as it's not in checked state") % {'id': claim.code}

    @classmethod
    def _ai_evaluation_err_msg(cls, claim_codes, ai_connection_error: str):
        return _("Exception occurred during connecting with AI server: %(ai_connection_error)s") % \
               {'ai_connection_error': ai_connection_error, 'claim_codes': str(claim_codes)}

    def _send_claims(self, claims_):
        self._evaluation_organizer.evaluate_selected_claims(claims_)
        return []
