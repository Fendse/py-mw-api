import argparse

class EncapsulatingParser(argparse.ArgumentParser):
    """
    A subclass of argparse.ArgumentParser which allows for callbacks to be specified.
    In addition to all functionality provided by argparse.ArgumentParser, CustomParser
    allows a parser to be assigned callbacks using the after_parse and after_full_parse
    parameters.

    after_parse takes a list of callables. Each of those will be called, taking the parser and the namespace as positional parameters, after any set of arguments have been parsed.
    after_full_parse takes a list of callables. Each of those will be called, taking the parser and the namespace as positional parameters, only after ALL arguments have been parsed.

    The return values of these functions are all ignored. They exist to perform side effects or to modify the namespace in place.

    Instead of an iterable, after_parse or after_full_parse can be specified as a single callable.
    """
    def __init__(self, *args, after_parse=[], after_full_parse=[], **kwargs):
        super(EncapsulatingParser, self).__init__(*args, **kwargs)
        try:
            iter(after_parse)
        except TypeError:
            after_parse = [after_parse]
        try:
            iter(after_full_parse)
        except TypeError:
            after_full_parse = [after_full_parse]

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
                
    def parse_known_args(self, *args, **kwargs):
        namespace, unparsed_args = super(EncapsulatingParser, self).parse_known_args(*args, **kwargs)

        for callback in self._after_parse:
            callback(self, namespace)
            
        if not unparsed_args:
            for callback in self._after_full_parse:
                callback(self, namespace)
                            
        return namespace, unparsed_args
