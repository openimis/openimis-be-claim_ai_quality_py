import json
import asyncio
from abc import ABC

from typing import Callable, Dict

from asgiref.sync import sync_to_async
from django.db import transaction


class AbstractPayloadHandler(ABC):
    @property
    def type_handlers(self) -> Dict[str, Callable]:
        raise NotImplementedError('Type handlers not implemented')

    def handle_payload(self, payload):
        payload_type = payload.get('type', '')
        return self.type_handlers.get(payload_type, 'default')(payload)

    def dispatch(self, payload: str):
        payload = json.loads(payload)
        self.handle_payload(payload)


class AIResponsePayloadHandlerMixin(AbstractPayloadHandler):

    @property
    def type_handlers(self) -> Dict[str, Callable]:
        return {
            'claim.bundle.payload': self.claim_response_bundle,
            'claim.bundle.acceptance': self.acceptance,
            'claim.bundle.evaluation_exception': self.evaluation_exception,
            'bundle.authentication_exception': self.authentication_exception,
            'default': self.default,
        }

    def claim_response_bundle(self, payload):
        task = sync_to_async(self.update_claims)(payload['content'])
        asyncio.ensure_future(task)
        index = payload.get('index', None)
        self.update_response_query(index, 'Valuated')
        asyncio.ensure_future(self.server_client.send({'type': 'claim.bundle.acceptance', 'content': index}))

    @transaction.atomic
    def update_claims(self, fhir_claim_response):
        update = self.fhir_converter.update_claims_by_response_bundle(fhir_claim_response)
        print(F"Claims updated: {update}, Content of payload hash: " + str(str(fhir_claim_response).__hash__()))

    def acceptance(self, payload):
        self.update_response_query(payload.get('index', None), 'Accepted')
        print("Bundle was accepted")

    def evaluation_exception(self, payload):
        self.update_response_query(payload.get('index', None), 'Refused')
        print(F"Bundle rejected, reason: {payload['content']}")

    def authentication_exception(self, payload):
        print(F"Connection rejected, reason: {payload['content']}")
        raise ConnectionError("Invalid authentication token")

    def default(self, payload):
        print("Uncategorized payload: "+str(payload))

    def update_response_query(self, bundle_index, new_status):
        if not bundle_index or not new_status:
            # Response payload didn't affect bundle query
            return
        else:
            self.response_query[bundle_index] = new_status

    @property
    def _response_type_bundle_status(self):
        return {
            'claim.bundle.payload': 'Valuated',
            'claim.bundle.acceptance': 'Accepted',
            'claim.bundle.evaluation_exception': 'Refused'
        }

