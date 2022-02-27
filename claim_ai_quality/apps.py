from django.apps import AppConfig

MODULE_NAME = 'claim_ai_quality'

DEFAULT_CONFIG = {
    "rest_api_login_endpoint": "http://localhost:8000/api/api_fhir_r4/login/",
    "rest_api_bundle_evaluation_endpoint": "http://localhost:8000/api/claim_ai/claim_bundle_evaluation/",
    "rest_api_single_claim_evaluation_endpoint": "http://localhost:8000/api/claim_ai/claim_evaluation/",
    "wait_for_evaluation": True,  # Determines if during sending REST Requests interface wants to wait for response.

    "rest_api_user_login": 'claim_ai_admin',  # Used for JWT Authentication on Claim AI Server
    "rest_api_user_password": 'claim_ai_admin',  # Used for JWT Authentication on Claim AI Server

    "claim_ai_username": '_ClaimAIAdmin',  # User dedicated to perform db operations on history model e.g. save
    "event_based_activation": False,
    "bundle_size": 200,
    "request_time_resend_after_hours": 15,
    "accepted_category_code": '0',
    "rejected_category_code": '1',
    "reason_rejected_by_ai_code": -2,
    "date_format": '%Y-%m-%d',
    "claim_evaluation_error_log_path": 'claim_ai_evaluation.log',
    "misclassification_report_perms": ["112001"],
    # One of "integrated", "rest_api", if not set integrated evaluation is used, if claim_ai module is installed.
    "evaluation_method": ""
}


class ClaimAiQualityConfig(AppConfig):
    name = MODULE_NAME

    event_based_activation = DEFAULT_CONFIG["event_based_activation"]
    bundle_size = DEFAULT_CONFIG["bundle_size"]
    rejected_category_code = DEFAULT_CONFIG["rejected_category_code"]
    accepted_category_code = DEFAULT_CONFIG["accepted_category_code"]
    reason_rejected_by_ai_code = DEFAULT_CONFIG["reason_rejected_by_ai_code"]
    date_format = DEFAULT_CONFIG['date_format']
    request_time_resend_after_hours = DEFAULT_CONFIG['request_time_resend_after_hours']
    claim_evaluation_error_log_path = DEFAULT_CONFIG['claim_evaluation_error_log_path']
    misclassification_report_perms = DEFAULT_CONFIG['misclassification_report_perms']

    rest_api_login_endpoint = DEFAULT_CONFIG['rest_api_login_endpoint']
    rest_api_bundle_evaluation_endpoint = DEFAULT_CONFIG['rest_api_bundle_evaluation_endpoint']
    rest_api_single_claim_evaluation_endpoint = DEFAULT_CONFIG['rest_api_single_claim_evaluation_endpoint']

    rest_api_user_login = DEFAULT_CONFIG['rest_api_single_claim_evaluation_endpoint']
    rest_api_user_password = DEFAULT_CONFIG['rest_api_single_claim_evaluation_endpoint']

    wait_for_evaluation = DEFAULT_CONFIG['wait_for_evaluation']

    claim_ai_username = DEFAULT_CONFIG['claim_ai_username']

    evaluation_method = DEFAULT_CONFIG['evaluation_method']


    def _configure_perms(self, cfg):
        for config, config_value in cfg.items():
            setattr(ClaimAiQualityConfig, config, config_value)

    def ready(self):
        from core.models import ModuleConfiguration
        cfg = ModuleConfiguration.get_or_default(MODULE_NAME, DEFAULT_CONFIG)
        self._configure_perms(cfg)
