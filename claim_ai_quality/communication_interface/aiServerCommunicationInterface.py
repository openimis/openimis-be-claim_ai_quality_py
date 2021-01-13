import asyncio
import json
import time
import zlib

from claim.models import Claim
from core.websocket import AsyncWebSocketClient
from itertools import groupby
from claim_ai_quality.communication_interface.fhirWebsocketClient import AbstractFHIRWebSocket


class AiServerCommunicationInterface(AbstractFHIRWebSocket):

    async def sent_all(self):
        self.response_query = {}
        for index, next_bundle in enumerate(self._get_imis_data(), start=0):
            self.response_query[index] = 'Sent'
            await self.send_data_bundle(next_bundle, data_type='claim.bundle.payload')
        await self._sustain_conneciton()

    async def on_receive(self, message):
        # TODO: should send information: about received responsebundle and update claims
        await self.__dispatch(message)

    def update_claims(self, fhir_claim_response):
        # TODO: Use claim repose adjudication for update
        print("Content of payload hash: " + str(str(fhir_claim_response).__hash__()))
        pass

    def update_response_query(self):
        self.response_query.pop()

    def _get_imis_data(self):
        # TODO: Should yield chunks of uncategorised claims
        return iter( [[Claim()], [Claim()]])

    async def __dispatch(self, payload):
        payload = json.loads(payload)
        if payload['type'] == 'claim.bundle.payload':
            self.update_claims(payload['content'])
            bundle_index = payload['index']
            self.response_query[bundle_index] = 'Valuated'
            await self.server_client.send({'type': 'claim.bundle.acceptance', 'content': True})
        elif payload['type'] == 'claim.bundle.acceptance':
            bundle_index = payload['index']
            self.response_query[bundle_index] = 'Accepted'
            print("Bundle was accepted")
        else:
            print("Uncategorized payload: "+str(payload))

    async def _sustain_conneciton(self):
        # Keeps loop alive untill all bundles were evaluated
        while True:
            unique_bundle_statuses = groupby(self.response_query.values())
            element, _ = next(unique_bundle_statuses, (None, None))
            if element == 'Valuated' \
                    and not next(unique_bundle_statuses, False)\
                    and self.server_client.is_open():
                break
            continue
