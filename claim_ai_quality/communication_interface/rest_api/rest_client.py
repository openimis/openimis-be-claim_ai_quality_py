import decimal
import urllib
import uuid
from urllib.parse import urlparse, urlunparse

import orjson
import requests

from claim_ai_quality.apps import ClaimAiQualityConfig


class ClaimRestApiRequestClient:
    @property
    def BUNDLE_EVALUATION_ENDPOINT(self):
        v = ClaimAiQualityConfig.rest_api_bundle_evaluation_endpoint
        return v if v.endswith('/') else F"{v}/"

    @property
    def CLAIM_EVALUATION_ENDPOINT(self):
        v = ClaimAiQualityConfig.rest_api_single_claim_evaluation_endpoint
        return v if v.endswith('/') else F"{v}/"

    @property
    def LOGIN_ENDPOINT(self):
        v = ClaimAiQualityConfig.rest_api_login_endpoint
        return v if v.endswith('/') else F"{v}/"

    def send_claim_bundle(self, claim_bundle: dict, wait_for_response: bool = False):
        response = self._post_request(
            endpoint_url=self.BUNDLE_EVALUATION_ENDPOINT,
            payload=claim_bundle,
            query_params={'wait_for_evaluation': wait_for_response}
        )
        if response.status_code >= 400:
            raise ConnectionError(
                f"Sending data to Server has failed with code {response.status_code}: ", response.content)
        content = response.content
        return orjson.loads(content)

    def get_claim_bundle(self, claim_bundle_evaluation_hash):
        response = self._get_request(self.BUNDLE_EVALUATION_ENDPOINT, claim_bundle_evaluation_hash)
        return orjson.loads(response.content)

    def _post_request(self,  endpoint_url: str, payload: dict, query_params=None):
        payload_json = self.__transform_payload(payload)
        if query_params is None:
            query_params = {}

        endpoint_url = self.__add_qury_param(endpoint_url, query_params)
        return requests.post(endpoint_url, data=payload_json, headers=self._get_headers())

    def _get_request(self, endpoint_url: str, resource_id: str, query_params=None):
        if query_params is None:
            query_params = {}

        if not endpoint_url.endswith('/'):
            endpoint_url = F"{endpoint_url}/"
        endpoint_url = F"{endpoint_url}{resource_id}"
        endpoint_url = self.__add_qury_param(endpoint_url, query_params)
        return requests.get(endpoint_url, headers=self._get_headers())

    def __add_qury_param(self, url, query_params):
        url_parts = list(urlparse(url))
        url_parts[4] = urllib.parse.urlencode(query_params)  # Query
        return urlunparse(url_parts)

    def _get_headers(self):
        token = self.__get_bearer_token()
        headers = {
            "Content-Type": "application/json",
            'Authorization': f"Bearer {token}"
        }
        return headers

    def __get_bearer_token(self):
        # TODO: Fetch this once and wait until expire
        credentials = {
            "username": ClaimAiQualityConfig.rest_api_user_login,
            "password": ClaimAiQualityConfig.rest_api_user_password
        }
        url = self.LOGIN_ENDPOINT

        response = requests.post(url, data=credentials)
        if response.status_code != 200:
            raise ConnectionError("Invalid login to AI Server, details: ", response.content)
        return orjson.loads(response.content)['token']

    def __transform_payload(self, payload: dict):
        def uuid_convert(o):
            if isinstance(o, uuid.UUID):
                return o.hex
            if isinstance(o, decimal.Decimal):
                return float(o)

        return orjson.dumps(payload, default=uuid_convert)
