from collections import defaultdict, namedtuple
from functools import lru_cache
from datetime import datetime

from claim import ClaimConfig
from claim.models import ClaimDetail, ClaimItem, ClaimService, Claim
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.utils.translation import gettext as _
from typing import Union
from claim_ai_quality.apps import ClaimAiQualityConfig

from .report_template import template
from .report import MisclassificationReportBuilder
# Create your views here.
from report.services import ReportService

from claim_ai_quality.services import AiQualityReportService


def miscategorisation_report(request):
    report_service = ReportService(request.user)
    report_data_service = AiQualityReportService(request.user)
    data = report_data_service.fetch(request.GET)
    report_builder = MisclassificationReportBuilder()
    return report_service.process('claim_ai_misclassification', report_builder.build_report_data(data), template)
