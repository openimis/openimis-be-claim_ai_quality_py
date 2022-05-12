from unittest import mock, skipIf
from unittest.mock import PropertyMock, MagicMock

from django.conf import settings
from django.test import testcases
from graphene import Schema
from graphene.test import Client

from claim import schema as claim_schema
from claim.models import Claim, ClaimItem, ClaimService
from claim_ai_quality import schema as claim_ai_schema
from claim_ai_quality.apps import ClaimAiQualityConfig
from claim_ai_quality.schema import bind_signals
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

    @classmethod
    def mocked_encoder(cls, df_categorical):
        from sklearn import preprocessing
        le = preprocessing.LabelEncoder()
        for column in list(df_categorical.columns):
            df_categorical[column] = le.fit_transform(df_categorical[column])
        return df_categorical

    @classmethod
    def mocked_scaler(cls, df):
        from sklearn import preprocessing
        scaler = preprocessing.MinMaxScaler()
        return scaler.fit_transform(df)

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

    @skipIf('claim_ai' not in settings.INSTALLED_APPS,
            "Claim AI Module not attached, test for integrated solution skipped")
    def test_direct_graphene_call(self):
        with mock.patch('claim_ai.evaluation.predictor.AiPredictor.predict') as mock_:
            mock_.return_value = [1, 0]
            executed = self.ai_schema_client.execute(
                self._MUTATION_SEND_CLAIMS_FOR_EVALUATION,
                context=self.BaseTestContext(self._TEST_USER))
            mutation_id = executed['data']['sendClaimsForAiEvaluation']['clientMutationId']
            mutation_log = MutationLog.objects.filter(client_mutation_id=mutation_id)
            self.assertTrue(mutation_log.exists())
            self._assert_claim_updated()

    @skipIf('claim_ai' not in settings.INSTALLED_APPS,
            "Claim AI Module not attached, test for integrated solution skipped")
    @mock.patch('claim.schema.SubmitClaimsMutation.async_mutate')
    @mock.patch("claim_ai.evaluation.preprocessors.v2_preprocessor.AbstractAiInputDataFramePreprocessor.encoder",
                new_callable=PropertyMock)
    @mock.patch("claim_ai.evaluation.preprocessors.v2_preprocessor.AbstractAiInputDataFramePreprocessor.scaler",
                new_callable=PropertyMock)
    def test_submit_claim_evaluation(self, mocked_scaler, mocked_encoder, submit):
        mocked_scaler.return_value = MagicMock()
        mocked_scaler.return_value.transform = self.mocked_scaler

        mocked_encoder.return_value = MagicMock()
        mocked_encoder.return_value.transform = self.mocked_encoder

        submit.side_effect = self.make_claim_accepted
        with mock.patch('claim_ai.evaluation.predictor.AiPredictor.predict') as mock_:
            mock_.return_value = [1, 0]
            ClaimAiQualityConfig.event_based_activation = True
            executed = self.claim_schema_client.execute(
                self._MUTATION_SUBMIT_CLAIMS,
                context=self.BaseTestContext(self._TEST_USER))
            mutation_id = executed['data']['submitClaims']['clientMutationId']
            mutation_log = MutationLog.objects.filter(client_mutation_id=mutation_id)
            self.assertTrue(mutation_log.exists())
            self._assert_claim_updated()

    @skipIf('claim_ai' not in settings.INSTALLED_APPS,
            "Claim AI Module not attached, test for integrated solution skipped")
    @mock.patch('claim.schema.SubmitClaimsMutation.async_mutate')
    @mock.patch("claim_ai.evaluation.preprocessors.v2_preprocessor.AbstractAiInputDataFramePreprocessor.encoder",
                new_callable=PropertyMock)
    @mock.patch("claim_ai.evaluation.preprocessors.v2_preprocessor.AbstractAiInputDataFramePreprocessor.scaler",
                new_callable=PropertyMock)
    def test_submit_claim_evaluation_invalid(self, mocked_scaler, mocked_encoder, submit):
        mocked_scaler.return_value = MagicMock()
        mocked_scaler.return_value.transform = self.mocked_scaler

        mocked_encoder.return_value = MagicMock()
        mocked_encoder.return_value.transform = self.mocked_encoder

        submit.side_effect = self.make_claim_rejected
        with mock.patch('claim_ai.evaluation.predictor.AiPredictor.predict') as mock_:
            mock_.return_value = [1, 0]
            executed = self.claim_schema_client.execute(
                self._MUTATION_SUBMIT_CLAIMS,
                context=self.BaseTestContext(self._TEST_USER)
            )
            mutation_id = executed['data']['submitClaims']['clientMutationId']
            mutation_log = MutationLog.objects.filter(client_mutation_id=mutation_id)
            # Not called as claim is rejected
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
