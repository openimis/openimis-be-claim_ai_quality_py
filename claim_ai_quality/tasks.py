import asyncio
import logging
import traceback

from celery import shared_task

from .ai_evaluation.rest import RestAIEvaluationOrganizer
from .apps import ClaimAiQualityConfig

logger = logging.getLogger(__name__)


def ai_evaluation():
    try:
        RestAIEvaluationOrganizer.evaluate_all_eligible_claims()
    except Exception as e:
        logger.error(F"Exception occurred during evaluation task: {str(e)}\n{traceback.print_exc()}")


@shared_task(name='claim_ai_processing')
def claim_ai_processing():
    # In case of event based activation claims are sent after submission
    if not ClaimAiQualityConfig.event_based_activation:
        ai_evaluation()


@shared_task(name='pull_evaluated_tasks')
def pull_evaluated_tasks():
    # In case of event based activation claims are sent after submission
    if not ClaimAiQualityConfig.event_based_activation:
        RestAIEvaluationOrganizer.pull_data_for_not_evaluated_bundles()
