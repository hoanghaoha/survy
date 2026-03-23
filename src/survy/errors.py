class BaseError(Exception):
    pass


class FileTypeError(BaseError):
    pass


class DataTypeError(BaseError):
    pass


class DataStructureError(BaseError):
    pass


class QuestionTypeError(BaseError):
    pass
