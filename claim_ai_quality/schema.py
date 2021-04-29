import asyncio
import logging
import threading
from datetime import datetime

import graphene
from claim.gql_mutations import SubmitClaimsMutation
from core.schema import signal_mutation_module_after_mutating, signal_mutation_module_validate
from claim.models import Claim
from django.dispatch import dispatcher

from claim_ai_quality.ai_evaluation import create_base_communication_interface, send_claims
from claim_ai_quality.apps import ClaimAiQualityConfig
from .gql_mutations import EvaluateByAIMutation, send_claims_to_evaluation
from .models import ClaimAiQualityMutation
from .utils import add_json_ext_to_all_submitted_claims, reset_sent_but_not_evaluated_claims

logger = logging.getLogger(__name__)


class Mutation(graphene.ObjectType):
    send_claims_for_ai_evaluation = EvaluateByAIMutation.Field()


def on_claim_ai_evaluation_mutation(sender, **kwargs):
    uuids = kwargs['data'].get('uuids', [])
    if not uuids:
        uuid = kwargs['data'].get('claim_uuid', None)
        uuids = [uuid] if uuid else []
    if not uuids:
        return []
    impacted_claims = Claim.objects.filter(uuid__in=uuids).all()
    for claim in impacted_claims:
        ClaimAiQualityMutation.objects.create(
            claim=claim, mutation_id=kwargs['mutation_log_id'])
    return []


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


def on_claim_submit_mutation(sender: dispatcher.Signal, **kwargs):
    mutation_type = sender._mutation_class

    if not mutation_type == SubmitClaimsMutation._mutation_class:
        return []

    uuids = kwargs['data'].get('uuids', [])
    if not uuids:
        uuid = kwargs['data'].get('claim_uuid', None)
        uuids = [uuid] if uuid else []
    if not uuids:
        return []

    claims = Claim.objects.filter(uuid__in=uuids)
    add_json_ext_to_all_submitted_claims(claims)
    claims_for_evaluation = []
    for c in claims.all():
        if c.status == Claim.STATUS_CHECKED:
            claims_for_evaluation.append(c)

    if ClaimAiQualityConfig.event_based_activation:
        t = threading.Thread(target=_send_submitted_claims,
                             args=[claims_for_evaluation])
        t.setDaemon(True)
        t.start()

    return []


def after_claim_ai_evaluation_validation(sender: dispatcher.Signal, **kwargs):
    mutation_type = sender._mutation_class

    if not mutation_type == EvaluateByAIMutation._mutation_class:
        return []

    uuids = kwargs['data'].get('uuids', [])
    if not uuids:
        uuid = kwargs['data'].get('claim_uuid', None)
        uuids = [uuid] if uuid else []
    if not uuids:
        return []

    claims = Claim.objects.filter(uuid__in=uuids)
    errors = send_claims_to_evaluation(claims)
    return errors or []


def bind_signals():
    signal_mutation_module_validate["claim_ai_quality"].connect(on_claim_ai_evaluation_mutation)
    signal_mutation_module_after_mutating["claim_ai_quality"].connect(after_claim_ai_evaluation_validation)
    signal_mutation_module_after_mutating["claim"].connect(on_claim_submit_mutation)
