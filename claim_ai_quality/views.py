from claim import ClaimConfig
from claim.models import ClaimDetail, ClaimItem, ClaimService
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.utils.translation import gettext as _
from .report import template
# Create your views here.
from report.services import ReportService

from claim_ai_quality.services import AiQualityReportService


def miscategorisation_report(request):
    report_service = ReportService(request.user)
    report_data_service = AiQualityReportService(request.user)
    data = report_data_service.fetch(request.GET)

    all_valuated = 0
    result = {
        'true_positive': 0,
        'true_negative': 0,
        'false_positive': 0,
        'false_negative': 0,
    }
    errors = []
    for provided in data:
        statuses = provided.status, provided.json_ext['claim_ai_quality']['ai_result']
        if statuses == (ClaimDetail.STATUS_PASSED, '1'):
            result['true_positive'] += 1
        elif statuses == (ClaimDetail.STATUS_PASSED, '2'):
            result['false_negative'] += 1
        elif statuses == (ClaimDetail.STATUS_REJECTED, '1'):
            result['false_positive'] += 1
        elif statuses == (ClaimDetail.STATUS_REJECTED, '2'):
            result['true_negative'] += 1
        else:
            errors.append((
                provided.claim.code,
                provided.item.code if isinstance(provided, ClaimItem) else provided.service.code,
                statuses
            ))

        all_valuated += 1

    valid_evaluations = (result['true_positive'] + result['true_negative'])
    data = {
        'all': str(all_valuated),
        'accuracy': str(valid_evaluations / all_valuated) if all_valuated != 0 else 'N/A',
        **{str(k): str(v) for k, v in result.items()},
        **{F"{key}_percentage": F"{(value/all_valuated)*100:.2f}%" for key, value in result.items()
           if all_valuated}
    }

    if errors:
        data['errors'] = str(errors)

    return report_service.process('claim_ai_misclassification', data, template)
