from typing import Optional


class MediaWikiWarning(RuntimeWarning):
    pass # TODO


class MediaWikiError(Exception):
    def __init__(self, code : str, info : str, details : Optional[str] = None):
        msg = f"{code}: {info}"

        if details is not None:
            msg += f"\n{details}"

        super().__init__(msg)
        self.code = code
        self.info = info
        self.details = details

    def from_response(response):
        code = response["error"]["code"]
        info = response["error"]["info"]
        details = response["error"]["*"]
        return MediaWikiError(code, info, details)