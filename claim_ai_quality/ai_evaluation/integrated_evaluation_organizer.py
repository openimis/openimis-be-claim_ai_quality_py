import logging

from claim.models import Claim
from claim_ai.evaluation.converters.r4_fhir_resources.fhir_response_builders import ClaimResponseBuilderFactory
from claim_ai.evaluation.converters.r4_fhir_resources.fhir_response_builders.base_builders.bundle_builders import \
    ClaimBundleEvaluationClaimResponseBundleBuilder
from claim_ai.rest_api.claim_evaluation.claim_bundle_evaluation_manager import ClaimBundleEvaluationManager
from claim_ai_quality.ai_evaluation.mutation_evaluation import EvaluationFromMutation
from claim_ai_quality.apps import ClaimAiQualityConfig
from claim_ai_quality.fhir._claim_response_converter import ClaimResponseConverter
from claim_ai_quality.models import ClaimBundleEvaluationResult, BundleClaimEvaluationResult
from claim_ai_quality.utils import reset_sent_but_not_evaluated_claims, add_json_ext_to_all_submitted_claims, \
    get_eligible_claims_bundle_iterator
from core import TimeUtils
from core.models import User

logger = logging.getLogger(__name__)


class IntegratedClaimAIEvaluationOrganizer:
    EVALUATION_BUNDLE_MANAGER = ClaimBundleEvaluationManager(
        user=User.objects.get(t_user__username=ClaimAiQualityConfig.claim_ai_username)
    )
    CLAIM_RESPONSE_CONVERTER = ClaimResponseConverter()
    BUNDLE_CONVERTER = ClaimBundleEvaluationClaimResponseBundleBuilder(ClaimResponseBuilderFactory())

    @classmethod
    def evaluate_claims_from_mutation(cls, user, **data):
        """
        Evaluate selected using data sent with GraphQL mutation.
        """
        return EvaluationFromMutation(cls).evaluate(user, **data)

    @classmethod
    def evaluate_all_eligible_claims(cls):
        """
        Send all claims stored in system that are eligible for AI Evaluation.
        """
        logger.info("Evaluation from integrated solution triggered.")
        reset_sent_but_not_evaluated_claims()
        add_json_ext_to_all_submitted_claims()
        iterator = get_eligible_claims_bundle_iterator()
        bundles = []
        while True:
            next_bundle = cls._get_from_iterator(iterator)
            if next_bundle:
                bundles.append(cls._evaluate(next_bundle))
            else:
                break
        return bundles

    @classmethod
    def _get_from_iterator(cls, queryset):
        chunk = next(queryset, None)
        if not chunk:
            return None
        return list(chunk)

    @classmethod
    def evaluate_selected_claims(cls, claims):
        """
        Send bundle of claims for evaluation. Created for event based evaluation.
        """
        logger.info("Evaluation from integrated solution triggered.")
        add_json_ext_to_all_submitted_claims(claims)
        claims_for_evaluation = []
        for c in claims:
            if c.status == Claim.STATUS_CHECKED:
                c.json_ext['claim_ai_quality']['request_time'] = str(TimeUtils.now())
                c.save()
                claims_for_evaluation.append(c)
            else:
                logger.info(F"Claim {c} will not be evaluated, it's not in checked state")

        reset_sent_but_not_evaluated_claims()
        cls._evaluate(claims_for_evaluation)

    @classmethod
    def pull_data_for_not_evaluated_bundles(cls):
        """
        Pull data for all bundles that don't have evaluation result.
        By default, bundle is sent for evaluation and queued for evaluation.
        Response is not immediate and client is not waiting for a response from the server and
        results have to be pulled from server.
        """
        raise NotImplementedError("Pulling data unavailable.Evaluation is done in place instance")

    @classmethod
    def pull_data_for_bundle(cls, bundle_hash):
        """
        Pull data for specific bundle of claims.
        """
        raise NotImplementedError("Pulling data unavailable. Evaluation is done in place instance")

    @classmethod
    def _evaluate(cls, next_bundle):
        evaluation_data = cls.EVALUATION_BUNDLE_MANAGER.create_idle_evaluation_bundle(next_bundle)
        evaluation_info = cls.EVALUATION_BUNDLE_MANAGER.evaluate_bundle(evaluation_data)
        fhir_format = cls.BUNDLE_CONVERTER.build_fhir_bundle_dict(evaluation_info, None)
        # TODO: Add direct update from bundle instead of fhir
        for x in fhir_format['entry']:
            cls.CLAIM_RESPONSE_CONVERTER.update_claim(x['resource'].dict())
        return cls._create_bundle_for_claims(
            evaluation_data.evaluation_hash,
            [x.claim for x in evaluation_info.claims.all().prefetch_related('claim')])

    @classmethod
    def _create_bundle_for_claims(cls, bundle_evaluation_identifier, claims):
        bundle = ClaimBundleEvaluationResult(evaluation_hash=bundle_evaluation_identifier)
        bundle.save(username=ClaimAiQualityConfig.claim_ai_username)
        for claim in claims:
            next_ = BundleClaimEvaluationResult(claim=claim, bundle_evaluation=bundle)
            next_.save()
        return bundle
