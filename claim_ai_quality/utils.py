from datetime import datetime

from claim.models import Claim
from core import TimeUtils
from django.db import transaction

from claim_ai_quality.apps import ClaimAiQualityConfig
from django.db.models import Q, TextField
from django.db.models.functions import Cast


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


def __update_number_of_tries(claim):
    tries = claim.json_ext['claim_ai_quality'].get('evaluation_tries', 0)
    claim.json_ext['claim_ai_quality']['evaluation_tries'] = (tries + 1)


def __reset_request_time(claim):
    claim.json_ext['claim_ai_quality']['request_time'] = None


@transaction.atomic
def reset_sent_but_not_evaluated_claims():
    claims = Claim.objects\
        .select_for_update() \
        .filter(
                json_ext__jsoncontains={'claim_ai_quality': {'was_categorized': False}},
                validity_to__isnull=True)\
        .filter(~Q(json_ext__jsoncontains={'claim_ai_quality': {'request_time': None}})) \
        .filter(status=Claim.STATUS_CHECKED)

    for claim in claims:
        parsed_time = datetime.fromisoformat(claim.json_ext['claim_ai_quality']['request_time'])
        time_delta = TimeUtils.now() - parsed_time
        time_delta_hours = time_delta.total_seconds() // 3600
        if time_delta_hours >= ClaimAiQualityConfig.request_time_resend_after_hours:
            __update_number_of_tries(claim)
            __reset_request_time(claim)
            claim.save()


def add_json_ext_to_all_submitted_claims():
    all_submitted_claims = Claim.objects\
        .filter(
            status__in=(Claim.STATUS_CHECKED, Claim.STATUS_REJECTED),
            validity_to__isnull=True) \
        .annotate(ext_as_str=Cast('json_ext', TextField()))\
        .exclude(ext_as_str__icontains='claim_ai_quality')

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
