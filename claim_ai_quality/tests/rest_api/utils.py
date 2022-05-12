from medical.models import Diagnosis
from medical.test_helpers import create_test_item, create_test_service

from api_fhir_r4.tests import LocationTestMixin, PatientTestMixin
from api_fhir_r4.utils import TimeUtils, DbManagerUtils
from claim.models import Claim, ClaimItem, ClaimService
from claim.test_helpers import create_test_claim_admin
from claim_ai_quality.apps import ClaimAiQualityConfig
from core import datetime
from core.forms import User
from core.services import create_or_update_interactive_user, create_or_update_core_user
from insuree.test_helpers import create_test_insuree
from location.models import HealthFacility
from product.test_helpers import create_test_product


class ClaimAITestInitialDataGenerator:
    _TEST_CODE = 'codeTest'
    _TEST_STATUS = Claim.STATUS_CHECKED
    _TEST_UUID = 'AAAA1E5A-C491-4468-A540-567E569BAAAA'
    _TEST_STATUS_DISPLAY = "entered"
    _TEST_OUTCOME = "queued"
    _TEST_ADJUSTMENT = "adjustment"
    _TEST_DATE_PROCESSED = "2010-11-16T00:00:00"
    _TEST_APPROVED = 1000.00
    _TEST_REJECTION_REASON = 0
    _TEST_VISIT_TYPE = "O"

    # claim item data
    _TEST_ITEM_CODE = "iCode"
    _TEST_ITEM_UUID = "AAAA76E2-DC28-4B48-8E29-3AC4ABEC0000"
    _TEST_ITEM_STATUS = ClaimItem.STATUS_PASSED
    _TEST_ITEM_QUANTITY = 20
    _TEST_ITEM_PRICE = 10.0
    _TEST_ITEM_REJECTED_REASON = 0

    # claim service data
    _TEST_SERVICE_CODE = "sCode"
    _TEST_SERVICE_UUID = "AAAA29BA-3F4E-4E6F-B55C-23A488A10000"
    _TEST_SERVICE_STATUS = ClaimService.STATUS_PASSED
    _TEST_SERVICE_QUANTITY = 1
    _TEST_SERVICE_PRICE = 800
    _TEST_SERVICE_REJECTED_REASON = 0

    _TEST_ID = 9999
    _TEST_HISTORICAL_ID = 9998
    _PRICE_ASKED_ITEM = 1000.0
    _PRICE_ASKED_SERVICE = 820.0
    _PRICE_APPROVED = 1000
    _ADMIN_AUDIT_USER_ID = -1

    _TEST_UUID = "AAAA1E5A-C491-4468-A540-567E569BAAAA"
    _TEST_ITEM_AVAILABILITY = True

    _TEST_ITEM_TYPE = 'D'
    _TEST_SERVICE_TYPE = 'D'

    # insuree and claim admin data
    _TEST_PATIENT_UUID = "76aca309-f8cf-4890-8f2e-b416d78de00b"
    _TEST_PATIENT_ID = 9283
    _TEST_CLAIM_ADMIN_UUID = "044c33d1-dbf3-4d6a-9924-3797b461e535"
    _TEST_CLAIM_ADMIN_ID = 9282

    _PRICE_VALUATED = 1000.0
    # hf test data
    _TEST_HF_ID = 10000
    _TEST_HF_UUID = "6d0eea8c-62eb-11ea-94d6-c36229a16c2f"
    _TEST_HF_CODE = "12345678"
    _TEST_HF_NAME = "TEST_NAME"
    _TEST_HF_LEVEL = "H"
    _TEST_HF_LEGAL_FORM = "G"
    _TEST_ADDRESS = "TEST_ADDRESS"
    _TEST_PHONE = "133-996-476"
    _TEST_FAX = "1-408-999 8888"
    _TEST_EMAIL = "TEST@TEST.com"

    _TEST_USER_NAME = "TestUserTest2"
    _TEST_USER_PASSWORD = "TestPasswordTest2"
    _TEST_DATA_USER = {
        "username": _TEST_USER_NAME,
        "last_name": _TEST_USER_NAME,
        "password": _TEST_USER_PASSWORD,
        "other_names": _TEST_USER_NAME,
        "user_types": "INTERACTIVE",
        "language": "en",
        "roles": [9],
    }

    _TEST_PRODUCT_CODE = "Test0004"

    _GQL_EVALUATION_TEMPLATE = """
        mutation {
          sendClaimsForAiEvaluation(
            input: {
              clientMutationId: "AAAA7765-0A21-4BE0-B100-220F889BAAAA"
              clientMutationLabel: "Claim evaluated: _3BKQ16A"
              uuids: ["%(claim_uuid)s"]
            }
          ) {
            clientMutationId
            internalId
          }
        }
    """

    _GQL_SUBMIT_TEMPLATE = """
        mutation {
          submitClaims(
            input: {
              clientMutationId: "AAAA7765-0A21-4BE0-B100-220F889BAAAA"
              clientMutationLabel: "Claim evaluated: _3BKQ16A"
              uuids: ["%(claim_uuid)s"]
            }
          ) {
            clientMutationId
            internalId
          }
        }
    """

    def mixin_setup(self):
        self._TEST_USER = self.get_or_create_user_api()
        # This user should be created using migration, not available in unit tests by default
        self._CLAIM_AI_ADMIN = self.get_or_create_user_api(ClaimAiQualityConfig.claim_ai_username)
        self.item = create_test_item(
            self._TEST_ITEM_TYPE,
            custom_props={"code": self._TEST_ITEM_CODE, 'price': self._TEST_ITEM_PRICE, 'care_type': 'O'}
        )
        self.item.uuid = self._TEST_ITEM_UUID
        self.item.save()
        self.service = create_test_service(
            self._TEST_SERVICE_TYPE,
            custom_props={"code": self._TEST_SERVICE_CODE, 'price': self._TEST_SERVICE_PRICE, 'care_type': 'O'}
        )
        self.service.uuid = self._TEST_SERVICE_UUID
        self.service.save()
        self._TEST_HF = self._create_test_health_facility()
        self._TEST_PRODUCT = self._create_test_product()
        self._TEST_CLAIM = self._create_test_unevaluated_claim()
        self._MUTATION_SEND_CLAIMS_FOR_EVALUATION = \
            self._GQL_EVALUATION_TEMPLATE % {'claim_uuid': self._TEST_CLAIM.uuid}
        self._MUTATION_SUBMIT_CLAIMS = \
            self._GQL_SUBMIT_TEMPLATE % {'claim_uuid': self._TEST_CLAIM.uuid}

    def _create_test_unevaluated_claim(self):
        imis_location = PatientTestMixin().create_mocked_location()
        imis_location.save()

        insuree = create_test_insuree(with_family=True)
        insuree.uuid = self._TEST_PATIENT_UUID
        insuree.id = self._TEST_PATIENT_ID
        insuree.current_village = imis_location
        insuree.save()

        imis_family = insuree.family
        imis_family.location = imis_location
        imis_family.save()
        insuree.family = imis_family
        insuree.save()

        historical_claim = self._create_test_claim(insuree, True)
        claim = self._create_test_claim(insuree)

        self._create_items_and_services(historical_claim, self._TEST_PRODUCT, self.item, self.service)
        item, service = self._create_items_and_services(claim, self._TEST_PRODUCT, self.item, self.service)
        return claim

    def _create_items_and_services(self, claim, imis_product, item, service):
        claim_item = self._create_test_claim_item(claim, item, imis_product)
        claim_service = self._create_test_claim_service(claim, service, imis_product)
        return claim_item, claim_service

    def _create_test_claim(self, insuree, historical=False):
        imis_claim = Claim()
        if not historical:
            imis_claim.id = self._TEST_ID
            imis_claim.uuid = self._TEST_UUID
        else:
            imis_claim.id = self._TEST_HISTORICAL_ID
        imis_claim.code = self._TEST_CODE
        imis_claim.status = self._TEST_STATUS
        imis_claim.adjustment = self._TEST_ADJUSTMENT
        imis_claim.date_processed = TimeUtils.str_to_date(self._TEST_DATE_PROCESSED)
        imis_claim.approved = self._TEST_APPROVED
        imis_claim.rejection_reason = self._TEST_REJECTION_REASON
        imis_claim.insuree = insuree
        imis_claim.health_facility = self._TEST_HF
        if not historical:
            imis_claim.icd = Diagnosis(code='ICD00I')
            imis_claim.icd.audit_user_id = self._ADMIN_AUDIT_USER_ID
            imis_claim.icd.save()
        else:
            imis_claim.icd = Diagnosis(code='ICD00V')
            imis_claim.icd.audit_user_id = self._ADMIN_AUDIT_USER_ID
            imis_claim.icd.save()
        imis_claim.audit_user_id = self._ADMIN_AUDIT_USER_ID
        imis_claim.icd.date_from = datetime.date(2018, 12, 12)
        imis_claim.date_from = datetime.date(2018, 12, 12)
        imis_claim.date_claimed = datetime.date(2018, 12, 14)
        imis_claim.visit_type = self._TEST_VISIT_TYPE
        claim_admin = create_test_claim_admin()
        claim_admin.uuid = self._TEST_CLAIM_ADMIN_UUID
        claim_admin.id = self._TEST_CLAIM_ADMIN_ID
        claim_admin.health_facility = self._TEST_HF
        claim_admin.save()
        imis_claim.admin = claim_admin
        imis_claim.save()
        return imis_claim

    def _create_test_claim_item(self, claim, provided, product):
        item = ClaimItem()
        item.item = provided
        item.product = product
        item.claim = claim
        item.status = self._TEST_ITEM_STATUS
        item.qty_approved = self._TEST_ITEM_QUANTITY
        item.qty_provided = self._TEST_ITEM_QUANTITY
        item.rejection_reason = self._TEST_ITEM_REJECTED_REASON
        item.availability = self._TEST_ITEM_AVAILABILITY
        item.price_asked = self._PRICE_ASKED_ITEM
        item.price_approved = self._TEST_ITEM_PRICE
        item.audit_user_id = self._ADMIN_AUDIT_USER_ID
        item.price_valuated = self._PRICE_VALUATED
        item.save()
        return item

    def _create_test_claim_service(self, claim, provided, product):
        service = ClaimService()
        service.service = provided
        service.product = product
        service.claim = claim
        service.status = self._TEST_SERVICE_STATUS
        service.qty_approved = self._TEST_SERVICE_QUANTITY
        service.qty_provided = self._TEST_SERVICE_QUANTITY
        service.rejection_reason = self._TEST_SERVICE_REJECTED_REASON
        service.availability = self._TEST_ITEM_AVAILABILITY
        service.price_asked = self._PRICE_ASKED_SERVICE
        service.price_approved = self._TEST_SERVICE_PRICE
        service.audit_user_id = self._ADMIN_AUDIT_USER_ID
        service.price_valuated = self._PRICE_VALUATED
        service.save()
        return service

    def _create_test_health_facility(self):
        location = LocationTestMixin().create_test_imis_instance()
        location.save()
        hf = HealthFacility()
        hf.id = self._TEST_HF_ID
        hf.uuid = self._TEST_HF_UUID
        hf.code = self._TEST_HF_CODE
        hf.name = self._TEST_HF_NAME
        hf.level = self._TEST_HF_LEVEL
        hf.legal_form_id = self._TEST_HF_LEGAL_FORM
        hf.address = self._TEST_ADDRESS
        hf.phone = self._TEST_PHONE
        hf.fax = self._TEST_FAX
        hf.email = self._TEST_EMAIL
        hf.location_id = location.id
        hf.offline = False
        hf.audit_user_id = -1
        hf.save()
        return hf

    def _create_test_product(self):
        imis_product = create_test_product(self._TEST_PRODUCT_CODE, valid=True, custom_props=None)
        imis_product.save()
        return imis_product

    def get_or_create_user_api(self, username=_TEST_USER_NAME):
        user = DbManagerUtils.get_object_or_none(User, username=username)
        if user is None:
            user = self.__create_user_interactive_core(username)
        return user

    def __create_user_interactive_core(self, username=_TEST_USER_NAME):
        data = self._TEST_DATA_USER
        data['username'] = username
        i_user, i_user_created = create_or_update_interactive_user(
            user_id=None, data=data, audit_user_id=999, connected=False
        )
        create_or_update_core_user(user_uuid=None, username=username, i_user=i_user)
        return DbManagerUtils.get_object_or_none(User, username=username)

