import asyncio
import logging
import threading
import traceback

from typing import List, Union

from django.db.models import QuerySet

from claim.models import Claim
from claim_ai_quality.ai_evaluation import create_base_websocket_communication_interface, send_claims_websocket
from claim_ai_quality.ai_evaluation.rest_organizer import RestAIEvaluationOrganizer
from claim_ai_quality.apps import ClaimAiQualityConfig
from claim_ai_quality.utils import reset_sent_but_not_evaluated_claims

logger = logging.getLogger(__name__)


def _send_submitted_claims(submitted_claims_bundle):
    try:
        RestAIEvaluationOrganizer.evaluate_selected_claims(submitted_claims_bundle)
    except Exception as e:
        logger.error(F"Exception occurred during evaluation task: {str(e)}\n{traceback.print_exc()}")


def evaluate_checked_claims_on_event_activation(claims: Union[QuerySet, List]):
    claims_for_evaluation = []
    if isinstance(claims, QuerySet):
        claims = claims.all()
    for c in claims:
        if c.status == Claim.STATUS_CHECKED:
            claims_for_evaluation.append(c)

    if ClaimAiQualityConfig.event_based_activation:
        #TODO: Use celery instead of threading
        t = threading.Thread(target=_send_submitted_claims, args=[claims_for_evaluation])
        t.setDaemon(True)
        t.start()
