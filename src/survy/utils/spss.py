from typing import Literal

from survy.survey.question import Question, QuestionType
from survy.separator import MULTISELECT


def variable_labels(
    qtype: str, id: str, label: str, mapping: dict[str, int] = {}
) -> str:
    match qtype:
        case QuestionType.SELECT | QuestionType.NUMBER:
            return f"VARIABLE LABELS {id} '{label}'."
        case QuestionType.MULTISELECT:
            return "\n".join(
                [
                    f"VARIABLE LABELS {id}{MULTISELECT}{i} '[{op}] {label}'."
                    for op, i in mapping.items()
                ]
            )
        case _:
            raise KeyError("Can not identify question type")


def variable_level(
    qtype: str,
    id: str,
    level: Literal["NOMINAL", "ORDINAL", "SCALE"],
    mapping: dict[str, int] = {},
) -> str:
    match qtype:
        case QuestionType.MULTISELECT:
            return "\n".join(
                [
                    f"VARIABLE LEVEL {id}{MULTISELECT}{i} ({level})."
                    for i in mapping.values()
                ]
            )
        case _:
            return f"VARIABLE LEVEL {id} ({level})."


def value_labels(qtype: str, id: str, mapping: dict[str, int]) -> str:
    match qtype:
        case QuestionType.SELECT:
            op_map_str = "\n".join([f"{i} '{op}'" for op, i in mapping.items()])
            return f"VALUE LABELS {id} {op_map_str}."
        case QuestionType.MULTISELECT:
            return "\n".join(
                [
                    f"VALUE LABELS {id}{MULTISELECT}{i} 1 '{op}'."
                    for op, i in mapping.items()
                ]
            )
        case _:
            raise KeyError(f"Question type is not have value label: {qtype}")


def mrset(id: str, label: str, mapping: dict[str, int]) -> str:
    return f"""MRSETS /MDGROUP NAME=${id}
LABEL='{label}'
CATEGORYLABELS=COUNTEDVALUES VALUE=1
VARIABLES={" ".join([f"{id}{MULTISELECT}{i}" for _, i in mapping.items()])}
/DISPLAY NAME=[${id}]."""


def create_sps(questions: list[Question]):
    commands = []

    for question in questions:
        commands.append(
            variable_labels(
                question.qtype, question.id, question.label, question.mapping
            )
        )
        commands.append(value_labels(question.qtype, question.id, question.mapping))
        if question.qtype == QuestionType.MULTISELECT:
            commands.append(
                variable_level(question.qtype, question.id, "NOMINAL", question.mapping)
            )
            commands.append(mrset(question.id, question.label, question.mapping))
        elif question.qtype == QuestionType.SELECT:
            commands.append(
                variable_level(question.qtype, question.id, "NOMINAL", question.mapping)
            )
        elif question.qtype == QuestionType.NUMBER:
            commands.append(variable_level(question.qtype, question.id, "SCALE"))

    return "\n".join(commands)
