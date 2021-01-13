import json
import zlib

from core.websocket import AsyncWebSocketClient

from claim_ai_quality.apps import ClaimAiQualityConfig


class AiServerWebsocketClient(AsyncWebSocketClient):

    def __init__(self, socket_url, compressed_payload=None):
        super().__init__(socket_url)
        self.compressed_payload = compressed_payload or ClaimAiQualityConfig.zip_bundle

    def _transform_payload(self, payload: dict):
        byte_payload = json.dumps(payload).encode('utf-8')
        if self.compressed_payload:
            byte_payload = zlib.compress(byte_payload)
        return byte_payload
