import logging
import uuid
from typing import Union

from django.db import transaction

from claim_ai_quality.apps import ClaimAiQualityConfig
from claim_ai_quality.models import ClaimBundleEvaluationResult, BundleClaimEvaluationResult
from core.datetimes.ad_datetime import datetime

logger = logging.getLogger(__name__)


class RestResponseEvaluationHandler:
    def __init__(self, fhir_converter, username=None):
        self.username = username or ClaimAiQualityConfig.claim_ai_username
        self.fhir_converter = fhir_converter

    @transaction.atomic
    def update_claims_with_evaluation(self, fhir_bundle_response_json: dict) -> ClaimBundleEvaluationResult:
        bundle_evaluation_identifier = self._get_bundle_identifier(fhir_bundle_response_json)
        update_result = self.fhir_converter.update_claims_by_response_bundle(fhir_bundle_response_json)
        claims = [claim for claim in update_result if claim]  # Update puts None as invalid claim updates
        return self._save_claim_bundle_evaluation_result(claims, bundle_evaluation_identifier)

    def save_initial_claim_bundle_evaluation_result(self, fhir_bundle_response_json: dict) \
            -> ClaimBundleEvaluationResult:
        """
        For claims that were sent for evaluation but evaluation was not yet done.
        """
        claims = self.fhir_converter.get_claims_from_response_bundle(fhir_bundle_response_json)
        bundle_evaluation_identifier = self._get_bundle_identifier(fhir_bundle_response_json)
        return self._create_init_bundle_for_claims(bundle_evaluation_identifier, claims)

    def _get_bundle_identifier(self, fhir_bundle_response_json) -> Union[uuid.UUID, str]:
        return fhir_bundle_response_json['identifier']['value']

    def _save_claim_bundle_evaluation_result(self, claims, bundle_evaluation_identifier) -> ClaimBundleEvaluationResult:
        """
        For evaluated claims.
        """
        bundle_query = ClaimBundleEvaluationResult.objects.filter(evaluation_hash=bundle_evaluation_identifier)

        if bundle_query.exists():
            bundle = bundle_query.get()
            if [claim.claim for claim in bundle.claims.all()] != claims:
                logger.warning(
                    f"Initial collection of claims in claim bundle {bundle_evaluation_identifier} "
                    f"differs from the claim collection coming from the response bundle.")
        else:
            logger.info(
                "New ClaimBundleEvaluationResult created directly from evaluation response."
                "It should be created when given bundle is sent for evaluation and then updated with result.")
            bundle = self._create_init_bundle_for_claims(bundle_evaluation_identifier, claims)

        bundle.response_time = datetime.now()
        bundle.status = ClaimBundleEvaluationResult.BundleEvaluationStatus.FINISHED
        bundle.save(username=self.username)
        return bundle

    def _create_init_bundle_for_claims(self, bundle_evaluation_identifier, claims):
        bundle = ClaimBundleEvaluationResult(evaluation_hash=bundle_evaluation_identifier)
        bundle.save(username=self.username)

        for claim in claims:
            next_ = BundleClaimEvaluationResult(claim=claim, bundle_evaluation=bundle)
            next_.save()
        return bundle
