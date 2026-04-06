from typing import Iterable
import warnings
from dataclasses import dataclass, field
import polars

from survy.variable.variable import Variable
from survy.survey.survey import Survey
from survy.utils.functions import parse_id


@dataclass
class PolarReader:
    compact_ids: list[str]
    compact_separator: str
    auto_detect: bool
    name_pattern: str
    data: dict = field(default_factory=dict)
    type_map: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def _process_list(li: list) -> list:
        return sorted([i for i in li if i])

    def _parse_id(self, id: str) -> tuple[str, str | None]:
        parsed_items = parse_id(id, self.name_pattern)
        return parsed_items["id"], parsed_items.get("multi")

    def _read_multi(self, id: str, data: Iterable) -> None:
        self.type_map[id] = "multi"
        self.data.setdefault(id, [])
        self.data[id].append(data)

    def _read_multi_compact(self, id: str, data: Iterable[str | None]) -> None:
        splitted_data = [
            PolarReader._process_list(d.split(self.compact_separator)) if d else []
            for d in data
        ]

        self.type_map[id] = "multi_compact"
        self.data[id] = splitted_data

    def _read_normal(self, id: str, data: Iterable) -> None:
        data = [d if d != "" else None for d in data]
        self.type_map[id] = "normal"
        self.data[id] = data

    def _read_series(self, series: polars.Series) -> None:
        id, multi_id = self._parse_id(series.name)
        data = series.to_list()
        if id in self.compact_ids:
            self._read_multi_compact(id, data)
        elif self.auto_detect and any([self.compact_separator in str(d) for d in data]):
            self._read_multi_compact(id, data)
        elif multi_id:
            self._read_multi(id, data)
        else:
            self._read_normal(id, data)

    def read_df(self, df: polars.DataFrame):
        for column in df.columns:
            series = df[column]
            self._read_series(series)

    def to_survey(self, exclude_null: bool = True) -> Survey:
        def _from_normal(id: str, values: list):
            return Variable(series=polars.Series(id, values))

        def _from_multi(id: str, values: list):
            return Variable(
                series=polars.Series(
                    id, [PolarReader._process_list(list(d)) for d in zip(*values)]
                )
            )

        def _from_multi_compact(id: str, values: list):
            return Variable(series=polars.Series(id, values))

        functions = {
            "normal": _from_normal,
            "multi": _from_multi,
            "multi_compact": _from_multi_compact,
        }

        variables = []
        for id, values in self.data.items():
            type_ = self.type_map[id]
            result = functions[type_](id, values)
            variables.append(result)

        excluded_variables = []
        for variable in variables:
            if variable.series.dtype == polars.Null:
                if exclude_null:
                    warnings.warn(
                        f"Variable {variable.id} with no responses will be excluded"
                    )
                    excluded_variables.append(variable.id)
                else:
                    warnings.warn(f"Read Null Variable {variable.id}")

            if variable.series.dtype == polars.List and all(
                [d == [] for d in variable.series.to_list()]
            ):
                if exclude_null:
                    warnings.warn(
                        f"MULTISELECT Variable {variable.id} with no responses will be excluded"
                    )
                    excluded_variables.append(variable.id)
                else:
                    warnings.warn(f"Read Empty Variable {variable.id}")

        return Survey(
            variables=[
                variable
                for variable in variables
                if variable.id not in excluded_variables
            ]
        )


def read_polars(
    raw_df: polars.DataFrame,
    compact_ids: list[str] | None = None,
    compact_separator: str = ";",
    auto_detect: bool = False,
    name_pattern: str = "id(_multi)?",
    exclude_null: bool = True,
) -> Survey:
    """
    Convert a Polars DataFrame into a Survey object.

    This is the main entry point for reading survey data.

    Args:
        raw_df (polars.DataFrame): Input data.
        compact_ids (list[str] | None):
            IDs of variables using compact multi-select encoding.
        compact_separator (str):
            Separator for compact multi-select values.
        auto_detect (bool):
            Auto parse multi-select if data have compact_separator.
        name_pattern (str):
            Pattern for parsing column names into id/multi components.
        exclude_null (bool):
            Default True, exclude Null columns or Empty List columns

    Returns:
        Survey: Parsed survey object.
    """
    compact_ids = compact_ids or []
    reader = PolarReader(compact_ids, compact_separator, auto_detect, name_pattern)
    reader.read_df(raw_df)
    return reader.to_survey(exclude_null)
