import logging
from itertools import groupby

from core import TimeUtils
from claim.models import Claim, ClaimDetail
from django.db import transaction
from medical.models import Item, Service

from claim_ai_quality.apps import ClaimAiQualityConfig

logger = logging.getLogger(__name__)


class ClaimResponseConverter:

    @transaction.atomic
    def update_claim(self, claim_response: dict):
        # change claim status to select for review if any rejected items
        try:
            if claim_response.get("error", None):
                self._log_claim_evaluation_error(claim_response)
                return

            claim = Claim.objects.select_for_update().get(id=int(claim_response['id']), validity_to__isnull=True)
            if self._response_have_rejected_items(claim_response):
                self.__set_evaluated_review_status(claim)

            # update item status
            self._update_items_status(claim, claim_response)

            # json_ext update
            self._update_claim_json_ext(claim)
            claim.save()
            return claim.uuid
        except Exception as e:
            logger.error(F'Exception occurred during update, reason: {e}')
            return None

    def __set_evaluated_review_status(self, claim: Claim):
        claim.review_status = Claim.REVIEW_SELECTED

    def _response_have_rejected_items(self, claim_response):
        for item in claim_response['item']:
            category = self._get_item_adjudication(item)
            if category == ClaimAiQualityConfig.rejected_category_code:
                return True
        return False

    def _update_items_status(self, claim, claim_response):
        grouped_items = self._group_items(claim_response['item'])

        for provided_key, claim_provisions in grouped_items:
            for index, item in enumerate(list(claim_provisions)):
                self._update_single_item(item, claim)

    def _update_claim_json_ext(self, claim):
        json_ext = claim.json_ext or {}
        if not json_ext.get('claim_ai_quality', None):
            json_ext['claim_ai_quality'] = {}
        json_ext['claim_ai_quality']['was_categorized'] = True
        json_ext['claim_ai_quality']['response_time'] = str(TimeUtils.now())
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
            provided = claim.items \
                .select_for_update() \
                .filter(item__id=int(item_id), validity_to__isnull=True)\
                .order_by('validity_from')\
                .first()
        elif category == 'ActivityDefinition':
            provided = claim.services \
                .select_for_update() \
                .filter(service__id=int(item_id), validity_to__isnull=True)\
                .order_by('validity_from')\
                .first()
        else:
            raise ValueError(F"Invalid provided item of type: {category}")

        if provided is None:
            model = Item if category == 'Medication' else Service
            item = model.objects.filter(uuid=item_id).first()
            logger.warning(F"Couldn't match item {item.code} ({item.name}) with claim {claim.code}")
        return provided

    def _group_items(self, items):
        return groupby(items, key=lambda item: item['extension'][0]['valueReference']['reference'])

    def _update_single_item(self, item, claim,):
        provided = self._get_claim_item_by_claim_response_item(claim, item)
        if provided is None:
            return

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
        provided.validity_from = TimeUtils.now()
        provided.save()

    def _log_claim_evaluation_error(self, claim_response):
        path = ClaimAiQualityConfig.claim_evaluation_error_log_path
        with open(path, 'a') as f:
            error_message = claim_response['error'][0]['text']
            claim_id = claim_response['id']
            f.write(f'Claim [{claim_id}] evaluation failed, error: {error_message}\n')
        return
