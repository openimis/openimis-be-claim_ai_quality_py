import logging
import traceback

from api_fhir_r4.serializers import ClaimSerializer
from claim.models import Claim
from claim_ai_quality.apps import ClaimAiQualityConfig
from claim_ai_quality.fhir import ClaimBundleConverter
from claim_ai_quality.communication_interface.rest_api.response_handler import RestResponseEvaluationHandler
from claim_ai_quality.communication_interface.rest_api.rest_client import ClaimRestApiRequestClient
from claim_ai_quality.models import ClaimBundleEvaluationResult
from claim_ai_quality.utils import get_eligible_claims_bundle_iterator
from core import TimeUtils

logger = logging.getLogger(__name__)


class RestCommunicationException(Exception):
    pass


class RestCommunicationInterface:
    @classmethod
    def default_interface(cls):
        return cls(ClaimBundleConverter(ClaimSerializer()))

    def __init__(self, fhir_converter: ClaimBundleConverter, user=None):
        self.fhir_converter = fhir_converter
        self.user = user
        self.rest_client = ClaimRestApiRequestClient()
        username = self.user.username if self.user else None
        self.response_handler = RestResponseEvaluationHandler(self.fhir_converter, username=username)

    def send_all(self, wait_for_response=False):
        data = self._get_imis_data()  # generator of paginated data
        bundles = []
        while True:
            next_bundle = self._get_from_iterator(data)
            if next_bundle:
                bundles.append(self.send_bundle(next_bundle, wait_for_response))
                logger.info(F"Sent bundle of size {len(next_bundle)}")
            else:
                break
        return bundles

    def send_bundle(self, bundle, wait_for_response: bool = False):
        response_json = self._send_data_bundle(bundle, wait_for_response)
        if wait_for_response:
            result = self.response_handler.update_claims_with_evaluation(response_json)
        else:
            result = self.response_handler.save_initial_claim_bundle_evaluation_result(response_json)
            self._run_pull_evaluation_task(result)
        return result

    def pull_result_for_all_not_evaluated_bundles(self):
        identifiers = ClaimBundleEvaluationResult.objects\
            .not_evaluated_bundles()\
            .values_list('evaluation_hash', flat=True)

        bundles = [
            self.pull_evaluation_and_update_claims(identifier) for identifier in identifiers
        ]
        return bundles

    def pull_evaluation_and_update_claims(self, evaluation_hash):
        response_json = self.rest_client.get_claim_bundle(evaluation_hash)
        if self._confirm_bundle_evaluated(response_json):
            return self.response_handler.update_claims_with_evaluation(response_json)
        else:
            logger.info(f"No AI Evaluated claims in Response. Bundle ({evaluation_hash}) is not evaluated")
        return None

    def _send_data_bundle(self, bundle, wait_for_response):
        try:
            self._save_request_date(bundle)
            fhir_obj = self.fhir_converter.build_claim_bundle(bundle)
            return self.rest_client.send_claim_bundle(fhir_obj, wait_for_response)
        except Exception as e:
            logger.error(F"Error occurred during sending data bundle for evaluation, error: {e}")
            logger.debug(traceback.format_exc())
            raise RestCommunicationException(F'Sending data for AI evaluation has failed, reason:\n{e}') from e

    def _get_from_iterator(self, queryset):
        chunk = next(queryset, None)
        if not chunk:
            return None
        return list(chunk)

    def _get_imis_data(self):
        return get_eligible_claims_bundle_iterator()

    def _save_request_date(self, bundle):
        # Expected to have json_ext fields
        for b in bundle:
            b.json_ext['claim_ai_quality']['request_time'] = str(TimeUtils.now())
        Claim.objects.bulk_update(bundle, ['json_ext'])

    def _confirm_bundle_evaluated(self, bundle):
        for entry in bundle['entry']:
            for item in entry["resource"]["item"]:
                adjudication = item["adjudication"][0]
                category = str(adjudication["category"]["coding"][0]["code"])
                value = adjudication["reason"]["coding"][0]["code"]
                # Value == -2 item/service adjudication is undefined
                if category == ClaimAiQualityConfig.reason_rejected_by_ai_code and value != '-2':
                    return True
        return False

    @classmethod
    def _run_pull_evaluation_task(cls, result: ClaimBundleEvaluationResult):
        # TODO: Replace this with subscriptions based pull when available
        from claim_ai_quality.tasks import pull_data_for_evaluation
        PULLING_DATA_TASK = pull_data_for_evaluation
        PULLING_DATA_TASK.delay(result.evaluation_hash, )
        pass
