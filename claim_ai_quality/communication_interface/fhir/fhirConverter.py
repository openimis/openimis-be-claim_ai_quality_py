import concurrent.futures
import logging

from typing import List
from claim.models import Claim, ClaimItem, ClaimService
from fhir.resources.bundle import Bundle, BundleEntry, BundleLink
from api_fhir_r4.models import BundleType
from api_fhir_r4.serializers import ClaimSerializer
from api_fhir_r4.converters import ReferenceConverterMixin
from django.db.models import Model

from claim_ai_quality.communication_interface.fhir._claim_response_converter import ClaimResponseConverter

logger = logging.getLogger(__name__)


class ClaimBundleConverter:
    FHIR_REFERENCE_TYPE = ReferenceConverterMixin.DB_ID_REFERENCE_TYPE

    def __init__(self, fhir_serializer: ClaimSerializer):
        self.fhir_serializer = fhir_serializer
        self.fhir_serializer.reference_type = self.FHIR_REFERENCE_TYPE

        self.claim_response_converter = ClaimResponseConverter()
        self.fhir_serializer.context['contained'] = True

    def build_claim_bundle(self, claims: List[Model]) -> Bundle:
        fhir_claims = []
        processes = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            for claim in claims:
                if claim.status == Claim.STATUS_CHECKED:
                    processes.append(executor.submit(
                        self.fhir_serializer.to_representation, claim
                    ))
                else:
                    logger.warning(F"Claim {claim} is not in checked status and won't be sent for AI evaluation")

            for claim_convert in concurrent.futures.as_completed(processes):
                fhir_claims.append(claim_convert.result())

        bundle = self._build_bundle_set(fhir_claims)
        return bundle

    def update_claims_by_response_bundle(self, claim_response_bundle: dict):
        updated_claims = []
        for claim in claim_response_bundle['entry']:
            updated_claims.append(
                self.claim_response_converter.update_claim(claim['resource'])
            )

        return updated_claims

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
                items, contained = self._get_valid_items(items, obj['contained'], int(obj['id']))
                obj['contained'] = contained
                obj['item'] = items
                if not items:
                    continue
                for item in items:
                    self._item_float_values(item)

                for contained in obj['contained']:
                    if contained['resourceType'] in ('Medication', 'ActivityDefinition'):
                        self._extension_float(contained['extension'])
                entry = BundleEntry()
                entry = entry.dict()
                entry['resource'] = obj
                bundle['entry'].append(entry)
            except Exception as e:
                logger.warning("Error while adding entry to bundle, ", e)

    def _item_float_values(self, item):
        item['quantity']['value'] = float(item['quantity']['value'])
        item['unitPrice']['value'] = float(item['unitPrice']['value'])

    def _extension_float(self, extensions):
        extension = next(ext for ext in extensions if ext['url'] == 'unitPrice')
        extension['valueMoney']['value'] = float(extension['valueMoney']['value'])

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
        items_uuids = [i["productOrService"]["text"]
                       for i in items_list if i['category']['text'] == 'item']
        services_uuids = [i["productOrService"]["text"]
                          for i in items_list if i['category']['text'] == 'service']

        valid_items = ClaimItem.objects\
            .filter(claim__id=claim_id, item__code__in=items_uuids, validity_to=None) \
            .filter(status=ClaimItem.STATUS_PASSED)\
            .all()\
            .values_list('item__id', 'item__code').distinct()

        valid_services = ClaimService.objects\
            .filter(claim__id=claim_id, service__code__in=services_uuids, validity_to=None) \
            .filter(status=ClaimService.STATUS_PASSED) \
            .all()\
            .values_list('service__id', 'service__code').distinct()

        all_valid_uuids = list([i[0] for i in valid_items]) + list([s[0] for s in valid_services])
        all_valid_codes = list([i[1] for i in valid_items]) + list([s[1] for s in valid_services])

        updated_contained_list = []
        for contained in contained_list:
            if contained['resourceType'] not in ('Medication', 'ActivityDefinition'):
                updated_contained_list.append(contained)
            elif contained['resourceType'] == 'Medication':
                if int(contained['id'].split('/')[1]) in all_valid_uuids:
                    updated_contained_list.append(contained)
            else:
                if int(contained['id'].split('/')[1]) in all_valid_uuids:
                    updated_contained_list.append(contained)

        return [i for i in items_list if i["productOrService"]["text"] in all_valid_codes], updated_contained_list
