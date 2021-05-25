from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from .apps import ClaimAiQualityConfig
from .report_template import template
from .report import MisclassificationReportBuilder
from report.services import ReportService

from claim_ai_quality.services import AiQualityReportService


def miscategorisation_report(request):
    if not request.user.has_perms(ClaimAiQualityConfig.misclassification_report_perms):
        raise PermissionDenied(_("unauthorized"))

    report_service = ReportService(request.user)
    report_data_service = AiQualityReportService(request.user)
    data = report_data_service.fetch(request.GET)
    report_builder = MisclassificationReportBuilder()
    return report_service.process('claim_ai_misclassification', report_builder.build_report_data(data), template)
