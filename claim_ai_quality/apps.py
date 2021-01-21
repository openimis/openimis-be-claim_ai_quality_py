from django.apps import AppConfig

MODULE_NAME = 'claim_ai_quality'

DEFAULT_CONFIG = {
    "claim_ai_url": "",
    "event_based_activation": False,
    "bundle_size": 100,
    "zip_bundle": False
}


class ClaimAiQualityConfig(AppConfig):
    name = MODULE_NAME

    claim_ai_url = "ws://localhost:8000/claim_ai/ws/Claim/process/"
    event_based_activation = False
    bundle_size = 100
    zip_bundle = False

    def _configure_perms(self, cfg):
        ClaimAiQualityConfig.claim_ai_url = cfg.get("claim_ai_url", "ws://localhost:8000/claim_ai/ws/Claim/process/")
        ClaimAiQualityConfig.event_based_activation = cfg.get("event_based_activation", False)
        ClaimAiQualityConfig.bundle_size = cfg.get("bundle_size", 100)
        ClaimAiQualityConfig.zip_bundle = cfg.get('zip_bundle', False)

    def ready(self):
        from core.models import ModuleConfiguration
        cfg = ModuleConfiguration.get_or_default(MODULE_NAME, DEFAULT_CONFIG)
        self._configure_perms(cfg)

