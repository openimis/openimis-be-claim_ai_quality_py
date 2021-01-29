# Generated by Django 3.0.3 on 2021-01-27 17:13

from django.db import migrations
from claim.models import Claim, ClaimItem, ClaimService

def _empty_ai_quality_json():
    return {"was_categorized": False, "request_time": None, "response_time": None}


def _claim_ai_quality_json(claim):
    return {
        "was_categorized": True,
        "request_time": str(claim.validity_from_review),
        "response_time": str(claim.validity_from_review)
    }


def _add_claim_json_entry(claim):
    current_json = claim.json_ext or {}
    if not current_json.get("claim_ai_quality", None):
        if claim.status == Claim.STATUS_CHECKED:
            # If status checked add categorized=False
            current_json["claim_ai_quality"] = _empty_ai_quality_json()
        elif claim.status in (Claim.STATUS_PROCESSED, Claim.STATUS_VALUATED, Claim.STATUS_REJECTED):
            # Claims that were processed, valuated or rejected are considered categorized
            current_json["claim_ai_quality"] = _claim_ai_quality_json(claim)
        elif claim.status == Claim.STATUS_ENTERED:
            # No categorization for claims that were just entered
            pass
    claim.json_ext = current_json
    claim.save_history()
    claim.save()


def _add_claim_item_entry(claim_item):
    current_json = claim_item.json_ext or {}
    if not current_json.get("claim_ai_quality", None):
        current_json["claim_ai_quality"] = {
            "ai_result": str(claim_item.status)
        }
        claim_item.json_ext = current_json
        claim_item.save_history()
        claim_item.save()


def claim_ai_quality_initial(apps, schema_editor):
    for item in ClaimItem.objects.filter(validity_to=None).all():
        _add_claim_item_entry(item)

    for service in ClaimService.objects.filter(validity_to=None).all():
        _add_claim_item_entry(service)

    for claim in Claim.objects.filter(validity_to=None).all():
        _add_claim_json_entry(claim)


class Migration(migrations.Migration):

    dependencies = [
        ('claim', '0012_item_service_jsonExtField')
    ]

    operations = [
        migrations.RunPython(claim_ai_quality_initial, reverse_code=migrations.RunPython.noop)
    ]
