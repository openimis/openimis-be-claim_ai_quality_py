import asyncio
import functools
import time
from abc import ABC

from typing import List, Coroutine

from django.db.models import Model

from claim_ai_quality.communication_interface.fhirConverter import FHIRBundleConverter
from core.websocket import AsyncWebSocketClient

def ensure_connection(socket_client):
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(self, *args, **kwargs):
            client = getattr(self, socket_client)
            if not client.is_open():
                raise ConnectionError("Connection has to be opened before sending data")
            return await func(self, *args, **kwargs)
        return wrapped

    return wrapper


class AbstractFHIRWebSocket(ABC):
    TIMEOUT = 3600

    def __init__(self, web_socket_client: AsyncWebSocketClient, fhir_converter: FHIRBundleConverter):
        self.server_client = web_socket_client
        self.fhir_converter = fhir_converter
        self.server_client.add_action_on_receive(self.on_receive)
        self.server_client.add_action_on_close(self.on_close)

        self.response_query = []
        self.running = False

    def open_connection(self):
        self.server_client.open_connection()

    def close_connection(self):
        self.server_client.close_connection()

    @ensure_connection("server_client")
    async def send_data_bundle(self, data_bundle: List[Model], data_type='data_bundle'):
        fhir_obj = self.fhir_converter.build_data_bundle(data_bundle)
        payload = {'type': data_type, 'content': fhir_obj}
        await self.server_client.send(payload)

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
