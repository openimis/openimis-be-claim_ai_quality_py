import logging

from django.db.models import QuerySet

from claim.models import Claim
from claim_ai_quality.communication_interface.rest_api.restCommunicationInterface import RestCommunicationInterface
from claim_ai_quality.utils import reset_sent_but_not_evaluated_claims, add_json_ext_to_all_submitted_claims

logger = logging.getLogger(__name__)


class RestApiAllEligibleClaimsEvaluation:
    @classmethod
    def evaluate(cls, *args, **kwargs):
        reset_sent_but_not_evaluated_claims()
        add_json_ext_to_all_submitted_claims()
        interface = kwargs.get('communication_interface') or cls._get_default_interface()
        wait_for_response = kwargs.get('wait_for_response') or False
        return cls._send_all_eligible_claims_claims(interface, wait_for_response)

    @classmethod
    def _send_all_eligible_claims_claims(cls, interface, wait_for_response):
        return interface.send_all(wait_for_response)

    @classmethod
    def _get_default_interface(cls):
        logger.warning("RestApiAllEligibleClaimsEvaluation.evaluate: Using default RestCommunicationInterface.")
        return RestCommunicationInterface.default_interface()


class RestApiEventBasedEvaluation:
    @classmethod
    def evaluate(cls, *args, **kwargs):
        submitted_claims = kwargs.get('submitted_claims')
        if not submitted_claims:
            raise ValueError(
                "Input has to provide non empty `submitted_claims` argument with Iterable of claim objects")
        interface = kwargs.get('communication_interface') or cls._get_default_interface()
        wait_for_response = kwargs.get('wait_for_response') or False
        add_json_ext_to_all_submitted_claims(submitted_claims)
        cls._evaluate_checked_claims_on_event_activation(submitted_claims, interface, wait_for_response)

    @classmethod
    def _evaluate_checked_claims_on_event_activation(cls, claims, interface, wait_for_response):
        claims_for_evaluation = []
        if isinstance(claims, QuerySet):
            claims = claims.all()
        for c in claims:
            if c.status == Claim.STATUS_CHECKED:
                claims_for_evaluation.append(c)

        # TODO: Use celery instead of threading
        return cls._send_submitted_claims(claims_for_evaluation, interface, wait_for_response)

    @classmethod
    def _send_submitted_claims(cls, submitted_claims_bundle, interface, wait_for_response):
        if not submitted_claims_bundle:
            logger.info("No claims submitted for AI evaluation")
            return
        reset_sent_but_not_evaluated_claims()
        interface = interface or cls._get_default_interface()
        return interface.send_bundle(submitted_claims_bundle, wait_for_response)

    @classmethod
    def _get_default_interface(cls):
        logger.warning("RestApiAllEligibleClaimsEvaluation.evaluate: Using default RestCommunicationInterface.")
        return RestCommunicationInterface.default_interface()
