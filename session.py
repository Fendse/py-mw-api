import warnings
import requests

from .errors import MediaWikiError, MediaWikiWarning


class MWApiSession(requests.Session):
    def __init__(self, api_root, *args, **kwargs):
        super(MWApiSession, self).__init__(*args, **kwargs)
        self.api_root = api_root

    def query(self, verbose=False, **kwargs):
        params = kwargs

        params["action"] = "query"
        params["format"] = "json"

        response = self.get(self.api_root, params=params)
        if verbose:
            print(response.url)
        response.raise_for_status()
        response_json = response.json()

        self._check_for_alerts(response_json)

        # TODO: Implement continue.

        return response_json


    def full_query(self, verbose=False, **kwargs):
        aggregate_data = {}
        continue_params = {}

        while True:
            full_response = self.query(verbose=verbose, **kwargs, **continue_params)
            response = full_response["query"]

            for key in response:
                if key not in aggregate_data:
                    aggregate_data[key] = response[key]
                elif type(aggregate_data[key]) is dict:
                    for k in response[key]:
                        aggregate_data[key][k] = response[key][k]
                elif type(aggregate_data[key]) is list:
                    aggregate_data[key] = aggregate_data[key] + response[key]
                elif aggregate_data[key] != response[key]:
                    warnings.warn(f"Single-value item {key} has divergent values in continued query: ({aggregate_data[key]}, {response[key]})", category=MWApiWarning)


            if "continue" not in full_response:
                break

            continue_params = full_response["continue"]
            del(continue_params["continue"])

        return aggregate_data


    def post_action(self, action, token_type="csrf", raw_response=False, **kwargs):
        payload = kwargs

        payload["action"] = action
        payload["format"] = "json"

        if token_type is not None:
            token_response = self.full_query(meta="tokens", type=token_type)
            token = token_response["tokens"][token_type+"token"]

            if action == "login":
                payload["lgtoken"] = token
            else:
                payload["token"] = token

        response = self.post(self.api_root, payload)
        response.raise_for_status()
        response_json = response.json()
        self._check_for_alerts(response_json)

        return response if raw_response else response_json

    def _check_for_alerts(self, response):
        if "warnings" in response:
            received_warnings = response["warnings"]
            for part in received_warnings:
                for warning_key in received_warnings[part]:
                    warnings.warn(received_warnings[part][warning_key], category=MediaWikiWarning, stacklevel=3)

        if "error" in response:
            raise MediaWikiError.from_response(response)