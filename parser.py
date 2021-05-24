from .session import MWApiSession
from .encapsulating_argparse import EncapsulatingParser
import argparse
import warnings
import sys


class MWApiParser(EncapsulatingParser):
    def __init__(self, api_root=None, after_full_parse=[], **kwargs):
        try:
            iter(after_full_parse)
        except TypeError:
            after_full_parse = [after_full_parse, MWApiParser._login]
        else:
            after_full_parse = after_full_parse + [MWApiParser._login]
        
        super(MWApiParser, self).__init__(after_full_parse=after_full_parse, **kwargs)

        if api_root is None:
            self.add_argument("API_root", type=str, metavar="API_ROOT")
        else:
            self.add_argument("--api-root", type=str, metavar="API_ROOT", default=api_root, dest="API_root")

        self.add_argument("--username", "--user", type=str, metavar="USERNAME", default=argparse.SUPPRESS)
        auth_mutex = self.add_mutually_exclusive_group()
        auth_mutex.add_argument("--password", type=str, metavar="PASSWORD", default=argparse.SUPPRESS)
        auth_mutex.add_argument("--password-file", metavar="PASSWORD_FILE", type=str, default=argparse.SUPPRESS)

        self.add_argument("--assert", type=str, choices=["user", "bot"])

    def _login(parser, namespace):
        has_password = hasattr(namespace, "password") or hasattr(namespace, "password_file")
        has_username = hasattr(namespace, "username")

        namespace.session = MWApiSession(namespace.API_root)

        if has_username and has_password:
            if (hasattr(namespace, "password")):
                password = namespace.password
                del(namespace.password)
            else:
                with open(namespace.password_file, "rt") as password_file:
                    password = password_file.read()
                del(namespace.password_file)
            namespace.session.login(namespace.username, password)
            del(namespace.username)
        elif has_username:
            del(namespace.username)
            parser.error("Must not specify --username without either --password or --password-file")
        elif has_password:
            del(namespace.password)
            parser.error("Must not specify --password or --password-file without --username")

