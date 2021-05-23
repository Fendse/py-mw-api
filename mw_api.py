from encapsulating_argparse import EncapsulatingParser
import argparse
import requests
import warnings
import sys


class MWApiParser(EncapsulatingParser):
    def __init__(self, after_full_parse=[], **kwargs):
        try:
            iter(after_full_parse)
        except TypeError:
            after_full_parse = [after_full_parse, MWApiParser._login]
        else:
            after_full_parse = after_full_parse + [MWApiParser._login]
        
        super(MWApiParser, self).__init__(after_full_parse=after_full_parse, **kwargs)
        self.add_argument("API_root", type=str, metavar="API-ROOT")

        self.add_argument("--username", "--user", type=str, metavar="USERNAME", default=argparse.SUPPRESS)
        auth_mutex = self.add_mutually_exclusive_group()
        auth_mutex.add_argument("--password", type=str, metavar="PASSWORD", default=argparse.SUPPRESS)
        # TODO: Allow reading password from a file

        self.add_argument("--assert", type=str, choices=["user", "bot"])

    def _login(parser, namespace):
        has_password = hasattr(namespace, "password")
        has_username = hasattr(namespace, "username")

        namespace.session = MWApiSession(namespace.API_root)

        if has_username and has_password:
            login_response = namespace.session.post_action("login", token_type="login", lgname=namespace.username, lgpassword=namespace.password)["login"]

            if login_response["result"] == "Failed":
                parser.error(f"Token login failed with reason: {login_response['reason']}")
            elif login_response["result"] == "WrongToken":
                parser.error("Invalid login token")
            elif login_response["result"] == "NeedToken":
                parser.error("Token login returned result NeedToken.")
                print(login_response)
            elif login_response["result"] == "Success":
                print(f"Logged in as user {login_response['lgusername']} (ID: {login_response['lguserid']})", file=sys.stderr)
            else:
                parser.error(login_response)
        elif has_username:
            parser.error("Missing argument: PASSWORD")
        elif has_password:
            parser.error("Missing argument: USERNAME")

        userinfo_params = {
            "action": "query",
            "format": "json",
            "meta": "userinfo",
            "uiprop": "rights"
        }

        userinfo = namespace.session.full_query(meta="userinfo", uiprop="rights")["userinfo"]

        namespace.username = userinfo["name"]
        namespace.userrights = userinfo["rights"]
        namespace.logged_in = "anon" not in userinfo
        if has_password:
            del(namespace.password)


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
                break;

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
