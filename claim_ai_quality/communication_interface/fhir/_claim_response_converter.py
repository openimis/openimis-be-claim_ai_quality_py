from datetime import datetime

from claim.models import Claim, ClaimDetail
from django.db import transaction

from claim_ai_quality.apps import ClaimAiQualityConfig


class ClaimResponseConverter:

    @transaction.atomic
    def update_claim(self, claim_response: dict):
        # change claim status to select for review if any rejected items
        claim = Claim.objects.get(uuid=claim_response['id'], validity_to__isnull=True)
        if self._response_have_rejected_items(claim_response):
            claim.save_history()
            self.__set_evaluated_review_status(claim)

        # update item status
        self._update_items_status(claim, claim_response)

        # json_ext update
        self._update_claim_json_ext(claim)
        claim.save()
        return claim.uuid

    def __set_evaluated_review_status(self, claim: Claim):
        claim.review_status = Claim.REVIEW_SELECTED

    def _response_have_rejected_items(self, claim_response):
        for item in claim_response['item']:
            category = self._get_item_adjudication(item)
            if category == ClaimAiQualityConfig.rejected_category_code:
                return True
        return False

    def _update_items_status(self, claim, claim_response):
        for item in claim_response['item']:
            provided = self._get_claim_item_by_claim_response_item(claim, item)
            provided.save_history()
            adjudication = self._get_item_adjudication(item)

            # change item status and service status to rejected if adjudication.category == 1
            if adjudication == ClaimAiQualityConfig.rejected_category_code:
                provided.rejection_reason = ClaimAiQualityConfig.reason_rejected_by_ai_code
                provided.status = ClaimDetail.STATUS_REJECTED

            # jsonExt set to true, add ai_result = adjudiction.category + 1
            json_ext = provided.json_ext or {}
            json_ext['claim_ai_quality'] = self._create_item_ai_quality_json_ext(adjudication)
            provided.json_ext = json_ext
            provided.save()

    def _update_claim_json_ext(self, claim):
        json_ext = claim.json_ext or {}
        json_ext['claim_ai_quality']['was_categorized'] = True
        json_ext['claim_ai_quality']['response_time'] = str(datetime.now())
        claim.json_ext = json_ext

    def _create_item_ai_quality_json_ext(self, item_adjudication):
        return {'ai_result': int(item_adjudication)+1}

    def _get_item_adjudication(self, item):
        return item['adjudication'][0]['reason']['coding'][0]['code']

    def _set_evaluated_review_status(self, claim: Claim):
        claim.review_status = Claim.REVIEW_SELECTED

    def _get_claim_item_by_claim_response_item(self, claim, item):
        category, item_id = item['extension'][0]['valueReference']['reference'].split('/')
        if category == 'Medication':
            provided = claim.items.filter(item__uuid=item_id, validity_to__isnull=True).first()
        elif category == 'ActivityDefinition':
            provided = claim.services.filter(service__uuid=item_id, validity_to__isnull=True).first()
        else:
            raise ValueError(F"Invalid provided item of type: {category}")
        return provided
