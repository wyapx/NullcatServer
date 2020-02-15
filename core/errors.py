class ClientException(Exception):
    pass


class UnknownTypeError(ClientException, ValueError):
    pass


class TooBigEntityError(ClientException):
    pass
