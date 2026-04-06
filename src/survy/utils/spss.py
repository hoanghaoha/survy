from typing import Literal

from survy.variable.variable import VarType
from survy.separators import MULTISELECT


def _clean_spss_str(s: str):
    return s.replace("'", "").replace('"', "")[:120]


def variable_labels(
    qtype: str, id: str, label: str, option_indices: dict[str, int] = {}
) -> str:
    """Generate SPSS VARIABLE LABELS syntax for a variable.

    Args:
        qtype (str):
            The variable type (e.g., SELECT, MULTISELECT, NUMBER).
        id (str):
            The base variable name.
        label (str):
            The descriptive label for the variable.
        option_indices (dict[str, int], optional):
            Mapping of option labels to numeric indices. Required for
            multi-select variables.

    Returns:
        str:
            SPSS syntax string for variable labels. Returns an empty string
            for multi-select variables if no option indices are provided.

    Behavior:
        - SELECT and NUMBER: Generates a single VARIABLE LABELS statement.
        - MULTISELECT: Generates one label per option using indexed variables.

    Examples:
        >>> variable_labels("SELECT", "Q1", "Age")
        "VARIABLE LABELS Q1 'Age'."

        >>> variable_labels("MULTISELECT", "Q2", "Hobbies", {"Sports": 1})
        "VARIABLE LABELS Q2_1 '[Sports] Hobbies'."
    """
    match qtype:
        case VarType.SELECT | VarType.NUMBER:
            return f"VARIABLE LABELS {id} '{_clean_spss_str(label)}'."
        case VarType.MULTISELECT:
            if not option_indices:
                return ""

            return "\n".join(
                [
                    f"VARIABLE LABELS {id}{MULTISELECT}{i} '{_clean_spss_str(f'[{op}] {label}')}'."
                    for op, i in option_indices.items()
                ]
            )
        case _:
            raise KeyError("Can not identify variable type")


def variable_level(
    qtype: str,
    id: str,
    level: Literal["NOMINAL", "ORDINAL", "SCALE"],
    option_indices: dict[str, int] = {},
) -> str:
    """Generate SPSS VARIABLE LEVEL syntax for a variable.

    Args:
        qtype (str):
            The variable type.
        id (str):
            The base variable name.
        level (Literal["NOMINAL", "ORDINAL", "SCALE"]):
            Measurement level in SPSS.
        option_indices (dict[str, int], optional):
            Mapping of option labels to indices for multi-select variables.

    Returns:
        str:
            SPSS syntax string defining variable measurement levels.

    Behavior:
        - MULTISELECT: Generates one VARIABLE LEVEL statement per option.
        - Other types: Generates a single statement for the variable.

    Examples:
        >>> variable_level("SELECT", "Q1", "NOMINAL")
        "VARIABLE LEVEL Q1 (NOMINAL)."

        >>> variable_level("MULTISELECT", "Q2", "NOMINAL", {"A": 1})
        "VARIABLE LEVEL Q2_1 (NOMINAL)."
    """
    match qtype:
        case VarType.MULTISELECT:
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
    """Generate SPSS VALUE LABELS syntax for a variable.

    Args:
        qtype (str):
            The variable type.
        id (str):
            The base variable name.
        option_indices (dict[str, int]):
            Mapping of option labels to numeric codes.

    Returns:
        str:
            SPSS syntax string for value labels. Returns an empty string
            if no option indices are provided.

    Behavior:
        - MULTISELECT: Assigns value label '1' for each option-specific variable.
        - Other types: Assigns labels to values within a single variable.

    Examples:
        >>> value_labels("SELECT", "Q1", {"Yes": 1, "No": 0})
        "VALUE LABELS Q1 1 'Yes'\\n0 'No'."

        >>> value_labels("MULTISELECT", "Q2", {"A": 1})
        "VALUE LABELS Q2_1 1 'A'."
    """
    if not option_indices:
        return ""

    match qtype:
        case VarType.MULTISELECT:
            return "\n".join(
                [
                    f"VALUE LABELS {id}{MULTISELECT}{i} 1 '{op.replace("'", '').replace('"', '')[:120]}'."
                    for op, i in option_indices.items()
                ]
            )
        case _:
            op_map_str = "\n".join(
                [f"{i} '{_clean_spss_str(op)}'" for op, i in option_indices.items()]
            )
            return f"VALUE LABELS {id} {op_map_str}."


def mrset(id: str, label: str, option_indices: dict[str, int]) -> str:
    """Generate SPSS MRSETS syntax for a multi-response set.

    Args:
        id (str):
            The base variable name for the multi-response set.
        label (str):
            Label describing the set.
        option_indices (dict[str, int]):
            Mapping of option labels to indices.

    Returns:
        str:
            SPSS MRSETS syntax string. Returns an empty string if no
            option indices are provided.

    Notes:
        - Defines a multiple dichotomy group (MDGROUP).
        - Assumes binary coding (1 = selected).
        - Uses indexed variable names (e.g., Q1_1, Q1_2).

    Examples:
        >>> mrset("Q1", "Hobbies", {"Sports": 1, "Music": 2})
        "MRSETS /MDGROUP NAME=$Q1
        LABEL='Hobbies'
        CATEGORYLABELS=COUNTEDVALUES VALUE=1
        VARIABLES=Q1_1 Q1_2
        /DISPLAY NAME=[$Q1]."
    """
    if not option_indices:
        return ""

    return f"""MRSETS /MDGROUP NAME=${id}
LABEL='{_clean_spss_str(label)}'
CATEGORYLABELS=COUNTEDVALUES VALUE=1
VARIABLES={" ".join([f"{id}{MULTISELECT}{i}" for _, i in option_indices.items()])}
/DISPLAY NAME=[${id}]."""


def ctables(id_type_map: dict[str, VarType]) -> str:
    """Generate SPSS CTABLES syntax for a set of survey variables.

    Args:
        id_type_map (dict[str, VarType]):
            Mapping of variable IDs to their variable types.

    Returns:
        str:
            SPSS CTABLES command string for tabulating variables.

    Behavior:
        - SELECT: Adds frequency counts.
        - MULTISELECT: Uses MRSET references (prefixed with `$`).
        - NUMBER: Adds mean calculations.

    Notes:
        - The generated syntax includes placeholders (e.g., "BY [Input Tabspec here]")
          that should be customized by the user.
        - Includes comparison tests for means and proportions.

    Examples:
        >>> ctables({"Q1": VarType.SELECT, "Q2": VarType.MULTISELECT})
        "CTABLES
        /TABLE
        Q1 [C][COUNT F40.0, TOTALS[COUNT F40.0] +
        $Q2 [C][COUNT F40.0, TOTALS[COUNT F40.0] +
        BY [Input Tabspec here]
        /SLABELS POSITION=ROW VISIBLE=NO
        /CATEGORIES VARIABLES=ALL
            EMPTY=INCLUDE TOTAL=YES POSITION=BEFORE
        /COMPARETEST TYPE=MEAN ALPHA=0.05 ADJUST=NONE ORIGIN=COLUMN INCLUDEMRSETS=YES
            CATEGORIES=ALLVISIBLE MEANSVARIANCE=TESTEDCATS MERGE=YES STYLE=SIMPLE SHOWSIG=NO
        /COMPARETEST TYPE=PROP ALPHA=0.05 ADJUST=NONE ORIGIN=COLUMN INCLUDEMRSETS=YES
            CATEGORIES=ALLVISIBLE MEANSVARIANCE=TESTEDCATS MERGE=YES STYLE=SIMPLE SHOWSIG=NO."
    """
    calculations = []
    for id, qtype in id_type_map.items():
        if qtype == VarType.SELECT:
            calculations.append(f"{id} [C][COUNT F40.0, TOTALS[COUNT F40.0]] +")
        elif qtype == VarType.MULTISELECT:
            calculations.append(f"${id} [C][COUNT F40.0, TOTALS[COUNT F40.0]] +")
        elif qtype == VarType.NUMBER:
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
    CATEGORIES=ALLVISIBLE MEANSVARIANCE=TESTEDCATS MERGE=YES STYLE=SIMPLE SHOWSIG=NO.
    """
