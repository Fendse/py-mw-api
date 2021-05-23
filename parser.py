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
            namespace.session.login(namespace.username, namespace.password)
            del(namespace.username)
            del(namespace.password)
        elif has_username:
            del(namespace.username)
            parser.error("Missing argument: PASSWORD")
        elif has_password:
            del(namespace.password)
            parser.error("Missing argument: USERNAME")

