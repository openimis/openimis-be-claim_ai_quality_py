from datetime import datetime

from claim.gql_mutations import SubmitClaimsMutation
from core.schema import signal_mutation_module_after_mutating
from claim.models import Claim
from django.dispatch import dispatcher


def get_base_claim_ai_json_extension():
    return {
        "was_categorized": False,
        "request_time": None,
        "response_time": None
    }


def on_claim_mutation(sender: dispatcher.Signal, **kwargs):
    mutation_type = sender._mutation_class

    if not mutation_type == SubmitClaimsMutation._mutation_class:
        return

    uuids = kwargs['data'].get('uuids', [])
    if not uuids:
        uuid = kwargs['data'].get('claim_uuid', None)
        uuids = [uuid] if uuid else []
    if not uuids:
        return []

    claims = Claim.objects.filter(uuid__in=uuids).all()
    for claim in claims:
        json_ext = claim.json_ext or {}
        json_ext['claim_ai_quality'] = get_base_claim_ai_json_extension()
        claim.json_ext = json_ext
        claim.save()

    return []


def bind_signals():
    signal_mutation_module_after_mutating["claim"].connect(on_claim_mutation)
