from .session import MWApiSession
from .encapsulating_argparse import EncapsulatingParser
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

