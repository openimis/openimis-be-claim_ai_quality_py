from api_fhir_r4.serializers import ClaimSerializer
from claim_ai_quality.ai_evaluation.mutation_evaluation import EvaluationFromMutation
from claim_ai_quality.fhir import ClaimBundleConverter
from claim_ai_quality.communication_interface.rest_api.restCommunicationInterface import RestCommunicationInterface
from ._rest_api.eligible_claims_evaluation import RestApiAllEligibleClaimsEvaluation, \
    RestApiEventBasedEvaluation


class RestAIEvaluationOrganizer:
    _API_INTERFACE = RestCommunicationInterface(ClaimBundleConverter(ClaimSerializer()))

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
        return RestApiAllEligibleClaimsEvaluation\
            .evaluate(communication_interface=cls._API_INTERFACE, wait_for_response=True)

    @classmethod
    def evaluate_selected_claims(cls, claims):
        """
        Send bundle of claims for evaluation. Created for event based evaluation.
        """
        return RestApiEventBasedEvaluation\
            .evaluate(submitted_claims=claims, communication_interface=cls._API_INTERFACE, wait_for_response=True)

    @classmethod
    def pull_data_for_not_evaluated_bundles(cls):
        """
        Pull data for all bundles that don't have evaluation result.
        By default, bundle is sent for evaluation and queued for evaluation.
        Response is not immediate and client is not waiting for a response from the server and
        results have to be pulled from server.
        """
        return cls._API_INTERFACE.pull_result_for_all_not_evaluated_bundles()

    @classmethod
    def pull_data_for_bundle(cls, bundle_hash):
        """
        Pull data for specific bundle of claims.
        """
        return cls._API_INTERFACE.pull_evaluation_and_update_claims(bundle_hash)
