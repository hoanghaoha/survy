from enum import StrEnum


class QuestionType(StrEnum):
    """
    Enumeration of supported survey question types.

    Members:
        SELECT:
            Single-choice categorical question.
            Each response contains one selected option.

        MULTISELECT:
            Multiple-choice question.
            Each response may contain multiple selected options (typically as a list).

        NUMBER:
            Numeric question.
            Responses are treated as continuous or discrete numeric values.
    """

    SELECT = "select"
    MULTISELECT = "multiselect"
    NUMBER = "number"
