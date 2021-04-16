import concurrent.futures
import logging

from typing import List
from api_fhir_r4.models import Bundle, BundleType, BundleEntry
from api_fhir_r4.serializers import ClaimSerializer
from django.db.models import Model
from claim_ai_quality.communication_interface.fhir._claim_response_converter import ClaimResponseConverter

logger = logging.getLogger(__name__)

class ClaimBundleConverter:

    def __init__(self, fhir_serializer: ClaimSerializer):
        self.fhir_serializer = fhir_serializer
        self.claim_response_converter = ClaimResponseConverter()
        self.fhir_serializer.context['contained'] = True

    def build_claim_bundle(self, claims: List[Model]) -> Bundle:
        fhir_claims = []
        processes = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            for claim in claims:
                processes.append(executor.submit(self.fhir_serializer.to_representation, claim))

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
        bundle = Bundle()
        bundle.type = BundleType.BATCH.value
        bundle.total = len(data)
        bundle = bundle.toDict()
        bundle['entry'] = []
        self._build_bundle_entry(bundle, data)
        return bundle

    def _build_bundle_entry(self, bundle, data):
        for obj in data:
            try:
                items = obj.get('item', [])
                if not items:
                    continue
                for item in items:
                    self._item_float_values(item)

                for contained in obj['contained']:
                    if contained['resourceType'] in ('Medication', 'ActivityDefinition'):
                        self._extension_float(contained['extension'])
                entry = BundleEntry()
                entry = entry.toDict()
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
