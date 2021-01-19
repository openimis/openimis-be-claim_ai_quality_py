import concurrent.futures

from typing import List

from api_fhir_r4.models import Bundle, BundleType, BundleEntry
from api_fhir_r4.serializers import ClaimSerializer
from django.db.models import Model


class ClaimBundleConverter:

    def __init__(self, fhir_serializer: ClaimSerializer):
        self.fhir_serializer = fhir_serializer
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
            entry = BundleEntry()
            entry = entry.toDict()
            entry['resource'] = obj
            bundle['entry'].append(entry)
