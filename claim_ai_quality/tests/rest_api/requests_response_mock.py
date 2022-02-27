import json
import os


class RequestsMocked:
    _TEST_EVALUATION_URL = "https://imis_test_evaluation_endpoint.com/test_evaluation"
    _TEST_EVALUATION_SERVER_LOGIN = "https://imis_test_evaluation_endpoint.com/login_endpoint"
    _SERVER_POST_RESPONSE = "/rest_api/not_evaluated_response_bundle.json"
    _SERVER_GET_RESPONSE = "/rest_api/evaluated_response.json"

    class MockResponse:
        def __init__(self, status, content):
            self.status_code = status
            self.content = content

    @staticmethod
    def _read_file_from_path(filename):
        dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        return open(dir_path + filename).read()

    @staticmethod
    def mocked_post(url=None, data=None, headers=None):
        if 'login' in url:
            return RequestsMocked \
                .MockResponse(200, json.dumps({'token': 'BEARER_TOKEN_FOR_USER'}))
        elif 'wait_for_evaluation' not in url:
            return RequestsMocked\
                .MockResponse(201, RequestsMocked._read_file_from_path(RequestsMocked._SERVER_POST_RESPONSE))
        else:
            return RequestsMocked\
                .MockResponse(201, RequestsMocked._read_file_from_path(RequestsMocked._SERVER_GET_RESPONSE))

    @staticmethod
    def mocked_get(url=None, headers=None):
        if 'wait_for_evaluation' not in url:
            return RequestsMocked\
                .MockResponse(201, RequestsMocked._read_file_from_path(RequestsMocked._SERVER_POST_RESPONSE))
        else:
            return RequestsMocked\
                .MockResponse(201, RequestsMocked._read_file_from_path(RequestsMocked._SERVER_GET_RESPONSE))

    @staticmethod
    def mocked_get(url=None, headers=None):
        return RequestsMocked\
                .MockResponse(200, RequestsMocked._read_file_from_path(RequestsMocked._SERVER_GET_RESPONSE))