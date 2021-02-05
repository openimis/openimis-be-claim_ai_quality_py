from api_fhir_r4.serializers import ClaimSerializer
from claim.models import Claim
from claim.test_helpers import create_test_claim, create_test_claimservice, create_test_claimitem
from django.test import TestCase
from .test_response_bundle import adjudication_bundle, custom_bundle
from ..communication_interface import ClaimBundleConverter


class TestClaimBundleConverter(TestCase):
    FHIR_CONVERTER = ClaimBundleConverter(ClaimSerializer())

    def setUp(self) -> None:
        self._build_claim()

    def test_claim_response_transformation(self):
        self.FHIR_CONVERTER.update_claims_by_response_bundle(self.TEST_RESPONSE_BUNDLE)

        claim = Claim.objects.get(uuid=self.TEST_CLAIM.uuid)
        item = claim.items.first()
        service = claim.services.first()

        self.assertEqual(item.json_ext['claim_ai_quality']['ai_result'], 1)
        self.assertNotEqual(item.status, 2)  # Not rejected

        self.assertEqual(service.json_ext['claim_ai_quality']['ai_result'], 2)
        self.assertEqual(service.status, 2)  # Rejected
        self.assertEqual(service.rejection_reason, -2)  # Rejected by AI

        self.assertEqual(claim.json_ext['claim_ai_quality']['was_categorized'], True)
        self.assertEqual(claim.review_status, 4)

    def test_claim_response_transformation_all_valid(self):
        test_claim_response = self.TEST_RESPONSE_BUNDLE.copy()
        test_claim_response['entry'][0]['item'][1]['adjudication'][0]['reason']['coding'][0]['code'] = 0

        self.FHIR_CONVERTER.update_claims_by_response_bundle(self.TEST_RESPONSE_BUNDLE)

        claim = Claim.objects.get(uuid=self.TEST_CLAIM.uuid)
        item = claim.items.first()
        service = claim.services.first()

        self.assertEqual(item.json_ext['claim_ai_quality']['ai_result'], 1)
        self.assertNotEqual(item.status, 2)  # Not rejected

        self.assertEqual(service.json_ext['claim_ai_quality']['ai_result'], 1)
        self.assertNotEqual(service.status, 2)  # Rejected

        self.assertEqual(claim.json_ext['claim_ai_quality']['was_categorized'], True)
        self.assertNotEqual(claim.review_status, 4)

    @classmethod
    def _build_claim(cls):
        cls.TEST_CLAIM = create_test_claim()
        cls.TEST_CLAIM.json_ext = {'claim_ai_quality': {'was_categorized': False}}
        cls.TEST_CLAIM.save()
        cls.TEST_CLAIM_ITEM = create_test_claimitem(cls.TEST_CLAIM, 'D')
        cls.TEST_CLAIM_ITEM.save()
        cls.TEST_CLAIM_SERVICE = create_test_claimservice(cls.TEST_CLAIM, 'S')
        cls.TEST_CLAIM_SERVICE.save()
        cls.TEST_RESPONSE_BUNDLE = custom_bundle(cls.TEST_CLAIM.uuid,
                                                 cls.TEST_CLAIM_ITEM.item.uuid,
                                                 cls.TEST_CLAIM_SERVICE.service.uuid)