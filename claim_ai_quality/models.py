from django.db import models

from core import models as core_models
from claim.models import Claim


class ClaimAiQualityMutation(core_models.UUIDModel):
    claim = models.ForeignKey(Claim, models.DO_NOTHING,
                              related_name='claim_ai_mutations')
    mutation = models.ForeignKey(
        core_models.MutationLog, models.DO_NOTHING, related_name='claims_ai_evaluation')

    class Meta:
        managed = True
        db_table = "claim_ai_quality_EvaluateByAIMutation"
