import asyncio
import logging
from datetime import datetime

from claim.gql_mutations import SubmitClaimsMutation
from core.schema import signal_mutation_module_after_mutating
from claim.models import Claim
from django.dispatch import dispatcher

from claim_ai_quality.ai_evaluation import create_base_communication_interface, send_claims
from claim_ai_quality.apps import ClaimAiQualityConfig
from .utils import add_json_ext_to_all_submitted_claims, reset_sent_but_not_evaluated_claims

logger = logging.getLogger(__name__)


def _send_submitted_claims(submitted_claims_bundle):
    if not submitted_claims_bundle:
        logger.info("No claims submitted for AI evaluation")
        return

    reset_sent_but_not_evaluated_claims()
    communication_interface = create_base_communication_interface()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio \
        .get_event_loop() \
        .run_until_complete(send_claims(communication_interface, submitted_claims_bundle))


def on_claim_mutation(sender: dispatcher.Signal, **kwargs):
    mutation_type = sender._mutation_class

    if not mutation_type == SubmitClaimsMutation._mutation_class:
        return

    uuids = kwargs['data'].get('uuids', [])
    if not uuids:
        uuid = kwargs['data'].get('claim_uuid', None)
        uuids = [uuid] if uuid else []
    if not uuids:
        return []

    claims = Claim.objects.filter(uuid__in=uuids)
    all_submitted_claims = add_json_ext_to_all_submitted_claims()
    for c in claims.all():
        if c not in all_submitted_claims:
            all_submitted_claims.append(c)

    if ClaimAiQualityConfig.event_based_activation:
        _send_submitted_claims(all_submitted_claims)

    return []


def bind_signals():
    signal_mutation_module_after_mutating["claim"].connect(on_claim_mutation)
