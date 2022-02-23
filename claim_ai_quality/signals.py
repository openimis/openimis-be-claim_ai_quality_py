from claim_ai_quality.event_based_evaluation import evaluate_checked_claims_on_event_activation
from claim_ai_quality.utils import add_json_ext_to_all_submitted_claims
from core.service_signals import ServiceSignalBindType
from core.signals import bind_service_signal


def bind_service_signals():
    bind_service_signal(
        'claim.enter_and_submit_claim', _evaluate_on_enter_and_submit_service, ServiceSignalBindType.AFTER)


def _evaluate_on_enter_and_submit_service(*args, **kwargs):
    submitted_claim = kwargs['result']
    as_list = [submitted_claim]
    add_json_ext_to_all_submitted_claims(as_list)
    evaluate_checked_claims_on_event_activation(as_list)
