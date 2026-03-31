from enum import StrEnum


class QuestionType(StrEnum):
    SELECT = "select"
    MULTISELECT = "multiselect"
    NUMBER = "number"
    NULL = "null"
