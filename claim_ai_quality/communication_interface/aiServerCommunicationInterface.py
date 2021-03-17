import asyncio
import uuid

from asgiref.sync import sync_to_async
from claim.models import Claim
from itertools import groupby
from datetime import datetime
from django.core.paginator import Paginator

from . import AIResponsePayloadHandlerMixin
from .websocket import AbstractFHIRWebSocket
from ..apps import ClaimAiQualityConfig


class AiServerCommunicationInterface(AIResponsePayloadHandlerMixin, AbstractFHIRWebSocket):

    async def send_all(self):
        self.response_query = {}
        data = await self._get_imis_data()  # generator of paginated data
        next_bundle = await self._get_from_iterator(data)  # first bundle of claims

        while next_bundle:
            asyncio.ensure_future(self.__async_bundle_send(next_bundle))
            next_bundle = await self._get_from_iterator(data)

    async def __async_bundle_send(self, next_bundle):
        bundle_id = str(uuid.uuid4())
        self.response_query[bundle_id] = 'Sent'
        self.send_bundle(next_bundle, bundle_id)
        await self.sustain_connection()

    async def on_receive(self, message):
        await self.__dispatch(message)

    async def send_bundle_async(self, bundle):
        bundle_id = str(uuid.uuid4())
        self.response_query[bundle_id] = 'Sent'
        self.send_bundle(bundle, bundle_id)
        await self.sustain_connection()

    def send_bundle(self, bundle, bundle_id=None):
        if not bundle_id:
            bundle_id = str(uuid.uuid4())

        loop = asyncio.get_event_loop()
        task = loop.create_task(self.send_data_bundle(bundle, data_type='claim.bundle.payload', bundle_id=bundle_id))
        for claim in bundle:
            claim.json_ext['claim_ai_quality']['request_time'] = datetime.now()

        asyncio.ensure_future(task)

    async def _get_async_data(self):
        coro = sync_to_async(self._get_imis_data)()
        task = asyncio.create_task(coro)
        return await task

    @sync_to_async
    def _get_imis_data(self):
        queryset = Claim.objects\
            .filter(json_ext__jsoncontains={'claim_ai_quality': {'was_categorized': False}},
                    validity_to__isnull=True)\
            .filter(json_ext__jsoncontains={'claim_ai_quality': {'request_time': None}}) \
            .prefetch_related("items") \
            .prefetch_related("services") \
            .order_by('id')\
            .all()
        paginator = Paginator(queryset, ClaimAiQualityConfig.bundle_size)
        for page in range(1, paginator.num_pages + 1):
            yield paginator.page(page).object_list

    @sync_to_async
    def _get_from_iterator(self, queryset):
        chunk = next(queryset, None)
        if not chunk:
            return None
        return list(chunk)

    async def __dispatch(self, payload):
        self.dispatch(payload)

    async def sustain_connection(self):
        # Keeps loop alive until all bundles were evaluated and connection is open
        while True:
            unique_bundle_statuses = groupby(self.response_query.values())
            element, _ = next(unique_bundle_statuses, (None, None))
            # All sent bundles were evaluated
            if element in ('Valuated', 'Refused') \
                    and not next(unique_bundle_statuses, False)\
                    and self.server_client.is_open():
                break
            # Connection was lost
            if self.connection_lost:
                break
            await asyncio.sleep(0)
            continue
