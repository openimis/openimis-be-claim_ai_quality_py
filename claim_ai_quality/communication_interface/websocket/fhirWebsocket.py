import asyncio
import functools
import concurrent.futures
import logging

from abc import ABC

from typing import List

import traceback
from django.db.models import Model

from claim_ai_quality.communication_interface.fhir.fhirConverter import ClaimBundleConverter
from core.websocket import AsyncWebSocketClient

logger = logging.getLogger(__name__)


def ensure_connection(socket_client):
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(self, *args, **kwargs):
            client = getattr(self, socket_client)
            if not client.is_open():
                await self._connection_lost()
                raise ConnectionError("Connection has to be opened before sending data")
            return await func(self, *args, **kwargs)
        return wrapped

    return wrapper


class AbstractFHIRWebSocket(ABC):
    """
    Abstract async websocket client used for sending imis objects through FHIR.
    """

    def __init__(self, web_socket_client: AsyncWebSocketClient, fhir_converter: ClaimBundleConverter):
        self.server_client = web_socket_client
        self.fhir_converter = fhir_converter
        self.server_client.add_action_on_receive(self.on_receive)
        self.server_client.add_action_on_close(self.on_close)

        self.response_query = {}
        self.running = False
        self.connection_lost = False

    async def open_connection(self):
        self.server_client.open_connection()

    def close_connection(self):
        self.server_client.close_connection()

    @ensure_connection("server_client")
    async def send_data_bundle(self, data_bundle: List[Model], data_type='data_bundle', bundle_id=None):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            kwargs = {}
            if bundle_id:
                kwargs["bundle_id"] = bundle_id
            executor.submit(self._send, data_bundle, data_type, **kwargs)

    def _send(self, data_bundle, data_type='data_bundle', **payload_args):
        try:
            fhir_obj = self.fhir_converter.build_claim_bundle(data_bundle)
            payload = {'type': data_type, 'content': fhir_obj, **payload_args}
            loop = asyncio.new_event_loop()
            loop.run_until_complete(self.server_client.send(payload))
        except Exception as e:
            logger.error(F"Error ocurred during payload fhir transformation, error: {e}")
            logger.debug(traceback.format_exc())
            self.close_connection()
            self.connection_lost = True

    async def on_receive(self, message):
        raise NotImplementedError("on_receive has to implemented")

    def on_close(self):
        pass

    async def lock_connection(self):
        self.running = True
        await self._connection_keeper()

    def release_connection(self):
        self.running = False

    async def _connection_keeper(self):
        while self.running:
            await asyncio.sleep(0)

    async def _connection_lost(self):
        logger.error(F"Websocket connection {self.server_client.socket_url} failed")
        self.connection_lost = True
        self.release_connection()
