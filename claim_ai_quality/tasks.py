import asyncio

from claim.models import Claim
from .communication_interface import AiServerWebsocketClient, AiServerCommunicationInterface, FHIRBundleConverter


def claim_ai_processing():
    claims_to_send = Claim.objects.filter(json_ext__jsoncontains={'was_categorized': False, 'request_time': None})

    for claim in claims_to_send:
        pass


def ai_evaluation():
    async def send_claims(client):
        client.open_connection()
        sustain = asyncio.get_event_loop().create_task(client.lock_connection())
        send = asyncio.get_event_loop().create_task(client.sent_all())
        send.add_done_callback(
            lambda x: client.release_connection()
        )

        await asyncio.gather(
            sustain,
            send
        )

    socket_url = "ws://localhost:8001/claim_ai/ws/Claim/process1/"  # ClaimAiQualityConfig.claim_ai_url
    socket_client = AiServerWebsocketClient(socket_url=socket_url)
    communication_interface = AiServerCommunicationInterface(socket_client, FHIRBundleConverter())

    communication_interface.open_connection()

    try:
        asyncio \
            .get_event_loop() \
            .run_until_complete(send_claims(communication_interface))
    finally:
        communication_interface.close_connection()
        print('Task finished, connection status:' + str(socket_client.is_open()))
