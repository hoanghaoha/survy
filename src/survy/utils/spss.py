from typing import Literal

from survy.survey.question import QuestionType
from survy.separator import MULTISELECT


def variable_labels(
    qtype: str, id: str, label: str, option_indices: dict[str, int] = {}
) -> str:
    match qtype:
        case QuestionType.SELECT | QuestionType.NUMBER:
            return f"VARIABLE LABELS {id} '{label}'."
        case QuestionType.MULTISELECT:
            if not option_indices:
                return ""

            return "\n".join(
                [
                    f"VARIABLE LABELS {id}{MULTISELECT}{i} '[{op}] {label}'."
                    for op, i in option_indices.items()
                ]
            )
        case _:
            raise KeyError("Can not identify question type")


def variable_level(
    qtype: str,
    id: str,
    level: Literal["NOMINAL", "ORDINAL", "SCALE"],
    option_indices: dict[str, int] = {},
) -> str:
    match qtype:
        case QuestionType.MULTISELECT:
            if not option_indices:
                return ""

            return "\n".join(
                [
                    f"VARIABLE LEVEL {id}{MULTISELECT}{i} ({level})."
                    for i in option_indices.values()
                ]
            )
        case _:
            return f"VARIABLE LEVEL {id} ({level})."


def value_labels(qtype: str, id: str, option_indices: dict[str, int]) -> str:
    if not option_indices:
        return ""

    match qtype:
        case QuestionType.MULTISELECT:
            return "\n".join(
                [
                    f"VALUE LABELS {id}{MULTISELECT}{i} 1 '{op}'."
                    for op, i in option_indices.items()
                ]
            )
        case _:
            op_map_str = "\n".join([f"{i} '{op}'" for op, i in option_indices.items()])
            return f"VALUE LABELS {id} {op_map_str}."


def mrset(id: str, label: str, option_indices: dict[str, int]) -> str:
    if not option_indices:
        return ""

    return f"""MRSETS /MDGROUP NAME=${id}
LABEL='{label}'
CATEGORYLABELS=COUNTEDVALUES VALUE=1
VARIABLES={" ".join([f"{id}{MULTISELECT}{i}" for _, i in option_indices.items()])}
/DISPLAY NAME=[${id}]."""


def ctables(id_type_map: dict[str, QuestionType]) -> str:
    calculations = []
    for id, qtype in id_type_map.items():
        if qtype == QuestionType.SELECT:
            calculations.append(f"{id} [C][COUNT F40.0, TOTALS[COUNT F40.0]] +")
        elif qtype == QuestionType.MULTISELECT:
            calculations.append(f"${id} [C][COUNT F40.0, TOTALS[COUNT F40.0]] +")
        elif qtype == QuestionType.NUMBER:
            calculations.append(f"{id} [MEAN COMMA40.2] +")
    return f"""CTABLES
/TABLE
{"\n".join(calculations)}
BY [Input Tabspec here]
/SLABELS POSITION=ROW VISIBLE=NO
/CATEGORIES VARIABLES=ALL
    EMPTY=INCLUDE TOTAL=YES POSITION=BEFORE
/COMPARETEST TYPE=MEAN ALPHA=0.05 ADJUST=NONE ORIGIN=COLUMN INCLUDEMRSETS=YES
    CATEGORIES=ALLVISIBLE MEANSVARIANCE=TESTEDCATS MERGE=YES STYLE=SIMPLE SHOWSIG=NO
/COMPARETEST TYPE=PROP ALPHA=0.05 ADJUST=NONE ORIGIN=COLUMN INCLUDEMRSETS=YES
    CATEGORIES=ALLVISIBLE MEANSVARIANCE=TESTEDCATS MERGE=YES STYLE=SIMPLE SHOWSIG=NO
    """
