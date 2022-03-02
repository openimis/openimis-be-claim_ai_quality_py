import decimal
from unittest import mock
from unittest.mock import MagicMock, PropertyMock, call
from uuid import UUID

import orjson
from django.test import testcases
from graphene import Schema
from graphene.test import Client

from api_fhir_r4.serializers import ClaimSerializer
from claim import schema as claim_schema
from claim.models import Claim, ClaimItem, ClaimService
from claim_ai_quality import schema as claim_ai_schema
from claim_ai_quality.ai_evaluation.rest_organizer import RestAIEvaluationOrganizer
from claim_ai_quality.apps import ClaimAiQualityConfig
from claim_ai_quality.fhir import ClaimBundleConverter
from claim_ai_quality.schema import bind_signals
from claim_ai_quality.tests.rest_api.requests_response_mock import RequestsMocked
from claim_ai_quality.tests.rest_api.utils import ClaimAITestInitialDataGenerator
from core.models import MutationLog


class TestRestAIEvaluationOrganizer(ClaimAITestInitialDataGenerator, testcases.TestCase):

    @classmethod
    def make_claim_accepted(cls, *args, **kwargs):
        claim = Claim.objects.get(uuid=cls._TEST_UUID)
        claim.status = Claim.STATUS_CHECKED
        claim.save()
        for item in claim.items.all():
            item.status = ClaimItem.STATUS_PASSED
            item.save()
        for item in claim.services.all():
            item.status = ClaimService.STATUS_PASSED
            item.save()

    @classmethod
    def make_claim_rejected(cls, *args, **kwargs):
        claim = Claim.objects.get(uuid=cls._TEST_UUID)
        claim.status = Claim.STATUS_REJECTED
        claim.save()
        for item in claim.items.all():
            item.status = ClaimItem.STATUS_REJECTED
            item.save()
        for item in claim.services.all():
            item.status = ClaimService.STATUS_REJECTED
            item.save()

    _TEST_EVALUATION_URL = "https://imis_test_evaluation_endpoint.com/test_evaluation/"
    _TEST_EVALUATION_SERVER_LOGIN = "https://imis_test_evaluation_endpoint.com/login_endpoint/"
    _SERVER_POST_RESPONSE = "/rest_api/not_evaluated_response_bundle.json"
    _SERVER_GET_RESPONSE = "/rest_api/evaluated_response.json"

    class BaseTestContext:
        def __init__(self, user):
            self.user = user

    def setUp(self):
        super(TestRestAIEvaluationOrganizer, self).setUp()
        self.mixin_setup()

    @classmethod
    def setUpClass(cls):
        # Signals are not automatically bound in unit tests
        super(TestRestAIEvaluationOrganizer, cls).setUpClass()
        cls.ai_schema_client = Client(Schema(mutation=claim_ai_schema.Mutation))
        cls.claim_schema_client = Client(Schema(mutation=claim_schema.Mutation))
        bind_signals()

    @mock.patch('claim_ai_quality.communication_interface.rest_api.rest_client.ClaimRestApiRequestClient.LOGIN_ENDPOINT', new_callable=PropertyMock)
    @mock.patch('claim_ai_quality.communication_interface.rest_api.rest_client.ClaimRestApiRequestClient.BUNDLE_EVALUATION_ENDPOINT', new_callable=PropertyMock)
    @mock.patch('claim_ai_quality.communication_interface.rest_api.rest_client.ClaimRestApiRequestClient.CLAIM_EVALUATION_ENDPOINT', new_callable=PropertyMock)
    @mock.patch('claim_ai_quality.communication_interface.rest_api.rest_client.requests')
    @mock.patch('claim_ai_quality.schema.ClaimEvaluationOrganizer.evaluate_claims_from_mutation', side_effect=RestAIEvaluationOrganizer.evaluate_claims_from_mutation)
    @mock.patch('claim_ai_quality.gql_mutations.ClaimEvaluationOrganizer.evaluate_claims_from_mutation', side_effect=RestAIEvaluationOrganizer.evaluate_claims_from_mutation)
    @mock.patch('claim_ai_quality.schema.ClaimEvaluationOrganizer.evaluate_selected_claims', side_effect=RestAIEvaluationOrganizer.evaluate_selected_claims)
    def test_direct_graphene_call(self, send, mutation, organizer, requests_mock, url_claim, url_bundle, url_login):
        self.__setup_mocks(requests_mock, url_claim, url_bundle, url_login)
        expected_request = ClaimBundleConverter(ClaimSerializer()).build_claim_bundle(Claim.objects.filter(id=9999))
        executed = self.ai_schema_client.execute(
            self._MUTATION_SEND_CLAIMS_FOR_EVALUATION,
            context=self.BaseTestContext(self._TEST_USER)
        )
        mutation_id = executed['data']['sendClaimsForAiEvaluation']['clientMutationId']
        mutation_log = MutationLog.objects.filter(client_mutation_id=mutation_id)
        self._assert_post_request_calls(requests_mock, expected_request)
        self.assertTrue(mutation_log.exists())
        self._assert_claim_updated()

    @mock.patch('claim_ai_quality.communication_interface.rest_api.rest_client.ClaimRestApiRequestClient.LOGIN_ENDPOINT', new_callable=PropertyMock)
    @mock.patch('claim_ai_quality.communication_interface.rest_api.rest_client.ClaimRestApiRequestClient.BUNDLE_EVALUATION_ENDPOINT', new_callable=PropertyMock)
    @mock.patch('claim_ai_quality.communication_interface.rest_api.rest_client.ClaimRestApiRequestClient.CLAIM_EVALUATION_ENDPOINT', new_callable=PropertyMock)
    @mock.patch('claim_ai_quality.communication_interface.rest_api.rest_client.requests')
    @mock.patch('claim_ai_quality.schema.ClaimEvaluationOrganizer.evaluate_claims_from_mutation', side_effect=RestAIEvaluationOrganizer.evaluate_claims_from_mutation)
    @mock.patch('claim_ai_quality.gql_mutations.ClaimEvaluationOrganizer.evaluate_claims_from_mutation', side_effect=RestAIEvaluationOrganizer.evaluate_claims_from_mutation)
    @mock.patch('claim_ai_quality.schema.ClaimEvaluationOrganizer.evaluate_selected_claims', side_effect=RestAIEvaluationOrganizer.evaluate_selected_claims)
    @mock.patch('claim.schema.SubmitClaimsMutation.async_mutate')
    def test_submit_claim_evaluation(self, submit, send, mutation, organizer, requests_mock, url_claim, url_bundle, url_login):
        submit.side_effect = self.make_claim_accepted
        ClaimAiQualityConfig.event_based_activation = True
        self.__setup_mocks(requests_mock, url_claim, url_bundle, url_login)
        expected_request = ClaimBundleConverter(ClaimSerializer()).build_claim_bundle(Claim.objects.filter(id=9999))
        executed = self.claim_schema_client.execute(
            self._MUTATION_SUBMIT_CLAIMS,
            context=self.BaseTestContext(self._TEST_USER)
        )
        mutation_id = executed['data']['submitClaims']['clientMutationId']
        mutation_log = MutationLog.objects.filter(client_mutation_id=mutation_id)
        self._assert_post_request_calls(requests_mock, expected_request)
        self.assertTrue(mutation_log.exists())
        self._assert_claim_updated()

    @mock.patch('claim_ai_quality.communication_interface.rest_api.rest_client.ClaimRestApiRequestClient.LOGIN_ENDPOINT', new_callable=PropertyMock)
    @mock.patch('claim_ai_quality.communication_interface.rest_api.rest_client.ClaimRestApiRequestClient.BUNDLE_EVALUATION_ENDPOINT', new_callable=PropertyMock)
    @mock.patch('claim_ai_quality.communication_interface.rest_api.rest_client.ClaimRestApiRequestClient.CLAIM_EVALUATION_ENDPOINT', new_callable=PropertyMock)
    @mock.patch('claim_ai_quality.communication_interface.rest_api.rest_client.requests')
    @mock.patch('claim_ai_quality.schema.ClaimEvaluationOrganizer.evaluate_claims_from_mutation', side_effect=RestAIEvaluationOrganizer.evaluate_claims_from_mutation)
    @mock.patch('claim_ai_quality.gql_mutations.ClaimEvaluationOrganizer.evaluate_claims_from_mutation', side_effect=RestAIEvaluationOrganizer.evaluate_claims_from_mutation)
    @mock.patch('claim_ai_quality.schema.ClaimEvaluationOrganizer.evaluate_selected_claims', side_effect=RestAIEvaluationOrganizer.evaluate_selected_claims)
    @mock.patch('claim.schema.SubmitClaimsMutation.async_mutate')
    def test_submit_claim_evaluation_invalid(self, submit, send, mutation, organizer, requests_mock, url_claim, url_bundle, url_login):
        submit.side_effect = self.make_claim_rejected
        ClaimAiQualityConfig.event_based_activation = True
        self.__setup_mocks(requests_mock, url_claim, url_bundle, url_login)
        expected_request = ClaimBundleConverter(ClaimSerializer()).build_claim_bundle(Claim.objects.filter(id=9999))
        executed = self.claim_schema_client.execute(
            self._MUTATION_SUBMIT_CLAIMS,
            context=self.BaseTestContext(self._TEST_USER)
        )
        mutation_id = executed['data']['submitClaims']['clientMutationId']
        mutation_log = MutationLog.objects.filter(client_mutation_id=mutation_id)

        # Not called as claim is rejected
        requests_mock.post.assert_not_called()
        self.assertTrue(mutation_log.exists())
        self._assert_claim_not_updated()

    def _assert_claim_updated(self):
        claim = Claim.objects.get(uuid=self._TEST_CLAIM.uuid)
        json_ext = claim.json_ext
        item = list(claim.items.filter(validity_to__isnull=True).all())[0]
        service = list(claim.services.filter(validity_to__isnull=True).all())[0]
        self.assertTrue(json_ext['claim_ai_quality']['was_categorized'])
        self.assertEqual(claim.review_status, Claim.REVIEW_SELECTED)  # One of items rejected
        self.assertEqual(claim.status, Claim.STATUS_CHECKED)  # Status not changed
        self.assertEqual(item.status, 2)  # Rejected
        self.assertEqual(item.json_ext['claim_ai_quality']['ai_result'], 2)
        self.assertEqual(service.status, 1)  # Accepted
        self.assertEqual(service.json_ext['claim_ai_quality']['ai_result'], 1)

    def _assert_post_request_calls(self, requests_mock, expected_request, wait_for_response=True):
        def dflt(inp):
            if isinstance(inp, UUID):
                return inp.hex
            if isinstance(inp, decimal.Decimal):
                return float(inp)

        expected_request = orjson.dumps(expected_request, default=dflt)
        requests_mock.post.assert_has_calls([
            self._login_call(),
            call(F'https://imis_test_evaluation_endpoint.com/test_evaluation/?wait_for_evaluation={wait_for_response}',
                 data=expected_request,
                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer BEARER_TOKEN_FOR_USER'})
        ])

    def _login_call(self):
        return call(
            self._TEST_EVALUATION_SERVER_LOGIN, data={'username': 'claim_ai_admin', 'password': 'claim_ai_admin'})

    def __setup_mocks(self, requests_mock, url_claim, url_bundle, url_login):
        requests_mock.post = MagicMock(side_effect=RequestsMocked.mocked_post)
        requests_mock.get = MagicMock(side_effect=RequestsMocked.mocked_get)
        url_claim.return_value = self._TEST_EVALUATION_URL
        url_bundle.return_value = self._TEST_EVALUATION_URL
        url_login.return_value = self._TEST_EVALUATION_SERVER_LOGIN

    def _assert_claim_not_updated(self):
        claim = Claim.objects.get(uuid=self._TEST_CLAIM.uuid)
        json_ext = claim.json_ext
        item = list(claim.items.filter(validity_to__isnull=True).all())[0]
        service = list(claim.services.filter(validity_to__isnull=True).all())[0]
        self.assertFalse(json_ext['claim_ai_quality']['was_categorized'])
        self.assertEqual(claim.status, Claim.STATUS_REJECTED)  # Status not changed
        self.assertEqual(item.status, 2)  # Rejected
        self.assertEqual(item.json_ext['claim_ai_quality']['ai_result'], 2)
        self.assertEqual(service.status, 2)  # Rejected
        self.assertEqual(service.json_ext['claim_ai_quality']['ai_result'], 2)
