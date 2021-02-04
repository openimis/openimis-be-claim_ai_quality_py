from collections import namedtuple, defaultdict
from datetime import datetime
from functools import lru_cache

from claim.models import Claim, ClaimDetail, ClaimItem, ClaimService

from claim_ai_quality.apps import ClaimAiQualityConfig


class MisclassificationReportBuilder:
    ClaimKey = namedtuple('ClaimErrorKey', [
        'claim_id', 'claim_status', 'claim_claimed', 'claim_approved',
        'hf', 'hf_code', 'hf_name', 'location_name', 'location_code',
        'date', 'visit_from', 'visit_to', 'insuree_number', 'insuree_name', 'claim_admin'
    ])

    def __init__(self):
        self.clear_report_data()

    def create_report_data(self, from_data):
        self.clear_report_data()
        data = from_data

        unique_claims = set()
        errors = defaultdict(lambda: [])
        for provided in data:
            claim_status, ai_result = provided.status, provided.json_ext['claim_ai_quality']['ai_result']
            correctly_classified = self._categorize_item_status(claim_status, ai_result)

            if not correctly_classified:
                key = self.missclassified_record_key(provided.claim)
                errors[key].append(self.false_evaluation_entry(key, provided))

            self.total_items_and_services += 1
            unique_claims.add(provided.claim.id)

        self.total_claims = len(unique_claims)
        self.accuracy = (self.true_positive+self.true_negative) / self.total_items_and_services
        self.missclassified_records = self.build_list_of_errors(errors)

    def build_report_data(self, items_and_services):
        self.create_report_data(items_and_services)
        return {
            'all': str(self.total_items_and_services),
            'total_claims': str(self.total_claims),
            'accuracy': self._percentage_repr(self.accuracy),
            'true_positive_percentage': self._percentage_repr(self.true_positive/self.total_items_and_services),
            'true_negative_percentage': self._percentage_repr(self.true_negative/self.total_items_and_services),
            'false_positive_percentage': self._percentage_repr(self.false_positive/self.total_items_and_services),
            'false_negative_percentage': self._percentage_repr(self.false_negative/self.total_items_and_services),
            'list': self.missclassified_records
        }

    def _percentage_repr(self, value):
        return F"{value * 100:.2f}%" if value != 0 else '-'

    @lru_cache(maxsize=None)
    def missclassified_record_key(self, claim: Claim):
        insuree = claim.insuree
        admin = claim.admin
        return self.ClaimKey(**{
            'claim_id': claim.code,
            'claim_status': str(claim.status),
            'claim_claimed': claim.claimed,
            'claim_approved': claim.approved,
            'hf': claim.health_facility.name,
            'hf_code': claim.health_facility.code,
            'hf_name': claim.health_facility.name,
            'location_name': claim.health_facility.location.name,
            'location_code': claim.health_facility.location.code,
            'date': datetime.strftime(claim.date_claimed, ClaimAiQualityConfig.date_format),
            'visit_from': datetime.strftime(claim.date_from, ClaimAiQualityConfig.date_format),
            'visit_to': datetime.strftime(claim.date_to, ClaimAiQualityConfig.date_format),
            'insuree_number': insuree.chf_id,
            'insuree_name': F"{insuree.other_names} {insuree.last_name}",
            'claim_admin': F"{admin.other_names} {admin.last_name}",
        })

    def clear_report_data(self):
        self.true_positive = 0
        self.true_negative = 0
        self.false_positive = 0
        self.false_negative = 0
        self.total_claims = 0
        self.total_items_and_services = 0
        self.accuracy = 0
        self.missclassified_records = []

    def _categorize_item_status(self, claim_status, ai_result):
        statuses = (claim_status, ai_result)
        if statuses == (ClaimDetail.STATUS_PASSED, '1'):
            self.true_positive += 1
            return True
        elif statuses == (ClaimDetail.STATUS_REJECTED, '2'):
            self.true_negative += 1
            return True
        elif statuses == (ClaimDetail.STATUS_PASSED, '2'):
            self.false_negative += 1
            return False
        elif statuses == (ClaimDetail.STATUS_REJECTED, '1'):
            self.false_positive += 1
            return False
        else:
            pass

    def false_evaluation_item(self, provided: ClaimItem):
        item = provided.item
        return self.__provided_entry(provided, item.code)

    def false_evaluation_service(self, provided: ClaimService):
        service = provided.service
        return self.__provided_entry(provided, service.code)

    def false_evaluation_entry(self, key, provided):
        return self.false_evaluation_item(provided) if isinstance(provided, ClaimItem) \
            else self.false_evaluation_service(provided)

    def __provided_entry(self, provided, code):
        print(provided.price_approved)
        return {
            'code': code,
            'quantity': provided.qty_provided,
            'quantity_approved': provided.qty_approved,
            'price': provided.price_asked,
            'price_approved': provided.price_approved or provided.price_asked,
            'justification': provided.justification or '-',
            'rejection_reason': str(provided.rejection_reason),
            'ai_result': str(provided.json_ext['claim_ai_quality']['ai_result'])
        }

    def build_list_of_errors(self, errors):
        list_of_items = []
        for k, v in errors.items():
            for next_item in v:
                print(k._asdict())
                print(next_item)
                item = {**k._asdict(), **next_item}
                list_of_items.append(item)
        return list_of_items
