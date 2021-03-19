import asyncio
import logging
import traceback

from celery import shared_task

from .ai_evaluation import send_claims, create_base_communication_interface
from .apps import ClaimAiQualityConfig
from .utils import add_json_ext_to_all_submitted_claims, reset_sent_but_not_evaluated_claims

logger = logging.getLogger(__name__)


def ai_evaluation():
    reset_sent_but_not_evaluated_claims()
    communication_interface = create_base_communication_interface()
    try:
        # Scheduled job require new loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        asyncio \
            .get_event_loop() \
            .run_until_complete(send_claims(communication_interface))
    except Exception as e:
        logger.error(F"Exception occurred during evaluation task: {str(e)}\n{traceback.print_exc()}")
    finally:
        communication_interface.close_connection()


@shared_task(name='claim_ai_processing')
def claim_ai_processing():
    # In case of event based activation claims are sent after submision
    if not ClaimAiQualityConfig.event_based_activation:
        # Ensure json_ext fields are available
        add_json_ext_to_all_submitted_claims()
        asyncio.new_event_loop()
        ai_evaluation()
