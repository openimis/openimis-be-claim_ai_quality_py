import logging
from typing import List

from django.db.models import Model
from fhir.resources.bundle import Bundle, BundleEntry

from api_fhir_r4.converters import ReferenceConverterMixin
from api_fhir_r4.models import BundleType
from api_fhir_r4.serializers import ClaimSerializer
from claim.models import Claim, ClaimItem, ClaimService
from claim_ai_quality.fhir._claim_response_converter import ClaimResponseConverter

logger = logging.getLogger(__name__)


class ClaimBundleConverter:
    FHIR_REFERENCE_TYPE = ReferenceConverterMixin.UUID_REFERENCE_TYPE

    def __init__(self, fhir_serializer: ClaimSerializer):
        self.fhir_serializer = fhir_serializer
        self.fhir_serializer.reference_type = self.FHIR_REFERENCE_TYPE

        self.claim_response_converter = ClaimResponseConverter()
        self.fhir_serializer.context['contained'] = True

    def build_claim_bundle(self, claims: List[Model]) -> dict:
        """
        Builds bundle of claims. If claim from collection doesn't have any items or services in STATUS_PASSED it'll
        not be included in the bundle.
        """
        fhir_claims = [self.fhir_serializer.to_representation(claim) for claim in claims]
        # processes = []
        # fhir_claims = []
        # with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        #     for claim in claims:
        #         processes.append(executor.submit(
        #             self.fhir_serializer.to_representation, claim))
        #     for claim_convert in concurrent.futures.as_completed(processes):
        #         fhir_claims.append(claim_convert.result())

        bundle = self._build_bundle_set(fhir_claims)
        return bundle

    def update_claims_by_response_bundle(self, claim_response_bundle: dict):
        updated_claims = []
        for claim in claim_response_bundle['entry']:
            updated = self.claim_response_converter.update_claim(claim['resource'])
            if updated:
                updated_claims.append(updated)
        return updated_claims

    def get_claims_from_response_bundle(self, claim_response_bundle: dict):
        list_of_identifiers = [claim['resource']['id'] for claim in claim_response_bundle['entry']]
        claims = Claim.objects.filter(uuid__in=list_of_identifiers).all()
        found_uuids = set(claims.values_list("uuid", flat=True))
        missing = set(list_of_identifiers) - found_uuids
        if len(missing) != 0:
            logger.warning(F"Some of identifiers ({missing}) of claims in response"
                           F" bundle don't have representation in database")
            logger.debug(F"Payload with missing claims: {claim_response_bundle}")

        return list(claims)

    def _build_bundle_set(self, data):
        bundle = Bundle.construct()
        bundle.type = BundleType.BATCH.value
        bundle.total = len(data)
        bundle = bundle.dict()
        bundle['entry'] = []
        self._build_bundle_entry(bundle, data)
        return bundle

    def _build_bundle_entry(self, bundle, data):
        for obj in data:
            try:
                items = obj.get('item', [])
                items, contained = self._get_valid_items(items, obj['contained'], obj['id'])
                obj['contained'] = contained
                obj['item'] = items
                if not items:
                    continue
                for item in items:
                    self._item_float_values(item)

                entry = BundleEntry()
                entry = entry.dict()
                entry['resource'] = obj
                bundle['entry'].append(entry)
            except Exception as e:
                import traceback
                logger.debug(traceback.format_exc())
                logger.warning("Error while adding entry to bundle, ", e)

    def _item_float_values(self, item):
        item['quantity']['value'] = float(item['quantity']['value'])
        item['unitPrice']['value'] = float(item['unitPrice']['value'])

    def _exclude_rejected_items_and_services(self, claim):
        def exclude_rejected(provision):
            valid = []
            for item in provision.all():
                if item.status != 2:
                    valid.append(item)
            return valid

        claim.items.set(
            exclude_rejected(claim.items.all()))
        claim.services.set(
            exclude_rejected(claim.services.all()))

    def _get_valid_items(self, items_list, contained_list, claim_id):
        items_uuids = [i["productOrService"]["text"] for i in items_list if i['category']['text'] == 'item']
        services_uuids = [i["productOrService"]["text"] for i in items_list if i['category']['text'] == 'service']

        valid_items = ClaimItem.objects\
            .filter(claim__uuid=claim_id, item__code__in=items_uuids, validity_to=None) \
            .filter(status=ClaimItem.STATUS_PASSED)\
            .all()\
            .values_list('item__uuid', 'item__code').distinct()

        valid_services = ClaimService.objects\
            .filter(claim__uuid=claim_id, service__code__in=services_uuids, validity_to=None) \
            .filter(status=ClaimService.STATUS_PASSED) \
            .all()\
            .values_list('service__uuid', 'service__code').distinct()

        all_valid_uuids = list([i[0] for i in valid_items]) + list([s[0] for s in valid_services])
        all_valid_codes = list([i[1] for i in valid_items]) + list([s[1] for s in valid_services])

        updated_contained_list = []
        for contained in contained_list:
            if contained['resourceType'] not in ('Medication', 'ActivityDefinition'):
                updated_contained_list.append(contained)
            elif contained['resourceType'] == 'Medication':
                if self.__get_id(contained['id']) in all_valid_uuids:
                    updated_contained_list.append(contained)
            else:
                if self.__get_id(contained['id']) in all_valid_uuids:
                    updated_contained_list.append(contained)

        return [i for i in items_list if i["productOrService"]["text"] in all_valid_codes], updated_contained_list

    def __get_id(self, id_str):
        if '/' in id_str:
            return id_str.split('/')[1]
        else:
            return id_str
