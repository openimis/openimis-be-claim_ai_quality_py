import asyncio
import logging

from celery import shared_task
from api_fhir_r4.serializers import ClaimSerializer
from .communication_interface import AiServerWebsocketClient, AiServerCommunicationInterface, ClaimBundleConverter
from .apps import ClaimAiQualityConfig


logger = logging.getLogger(__name__)


def ai_evaluation():
    async def connect(client):
        await client.open_connection()

    async def send_claims(client):
        await connect(client)

        sustain = asyncio.get_event_loop().create_task(client.lock_connection())
        send = asyncio.get_event_loop().create_task(client.sent_all())

        send.add_done_callback(
            lambda x: client.release_connection()
        )

        await asyncio.gather(
            sustain,
            send
        )

    socket_url = ClaimAiQualityConfig.claim_ai_url  # ClaimAiQualityConfig.claim_ai_url
    socket_client = AiServerWebsocketClient(socket_url=socket_url)
    communication_interface = AiServerCommunicationInterface(socket_client, ClaimBundleConverter(ClaimSerializer()))

    try:
        # Scheduled job require new loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        asyncio \
            .get_event_loop() \
            .run_until_complete(send_claims(communication_interface))
    except Exception as e:
        logger.error(F"Unknown exception occurred: {str(e)}")
    finally:
        communication_interface.close_connection()


@shared_task(name='claim_ai_processing')
def claim_ai_processing():
    asyncio.new_event_loop()
    ai_evaluation()
