import uuid

from django.db import models

from claim.models import Claim
from core import models as core_models
from core.datetimes.ad_datetime import datetime
from core.fields import DateTimeField
from core.models import HistoryModel, HistoryModelManager


class ClaimAiQualityMutation(core_models.UUIDModel):
    claim = models.ForeignKey(Claim, models.DO_NOTHING,
                              related_name='claim_ai_mutations')
    mutation = models.ForeignKey(
        core_models.MutationLog, models.DO_NOTHING, related_name='claims_ai_evaluation')

    class Meta:
        managed = True
        db_table = "claim_ai_quality_EvaluateByAIMutation"


class ClaimBundleEvaluationResultManager(HistoryModelManager):
    def not_evaluated_bundles(self):
        return self.get_queryset().filter(status__in=(0, 1))

    def successfully_evaluated_bundles(self):
        return self.get_queryset().filter(status=2)

    def incorrectly_evaluated_bundles(self):
        return self.get_queryset().filter(status=-1)


class ClaimBundleEvaluationResult(HistoryModel):
    """
    Similar to ClaimBundleEvaluation model in claim_ai.
    """

    class BundleEvaluationStatus(models.IntegerChoices):
        IDLE = 0
        STARTED = 1
        FINISHED = 2
        FAILED = -1

    evaluation_hash = \
        models.CharField(max_length=36, default=uuid.uuid4, unique=True, null=False)
    status = \
        models.IntegerField(choices=BundleEvaluationStatus.choices, default=BundleEvaluationStatus.IDLE, null=False)

    request_time = DateTimeField(db_column="RequestTime", default=datetime.now)
    response_time = DateTimeField(db_column="ResponseTime", null=True)

    objects = ClaimBundleEvaluationResultManager()


class BundleClaimEvaluationResult(models.Model):
    # One to many without direct reference in claim object
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name='bundle_evaluation', null=False)
    bundle_evaluation = models.ForeignKey(ClaimBundleEvaluationResult, on_delete=models.CASCADE, related_name='claims')
