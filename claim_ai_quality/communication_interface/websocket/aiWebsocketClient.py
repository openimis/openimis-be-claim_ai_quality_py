import json
import zlib
from uuid import UUID
import orjson

import websocket
try:
    import thread
except ImportError:
    import _thread as thread

from core.websocket import AsyncWebSocketClient

from claim_ai_quality.apps import ClaimAiQualityConfig


class AiServerWebsocketClient(AsyncWebSocketClient):

    def __init__(self, socket_url, compressed_payload=None):
        super().__init__(socket_url)
        self.compressed_payload = compressed_payload or ClaimAiQualityConfig.zip_bundle

    def _transform_payload(self, payload: dict):
        def uuid_convert(o):
            if isinstance(o, UUID):
                return o.hex

        byte_payload = orjson.dumps(payload, default=uuid_convert)  # .encode('utf-8')
        if self.compressed_payload:
            byte_payload = zlib.compress(byte_payload)
        return byte_payload

    def open_connection(self):
        """
        Extends open_connection by adding custom headers
        """
        if not self.websocket:
            ws = websocket.WebSocketApp(
                self.socket_url,
                on_message=lambda ws, msg: self._on_recv(msg),
                header=self._get_auth()
            )
            self.websocket = ws
            thread.start_new_thread(self.websocket.run_forever, ())

    def _get_auth(self):
        token = ClaimAiQualityConfig.authentication_token
        return {'auth-token': token} if token else None
