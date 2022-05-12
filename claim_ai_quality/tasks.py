import logging
import time
import traceback

from celery import shared_task

from .ai_evaluation import ClaimEvaluationOrganizer
from .apps import ClaimAiQualityConfig

logger = logging.getLogger(__name__)


def ai_evaluation():
    try:
        ClaimEvaluationOrganizer.evaluate_all_eligible_claims()
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
        ClaimEvaluationOrganizer.pull_data_for_not_evaluated_bundles()


@shared_task
def pull_data_for_evaluation(evaluation_hash):
    # In seconds
    tries = 5
    initial_countdown = 10
    wait_ = initial_countdown
    for _ in range(tries):
        wait_ = wait_+wait_
        time.sleep(wait_)
        if not ClaimAiQualityConfig.event_based_activation:
            # Returns none if data was not updated
            fetched = ClaimEvaluationOrganizer.pull_data_for_bundle(evaluation_hash)
            if fetched is not None:
                break
