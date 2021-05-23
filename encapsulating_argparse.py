from argparse import ArgumentParser, Namespace
from typing import Callable, Iterable, Union

class EncapsulatingParser(ArgumentParser):
    """
    A variant of ArgumentParser which allows for callbacks to be specified.
    EncapsulatingParser allows a parser to be assigned callbacks using
    the optional after_parse and after_full_parse parameters.

    These parameters each take either a
    Callable[[ArgumentParser, Namespace], None] or an iterable of those.

    The arguments to after_parse are called in order after any set of arguments
    are parsed by parse_args or parse_known_args.
    The arguments to after_full_parse are only called after ALL arguments
    have been parsed
    Their return values are all ignored - they exist to perform side effects or
    to modify the namespace in place
    """
    def __init__(self, *args,
            after_parse : Union[Callable[[ArgumentParser, Namespace], None], Iterable[Callable[[ArgumentParser, Namespace], None]]] = [],
            after_full_parse : Union[Callable[[ArgumentParser, Namespace], None], Iterable[Callable[[ArgumentParser, Namespace], None]]] = [],
            **kwargs):
        super(EncapsulatingParser, self).__init__(*args, **kwargs)

        if hasattr(after_parse, "__call__"):
            after_parse = [after_parse]
        else:
            after_parse = list(after_parse)

        if hasattr(after_full_parse, "__call__"):
            after_full_parse = [after_full_parse]
        else:
            after_full_parse = list(after_full_parse)

        for parent in kwargs.get("parents", []):
            try:
                after_parse = parent._after_parse + after_parse
            except AttributeError:
                pass
            try:
                after_full_parse = parent._after_full_parse + after_full_parse
            except AttributeError:
                pass

        self._after_parse = after_parse
        self._after_full_parse = after_full_parse

    def parse_known_args(self, *args, **kwargs) -> Namespace:
        namespace, unparsed_args = super(EncapsulatingParser, self).parse_known_args(*args, **kwargs)

        for callback in self._after_parse:
            callback(self, namespace)

        if not unparsed_args:
            for callback in self._after_full_parse:
                callback(self, namespace)

        return namespace, unparsed_args
