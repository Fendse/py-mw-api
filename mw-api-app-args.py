from encapsulating_argparse import EncapsulatingParser
import requests


class MWApiParser(EncapsulatingParser):
    password_option_strings = ["--password"]
    token_option_strings = ["--login-token", "--token"]
    
    def __init__(self, after_full_parse=[], **kwargs):
        try:
            iter(after_full_parse)
        except TypeError:
            after_full_parse = [after_full_parse, MWApiParser._login]
        else:
            after_full_parse = after_full_parse + [MWApiParser._login]
        
        super(MWApiParser, self).__init__(after_full_parse=after_full_parse, **kwargs)
        self.add_argument("API_root", type=str, metavar="API-ROOT")
        self.add_argument("--timeout", "-t", type=float, metavar="TIMEOUT")

        auth_mutex = self.add_mutually_exclusive_group()
        self.add_argument("--user", "--username", type=str, metavar="USERNAME", default=argparse.SUPPRESS)
        auth_mutex.add_argument(*(MWApiArgumentParser.password_option_strings), type=str, metavar="PASSWORD", default=argparse.SUPPRESS)
        auth_mutex.add_argument("--token", "--login-token", "-t", type=str, metavar="LOGIN-TOKEN", default=argparse.SUPPRESS)

    def _login(namespace):
        has_password = hasattr(namespace, "password")
        has_token = hasattr(namespace, "token")
        has_username = hasattr(namespace, "username")
        
        if has_password and has_token:
            self.error("Password and login token must not both be specified")
        elif has_username and not has_token and not has_password:
            self.error("Username must not be specified without a password or token")
        elif has_password and not has_username:
            self.error("Password must not be present without a username")

        do_login = any(has_password, has_token, has_username)
            
        namespace.session = requests.Session()

        if do_login:
            login_params = {
                "action": "login",
                "format": "json"
            }

            if has_password:      
                # Password login
                login_params["lgname"] = namespace.username
                login_params["lgpassword"] = namespace.password
            elif has_token:
                # Token login
                login_params["lgtoken"] = namespace.token

            namespace.session.post(namespace.API_root, login_params)

        userinfo_params = {
            "action": "query",
            "format": "json",
            "meta": "userinfo",
            "uiprop": "rights"
        }

        userinfo = namespace.session.get(namespace.API_root, userinfo_params).json()["query"]["userinfo"]
        if has_username and session.username != userinfo["name"]:
            self.error(f"Attempted to log in as user {session.username} but instead logged in as user {userinfo['name']}")

        namespace.username = userinfo["name"]
        namespace.userrights = userinfo["rights"]
        namespace.logged_in = "anon" in userinfo
        if has_password:
            del(namespace.password)
        if has_token:
            del(namespace.token)
