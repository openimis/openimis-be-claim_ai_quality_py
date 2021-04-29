import itertools

import core
import uuid
from claim.models import Claim, ClaimService, ClaimItem
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet, Q
from django.utils.translation import gettext as _
from typing import Union, Iterator


class AiQualityReportService(object):
    CATEGORIZED_FILTER = Q(json_ext__jsoncontains={'claim_ai_quality': {'was_categorized': True}})

    def __init__(self, user):
        self.user = user

    def fetch(self, request) -> Iterator[Union[QuerySet, Union[ClaimService, ClaimItem]]]:
        queryset = Claim.objects.filter(*core.filter_validity())
        if settings.ROW_SECURITY:
            from location.models import UserDistrict
            dist = UserDistrict.get_user_districts(self.user._u)
            queryset = queryset \
                .filter(health_facility__location_id__in=[l.location_id for l in dist]) \

        queryset = queryset.filter(self.CATEGORIZED_FILTER)  # exclude entered and checked claims from query

        if request.get('claimUuids', None):
            uuids = list(map(lambda str_id: uuid.UUID(str_id), request.get('claimUuids').split(',')))
            claims = queryset.filter(uuid__in=uuids)
        else:
            claims = queryset \
                .filter(**self.build_filter(request))

        if not claims:
            raise PermissionDenied(_("unauthorized"))

        return claims

    def build_filter(self, request):
        query = {}

        if request.get('adminUuid', None):
            query['admin__uuid'] = uuid.UUID(request.get('adminUuid'))
        if request.get('patientChfId', None):
            query['insuree__chf_id'] = request.get('patientChfId')
        if request.get('claimDateTo', None):
            query['date_claimed__lte'] = request.get('claimDateTo')
        if request.get('claimDateFrom', None):
            query['date_claimed__gte'] = request.get('claimDateFrom')
        if request.get('claimCode', None):
            query['code__startswith'] = request.get('claimCode')
        if request.get('claimStatus', None):
            query['status'] = request.get('claimStatus')
        if request.get('claimedUnder', None):
            query['claimed__lte'] = request.get('claimedUnder')
        if request.get('claimedAbove', None):
            query['claimed__gte'] = request.get('claimedAbove')
        if request.get('feedbackStatusCode', None):
            query['feedback_status'] = request.get('feedbackStatusCode')
        if request.get('medicalItemCode', None):
            query['items__item__code'] = request.get('medicalItemCode')
        if request.get('medicalServiceCode', None):
            query['services__service__code'] = request.get('medicalServiceCode')
        if request.get('visitDateFrom', None):
            query['date_from'] = request.get('visitDateFrom')
        if request.get('visitDateTo', None):
            query['date_to'] = request.get('visitDateTo')

        if request.get('healthFacilityUuid', None):
            query['health_facility__uuid'] = uuid.UUID(request.get('healthFacilityUuid'))
        elif request.get('districtUuid', None):
            query['health_facility__location_id'] = uuid.UUID(request.get('districtUuid'))
        elif request.get('regionUuid', None):
            query['health_facility__location__parent_uuid'] = uuid.UUID(request.get('regionUuid'))

        return query
