import sys
import warnings
from typing import Iterable, List, Optional

from requests import Session

from .errors import MediaWikiError, MediaWikiWarning


class MWApiSession(Session):
    def __init__(self, api_root : str, *args, **kwargs):
        """
        Create a connection to the MediaWiki wiki at api_root.
        api_root should be a URL with no query string
        """
        super(MWApiSession, self).__init__(*args, **kwargs)
        self.api_root = api_root

        self._interesting_user_properties = set()
        self._userinfo = self._update_userinfo([])


    def _uiprop(self, prop : str) -> Optional[str]:
        if self._userinfo is None or str not in self._userinfo:
            self._update_userinfo([prop])

        return self._userinfo.get(prop, None)


    @property
    def usergroups(self) -> List[str]:
        """
        A list of groups the currently logged-in user belongs to,
        including the special '*' group, even if not logged in.
        """

        return self._uiprop("groups")


    @property
    def userrights(self) -> List[str]:
        """
        The permissions of the currently logged in user, or
        the permissions granted to everyone if nobody is logged in
        """
        return self._uiprop("rights")


    @property
    def userid(self) -> int:
        if self._userinfo is None:
            self._update_userinfo()

        return self._userinfo["id"]


    @property
    def username(self) -> str:
        """
        The username of the currently logged in user.
        If not logged in, this will instead be the user's IP address.
        """
        if self._userinfo is None:
            self._update_userinfo()

        return self._userinfo["name"]


    @property
    def logged_in(self) -> bool:
        """
        Whether a user is logged in in this session.
        """
        if self._userinfo is None:
            self._update_userinfo()

        return "anon" not in self._userinfo


    def _update_userinfo(self, properties : Iterable[str] = set()) -> None:
        """
        Submit a meta=userinfo query
        """

        self._interesting_user_properties.update(properties)

        self._userinfo = self.full_query(meta="userinfo", uiprop='|'.join(self._interesting_user_properties))["userinfo"]


    def login(self, username, password):
        login_response = self.post_action("login", token_type="login", token_key="lgtoken", lgname=username, lgpassword=password)["login"]

        if login_response["result"] != "Success":
            # Result was probably "Failed"
            # May have been "WrongToken"
            # "Needtoken" has been observed, but shouldn't occur
            raise MediaWikiError(login_response["result"], login_response["reason"], "")

        print(f"Logged in as user {login_response['lgusername']} (ID: {login_response['lguserid']})", file=sys.stderr)

        self._update_userinfo()


    def logout(self):
        self.post_action("logout")

        self._update_userinfo()


    def query(self, verbose=False, **kwargs):
        """
        Submit a query action
        """
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
                    warnings.warn(f"Single-value item {key} has divergent values in continued query: ({aggregate_data[key]}, {response[key]})", category=MediaWikiWarning)


            if "continue" not in full_response:
                break

            continue_params = full_response["continue"]
            del(continue_params["continue"])

        return aggregate_data


    def post_action(self,
            action,
            token_type = "csrf",
            token_key = "token",
            raw_response = False,
            allow_anonymous = False,
            **kwargs):

        if not allow_anonymous and not self.logged_in:
            raise RuntimeError("Action not permitted while logged out")

        payload = kwargs

        payload["action"] = action
        payload["format"] = "json"

        if token_type is not None:
            token_response = self.full_query(meta="tokens", type=token_type)
            token = token_response["tokens"][token_type+"token"]

            payload[token_key] = token

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
