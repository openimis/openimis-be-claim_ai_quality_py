from functools import lru_cache

from api_fhir_r4.converters import ClaimConverter
from typing import List

from api_fhir_r4.models import Bundle, BundleType, BundleEntry
from django.db.models import Model

from claim_ai_quality.apps import ClaimAiQualityConfig


@lru_cache(maxsize=None)
def _get_test_payload():
    # Test data mocking claims transformed to fhir bundle
    from ..temp_data import socket_data
    socket_data['entry'] = socket_data['entry'] * ClaimAiQualityConfig.bundle_size
    return socket_data


class FHIRBundleConverter:
    fhir_converter = ClaimConverter()

    def build_data_bundle(self, claims: List[Model]) -> Bundle:
        # TODO: Should return list claims converted to bundle
        return _get_test_payload()

    def _build_bundle_set(self, data):
        bundle = Bundle()
        bundle.type = BundleType.BATCH.value
        bundle.total = len(data)
        self._build_bundle_entry(bundle, data)
        return bundle

    def _build_bundle_entry(self, bundle, data):
        for obj in data:
            entry = BundleEntry()
            entry.resource = obj
            bundle.entry.append(entry)
