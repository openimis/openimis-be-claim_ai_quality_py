import logging

import graphene

from claim_ai_quality.ai_evaluation import ClaimEvaluationOrganizer
from core.schema import OpenIMISMutation

logger = logging.getLogger(__name__)


class EvaluateByAIMutation(OpenIMISMutation):
    _mutation_module = "claim_ai_quality"
    _mutation_class = "EvaluateByAIMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        return ClaimEvaluationOrganizer.evaluate_claims_from_mutation(user=user, **data)
