import asyncio
import concurrent.futures

from collections import Iterable

from api_fhir_r4.serializers import ClaimSerializer
from asgiref.sync import async_to_sync

from claim_ai_quality.apps import ClaimAiQualityConfig
from claim_ai_quality.communication_interface import AiServerWebsocketClient, AiServerCommunicationInterface, \
    ClaimBundleConverter


def create_base_communication_interface():
    socket_url = ClaimAiQualityConfig.claim_ai_url  # ClaimAiQualityConfig.claim_ai_url
    socket_client = AiServerWebsocketClient(socket_url=socket_url)
    return AiServerCommunicationInterface(socket_client, ClaimBundleConverter(ClaimSerializer()))


async def await_connection(client):
    while not client.server_client.is_open():
        await asyncio.sleep(0)
        pass


async def connect(client):
    await client.open_connection()


async def send_claims(client, claims=None):
    def __new_send_task_with_connection_release(send_method, *send_args, **send_kwargs):
        send = asyncio.get_event_loop().create_task(send_method(*send_args, **send_kwargs))
        send.add_done_callback(lambda x: client.release_connection())
        return send

    await connect(client)

    try:
        await asyncio.wait_for(await_connection(client), ClaimAiQualityConfig.connection_timeout)
    except concurrent.futures.TimeoutError as e:
        raise TimeoutError("AI Server connection timeout")

    tasks = []
    lock = asyncio.get_event_loop().create_task(client.lock_connection())
    tasks.append(lock)
    if not claims:
        tasks.append(
            __new_send_task_with_connection_release(client.send_all)
        )
    elif isinstance(claims, Iterable):
        tasks.append(
            __new_send_task_with_connection_release(client.send_bundle_async, list(claims))
        )
    else:
        raise TypeError(F"{type(claims)} is not iterable. Use iterable type for send bundle of claims "
                        F"or None for send all uncategorized claims")

    await asyncio.gather(
        *tasks
    )
