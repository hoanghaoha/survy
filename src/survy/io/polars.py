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
    """Convert a Polars DataFrame into a Survey object.

    This is the main entry point for reading survey data that is already
    loaded in memory as a Polars DataFrame. It detects and merges
    multiselect variables from two possible raw formats:

    **Wide format** — each answer option occupies its own column with a
    shared prefix and a separator-delimited numeric suffix
    (e.g. ``hobby_1``, ``hobby_2``). These are detected automatically
    via ``name_pattern``.

    **Compact format** — all selected answers are stored in a single cell
    joined by a delimiter (e.g. ``"Sport;Book"``). These must be declared
    explicitly via ``compact_ids`` or discovered via ``auto_detect``.

    After reading, both formats produce the same internal representation:
    a ``MULTISELECT`` variable whose data is a sorted list of chosen values
    per respondent.

    Args:
        raw_df (polars.DataFrame):
            Input data. Each column becomes a variable or is merged into
            a multiselect variable depending on the detection parameters.

        compact_ids (list[str] | None):
            Column IDs to treat as compact multiselect. Each listed column's
            cell values are split on ``compact_separator`` to recover
            individual choices. Do not combine with ``auto_detect=True``.

        compact_separator (str):
            Delimiter used inside compact multiselect cells.
            Also used by ``auto_detect`` to scan for compact columns.

        auto_detect (bool):
            If ``True``, every column is scanned for the presence of
            ``compact_separator`` in its values. Any column containing the
            separator in at least one cell is treated as compact multiselect.
            Do not combine with ``compact_ids``.

        name_pattern (str):
            Format template for parsing column names into wide multiselect
            groups. This is **not** a raw regex — it uses two named tokens:

            - ``id`` — matches the base variable name
            - ``multi`` — matches the numeric suffix

            The recognized separators between tokens are ``_``, ``.``,
            and ``:``. The template is converted internally into a regex
            by ``parse_id()``.

            Examples of how columns are parsed with the default pattern
            ``"id(_multi)?"``:

            - ``"hobby_1"`` → ``id="hobby"``, ``multi="1"`` (grouped)
            - ``"hobby_2"`` → ``id="hobby"``, ``multi="2"`` (grouped)
            - ``"gender"``  → ``id="gender"``, no ``multi`` (normal column)

            To match a different separator convention, change the template::

                # Columns named Q1.1, Q1.2, Q2.1, ...
                name_pattern="id.multi"

                # Columns named Q1:a, Q1:b, ...
                name_pattern="id:multi"

        exclude_null (bool):
            If ``True`` (default), columns where all values are null or
            all multiselect lists are empty are dropped from the resulting
            Survey with a warning. Set to ``False`` to keep them.

    Returns:
        Survey: Parsed survey object with variables inferred from the
        input DataFrame.

    Raises:
        Warning:
            If ``exclude_null=True`` and a column has no valid responses.

    Examples:
        **Wide + compact mixed input:**

        >>> df = polars.DataFrame(
        ...     {
        ...         "gender": ["Male", "Female", "Male"],
        ...         "yob": [2000, 1999, 1998],
        ...         "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
        ...         "animal_1": ["Cat", "", "Cat"],
        ...         "animal_2": ["Dog", "Dog", ""],
        ...     }
        ... )
        >>> print(df)
        shape: (3, 5)
        ┌────────┬──────┬─────────────┬──────────┬──────────┐
        │ gender ┆ yob  ┆ hobby       ┆ animal_1 ┆ animal_2 │
        │ ---    ┆ ---  ┆ ---         ┆ ---      ┆ ---      │
        │ str    ┆ i64  ┆ str         ┆ str      ┆ str      │
        ╞════════╪══════╪═════════════╪══════════╪══════════╡
        │ Male   ┆ 2000 ┆ Sport;Book  ┆ Cat      ┆ Dog      │
        │ Female ┆ 1999 ┆ Sport;Movie ┆          ┆ Dog      │
        │ Male   ┆ 1998 ┆ Movie       ┆ Cat      ┆          │
        └────────┴──────┴─────────────┴──────────┴──────────┘

        Using ``compact_ids`` to specify the compact column explicitly
        (``animal`` is auto-detected as wide via ``name_pattern``):

        >>> survey = read_polars(df, compact_ids=["hobby"])
        >>> print(survey)
        Survey (4 variables)
            Variable(id=gender, ...)
            Variable(id=yob, ...)
            Variable(id=hobby, ...)
            Variable(id=animal, ...)

        Using ``auto_detect`` instead (scans all columns for ``;``):

        >>> survey = read_polars(df, auto_detect=True, compact_separator=";")

        Both approaches produce the same result:

        >>> print(survey.get_df())
        shape: (3, 4)
        ┌────────┬──────┬────────────────────┬────────────────┐
        │ gender ┆ yob  ┆ hobby              ┆ animal         │
        │ ---    ┆ ---  ┆ ---                ┆ ---            │
        │ str    ┆ i64  ┆ list[str]          ┆ list[str]      │
        ╞════════╪══════╪════════════════════╪════════════════╡
        │ Male   ┆ 2000 ┆ ["Book", "Sport"]  ┆ ["Cat", "Dog"] │
        │ Female ┆ 1999 ┆ ["Movie", "Sport"] ┆ ["Dog"]        │
        │ Male   ┆ 1998 ┆ ["Movie"]          ┆ ["Cat"]        │
        └────────┴──────┴────────────────────┴────────────────┘

    Notes:
        - Empty strings (``""``) are converted to ``None``.
        - Multiselect values are always sorted alphabetically within each row.
        - Columns with no valid responses are excluded by default
          (``exclude_null=True``).
        - Do not combine ``auto_detect=True`` with ``compact_ids`` in the
          same call — use one approach or the other.
        - ``name_pattern`` separators (``_``, ``.``, ``:``) are defined in
          ``survy.separator.SEPARATORS``.
        - Column names must not contain more than one of these separators.
          Names like ``"my.var_1"`` are ambiguous and may cause
          ``parse_id()`` to fail or produce incorrect grouping. Rename
          such columns before loading (e.g. ``"myvar_1"`` or
          ``"my@var_1"``).
    """
    compact_ids = compact_ids or []
    reader = PolarReader(compact_ids, compact_separator, auto_detect, name_pattern)
    reader.read_df(raw_df)
    return reader.to_survey(exclude_null)
