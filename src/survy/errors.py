class BaseError(Exception):
    pass


class ParseError(BaseError):
    pass


class FileTypeError(BaseError):
    pass


class DataTypeError(BaseError):
    pass


class DataStructureError(BaseError):
    pass


class VarTypeError(BaseError):
    pass
