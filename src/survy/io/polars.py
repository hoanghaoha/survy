from typing import Iterable
import warnings
from dataclasses import dataclass, field
import polars

from survy.separator import LOOP
from survy.survey.question import Question
from survy.survey.survey import Survey
from survy.utils.functions import parse_id


@dataclass
class PolarReader:
    compact_ids: list[str]
    compact_separator: str
    name_pattern: str
    data: dict = field(default_factory=dict)
    type_map: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def _process_list(li: list) -> list:
        return sorted([i for i in li if i])

    def _parse_id(self, id: str) -> tuple[str, str | None, str | None]:
        parsed_items = parse_id(id, self.name_pattern)
        return parsed_items["id"], parsed_items.get("loop"), parsed_items.get("multi")

    def _read_multi(self, id: str, data: Iterable, loop_id: str | None) -> None:
        if loop_id:
            self.type_map[id] = "multi_loop"
            self.data.setdefault(id, {})
            self.data[id].setdefault(loop_id, [])
            self.data[id][loop_id].append(data)
        else:
            self.type_map[id] = "multi"
            self.data.setdefault(id, [])
            self.data[id].append(data)

    def _read_multi_compact(
        self, id: str, data: Iterable[str | None], loop_id: str | None
    ) -> None:
        splitted_data = [
            PolarReader._process_list(d.split(self.compact_separator)) if d else []
            for d in data
        ]

        if loop_id:
            self.type_map[id] = "multi_compact_loop"
            self.data.setdefault(id, {})
            self.data[id][loop_id] = splitted_data
        else:
            self.type_map[id] = "multi_compact"
            self.data[id] = splitted_data

    def _read_normal(self, id: str, data: Iterable, loop_id: str | None) -> None:
        data = [d if d != "" else None for d in data]
        if loop_id:
            self.type_map[id] = "normal_loop"
            self.data.setdefault(id, {})
            self.data[id][loop_id] = data
        else:
            self.type_map[id] = "normal"
            self.data[id] = data

    def _read_series(self, series: polars.Series) -> None:
        if series.dtype == polars.Null:
            warnings.warn(f"{series.name} is null")

        id, loop_id, multi_id = self._parse_id(series.name)
        if id in self.compact_ids:
            self._read_multi_compact(id, series.to_list(), loop_id)
        elif multi_id:
            self._read_multi(id, series.to_list(), loop_id)
        else:
            self._read_normal(id, series.to_list(), loop_id)

    def read_df(self, df: polars.DataFrame):
        for column in df.columns:
            series = df[column]
            self._read_series(series)

    def to_survey(self) -> Survey:
        def _from_normal(id: str, values: list):
            return Question(series=polars.Series(id, values))

        def _from_normal_loop(id: str, values: dict):
            questions = []
            for index, loop_id in enumerate(values.keys(), 1):
                question = Question(
                    series=polars.Series(f"{id}{LOOP}{index}", values[loop_id])
                )
                question.loop_id = loop_id
                questions.append(question)
            return questions

        def _from_multi(id: str, values: list):
            return Question(
                series=polars.Series(
                    id, [PolarReader._process_list(list(d)) for d in zip(*values)]
                )
            )

        def _from_multi_loop(id: str, values: dict):
            questions = []
            for index, loop_id in enumerate(values.keys(), 1):
                question = Question(
                    series=polars.Series(
                        f"{id}{LOOP}{index}",
                        [
                            PolarReader._process_list(list(d))
                            for d in zip(*values[loop_id])
                        ],
                    )
                )
                question.loop_id = loop_id
                questions.append(question)
            return questions

        def _from_multi_compact(id: str, values: list):
            return Question(series=polars.Series(id, values))

        def _from_multi_compact_loop(id: str, values: dict):
            questions = []
            for index, loop_id in enumerate(values.keys(), 1):
                question = Question(
                    series=polars.Series(f"{id}{LOOP}{index}", values[loop_id])
                )
                question.loop_id = loop_id
                questions.append(question)
            return questions

        functions = {
            "normal": _from_normal,
            "normal_loop": _from_normal_loop,
            "multi": _from_multi,
            "multi_loop": _from_multi_loop,
            "multi_compact": _from_multi_compact,
            "multi_compact_loop": _from_multi_compact_loop,
        }

        questions = []
        for id, values in self.data.items():
            type_ = self.type_map[id]
            result = functions[type_](id, values)
            if isinstance(result, list):
                questions.extend(result)
            else:
                questions.append(result)

        return Survey(questions=questions)


def read_polars(
    raw_df: polars.DataFrame,
    compact_ids: list[str] = [],
    compact_separator: str = ";",
    name_pattern: str = "id(.loop)?(_multi)?",
):
    reader = PolarReader(compact_ids, compact_separator, name_pattern)
    reader.read_df(raw_df)
    return reader.to_survey()
