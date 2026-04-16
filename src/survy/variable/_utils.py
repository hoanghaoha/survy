from enum import StrEnum


class VarType(StrEnum):
    """
    Enumeration of supported survey variable types.

    Members:
        SELECT:
            Single-choice categorical question.
            Each response contains one selected option.

        MULTISELECT:
            Multiple-choice varibale.
            Each response may contain multiple selected options (typically as a list).

        NUMBER:
            Numeric variable.
            Responses are treated as continuous or discrete numeric values.
    """

    SELECT = "select"
    MULTISELECT = "multiselect"
    NUMBER = "number"
