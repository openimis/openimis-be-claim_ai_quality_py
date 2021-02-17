from claim.models import Claim
from django.db.models import Q


def get_rejected_claim_json_extension(claim):
    return {
        "was_categorized": False,
        "request_time": str(claim.validity_from),
        "response_time": str(claim.validity_from)
    }

def get_base_claim_ai_json_extension():
    return {
        "was_categorized": False,
        "request_time": "None",
        "response_time": "None"
    }


def add_json_ext_to_all_submitted_claims():
    all_submitted_claims = Claim.objects\
        .filter(
            status__in=(Claim.STATUS_CHECKED, Claim.STATUS_REJECTED),
            validity_to__isnull=True)\
        .all()

    for claim in all_submitted_claims:
        json_ext = claim.json_ext or {}

        if json_ext.get('claim_ai_quality', None):
            continue

        if claim.status != Claim.STATUS_REJECTED:
            ai_quality_json_entry = get_base_claim_ai_json_extension()
        else:
            ai_quality_json_entry = get_rejected_claim_json_extension(claim)
        json_ext['claim_ai_quality'] = ai_quality_json_entry
        claim.json_ext = json_ext
        claim.save()

    return all_submitted_claims