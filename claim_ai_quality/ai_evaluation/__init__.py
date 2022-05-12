from django.utils.module_loading import import_string


def __load_organizer(organizer):
    try:
        if organizer == 'integrated':
            return import_string(
                'claim_ai_quality.ai_evaluation.integrated_evaluation_organizer.IntegratedClaimAIEvaluationOrganizer'
            )
        elif organizer == 'rest_api':
            return import_string(
                'claim_ai_quality.ai_evaluation.rest_organizer.RestAIEvaluationOrganizer'
            )
    except ImportError as e:
        raise ImportError(
            F"Failed to load custom Claim AI Evaluation organizer of type {organizer}.\n"
            F"If integrated solution is used make sure claim_ai module is installed. \nError: {e}") from e


def __get_organizer():
    from ..apps import ClaimAiQualityConfig
    evaluation_method_from_config = ClaimAiQualityConfig.evaluation_method
    if evaluation_method_from_config:
        return __load_organizer(evaluation_method_from_config)
    else:
        from django.conf import settings
        installed_applications = settings.INSTALLED_APPS
        if 'claim_ai' in installed_applications:
            return __load_organizer('integrated')
        else:
            return __load_organizer('rest_api')


ClaimEvaluationOrganizer = __get_organizer()
