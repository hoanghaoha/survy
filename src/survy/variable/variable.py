from typing import Any, Literal
import warnings

import polars

from survy.errors import DataStructureError, VarTypeError
from survy.variable._utils import VarType
from survy.variable.strategies.base_strategy import BaseStrategy
from survy.variable.strategies.multiselect_strategy import MultiSelectStrategy
from survy.variable.strategies.number_strategy import NumberStrategy
from survy.variable.strategies.select_strategy import SelectStrategy
from survy.utils.functions import extract_mapping


class Variable:
    """
    Represents a single survey variable backed by a Polars Series.

    Attributes:
        series (polars.Series): Raw data for the variable.
    """

    def __init__(self, series: polars.Series):
        """
        Initialize a Variable instance.

        Args:
            series (polars.Series): The data column representing the variable.

        Raises:
            AssertionError: If variable type cannot be determined.
        """
        self.series = series
        self._value_indices: dict[str, int] = {}
        self._label: str = ""

        assert self.vtype

    def __str__(self) -> str:
        """
        Representation string of variable.

        Examples:
        >>> gender = Variable(polars.Series("gender", ["Male", "Female", "Male"]))

        >>> print(gender)
        Variable(id=gender, base=3, label=gender, value_indices={'Male': 1, 'Female': 2})"
        """
        return f"Variable(id={self.id}, base={self.base}, label={self.label}, value_indices={self.value_indices})"

    def __iter__(self):
        """
        Iterate over raw values in the variable.

        Yields:
            Any: Each value in the underlying series.

        Examples:
            >>> for v in variable:
            ...     print(v)
        """
        return iter(self.series)

    def __getitem__(self, key: int | slice | Any) -> Any:
        """
        Retrieve one or more values from the variable.

        Args:
            key:
                Index, slice, or boolean mask supported by ``polars.Series``.

        Returns:
            Any: A single value or a subset of the series.

        Examples:
            >>> variable[0]
            'Male'

            >>> variable[1:3]
            shape: (2,)
        """
        return self.series[key]

    def __len__(self) -> int:
        """
        Return total number of responses (including missing values).

        Returns:
            int: Length of the underlying series.

        Examples:
            >>> len(variable)
            100
        """
        return self.len

    @property
    def id(self) -> str:
        """
        Returns the variable identifier (column name).

        Returns:
            str: Variable ID.
        """
        return self.series.name

    @id.setter
    def id(self, new_id: str):
        """
        Set a id for the variable.

        Args:
            new_id (str): New ID.
        """
        self.series = self.series.rename(new_id)

    @property
    def label(self) -> str:
        """
        Returns the display label of the variable.

        - Uses custom label if set, otherwise defaults to column name.
        - Prepends loop_id if present.
        - Truncates label to 249 characters.

        Returns:
            str: Formatted label.
        """
        label = self._label if self._label else self.series.name

        return label

    @label.setter
    def label(self, new_label: str):
        """
        Set a custom label for the variable.

        Args:
            new_label (str): New label.
        """
        self._label = new_label

    @property
    def value_indices(self) -> dict[str, int]:
        """
        Returns mapping of response values to numeric indices.

        - For numeric variable, returns empty dict.
        - If not manually set, inferred from data.

        Returns:
            dict[str, int]: Value-to-index mapping.
        """
        if self.series.dtype.is_numeric():
            return {}

        return (
            self._value_indices
            if self._value_indices
            else extract_mapping(self.series.to_list())
        )

    @value_indices.setter
    def value_indices(self, new_value_indices):
        """
        Set custom value index mapping.

        Ensures all existing values are covered.

        Args:
            new_value_indices (dict[str, int]): Mapping of values to indices.

        Raises:
            DataStructureError: If any value is missing from mapping.
        """
        if self.series.dtype.is_numeric():
            warnings.warn(f"NUMBER {self.id} can not be updated value_indices")
        else:
            for v in extract_mapping(self.series.to_list()).keys():
                if v not in new_value_indices.keys():
                    raise DataStructureError(
                        f"{self.id}: Value is not have option index: {v}"
                    )
            self._value_indices = new_value_indices

    @property
    def dtype(self) -> polars.DataType:
        """
        Returns the data type of the series.

        Returns:
            polars.DataType: Series data type.
        """
        return self.series.dtype

    @property
    def vtype(self) -> VarType:
        """
        Infers the variable type based on data type.

        Rules:
            - List → MULTISELECT
            - Numeric → NUMBER
            - String → SELECT
            - Otherwise, attempts cast to string → SELECT

        Returns:
            VarType: Inferred variable type.

        Raises:
            VarTypeError: If type cannot be determined.

        Examples:

        >>> gender = Variable(polars.Series("gender", ["Male", "Female", "Male"]))

        >>> gender.vtype
        select

        >>> yob = Variable(polars.Series("yob", [2000, 1999, 1998]))

        >>> yob.vtype
        number

        >>> hobby = Variable(polars.Series("hobby", [["Sport", Book"], ["Sport", "Movie"], ["Movie"]]))
        >>> hobby.vtype
        multi_select
        """
        dtype = self.dtype

        if dtype == polars.List:
            if all([d == [] for d in self.series.to_list()]):
                self.series = polars.Series(
                    self.series.name, ["" for _ in range(self.len)], dtype=polars.String
                )
                warnings.warn(f"{self.id} with empty list converted to SELECT")
                return VarType.SELECT
            return VarType.MULTISELECT

        if dtype.is_numeric():
            return VarType.NUMBER

        if dtype == polars.String:
            return VarType.SELECT

        try:
            self.series.cast(polars.String)
        except Exception as e:
            raise VarTypeError from e

        warnings.warn(f"{self.id} with dtype {self.series.dtype} converted to SELECT")
        return VarType.SELECT

    @property
    def base(self) -> int:
        """
        Returns the count of non-empty responses.

        Returns:
            int: Base count.

        Examples:

        >>> gender = Variable(polars.Series("gender", ["Male", "Female", "Male", None]))

        >>> gender.base
        3
        """
        return len([i for i in self.series.to_list() if i])

    @property
    def len(self) -> int:
        """
        Returns total number of responses.

        Returns:
            int: Length of series.

        Examples:

        >>> gender = Variable(polars.Series("gender", ["Male", "Female", "Male", None]))

        >>> gender.len
        4
        """
        return self.series.shape[0]

    @property
    def strategy(self) -> BaseStrategy:
        """
        Returns the appropriate strategy instance for the variable.

        Strategy is selected based on var type.

        Returns:
            BaseStrategy: Strategy instance.
        """
        return {
            VarType.SELECT: SelectStrategy,
            VarType.MULTISELECT: MultiSelectStrategy,
            VarType.NUMBER: NumberStrategy,
        }[self.vtype](self.series, self.value_indices)

    def replace(self, mapping: dict[str, str]) -> None:
        """
        Replace a values in variable data by a given mapping.

        Args:
            mapping (dict[str, str]): A mapping for replace values

        Returns:
            None

        Examples:

        >>> gender = Variable(polars.Series("gender", ["Male", "Female", "Male"]))

        >>> gender.replace({"Male": "Men"})
        >>> gender.series
        Series: 'gender' [str]
        [
                "Men"
                "Female"
                "Men"
        ]
        """
        if self.vtype != VarType.MULTISELECT:
            self.series = self.series.replace(mapping)
        else:
            new_series = polars.Series(
                self.id,
                [[mapping.get(d, d) for d in item] for item in self.series.to_list()],
            )
            self.series = new_series

        self.value_indices = extract_mapping(self.series.to_list())

    def to_dict(self) -> dict:
        """
        Serializes the variable into a dictionary.

        Returns:
            dict: Variable representation.

        Examples:

        >>> gender = Variable(polars.Series("gender", ["Male", "Female", "Male"]))

        >>> gender.to_dict()
        {'id': 'gender', 'data': ['Male', 'Female', 'Male'], 'label': '', 'value_indices': {'Female': 1, 'Male': 2}, 'vtype': <VarType.SELECT: 'select'>}
        """
        return {
            "id": self.id,
            "data": self.series.to_list(),
            "label": self._label,
            "value_indices": self.value_indices,
            "vtype": self.vtype,
        }

    @property
    def frequencies(self) -> polars.DataFrame:
        """Frequency counts and proportions for each value of the variable.

        Delegates to the underlying strategy based on variable type.
        See the concrete strategy implementations for details.

        Returns:
            A DataFrame with columns:
                - value name: the category, option, or numeric value
                - "count": number of respondents for that value
                - "proportion": count divided by total number of respondents

        Example:

            >>> gender = Variable(polars.Series("gender", ["Male", "Female", "Male"]))

            >>> gender.frequencies
            shape: (2, 3)
            ┌────────┬───────┬────────────┐
            │ gender ┆ count ┆ proportion │
            │ ---    ┆ ---   ┆ ---        │
            │ str    ┆ u32   ┆ f64        │
            ╞════════╪═══════╪════════════╡
            │ Female ┆ 1     ┆ 0.333333   │
            │ Male   ┆ 2     ┆ 0.666667   │
            └────────┴───────┴────────────┘

            >>> hobby = Variable(polars.Series("hobby", [["Sport", Book"], ["Sport", "Movie"], ["Movie"]]))

            >>> hobby.frequencies
            shape: (3, 3)
            ┌───────┬───────┬────────────┐
            │ hobby ┆ count ┆ proportion │
            │ ---   ┆ ---   ┆ ---        │
            │ str   ┆ u32   ┆ f64        │
            ╞═══════╪═══════╪════════════╡
            │ Book  ┆ 1     ┆ 0.333333   │
            │ Movie ┆ 2     ┆ 0.666667   │
            │ Sport ┆ 2     ┆ 0.666667   │
            └───────┴───────┴────────────┘
        """
        return self.strategy.frequencies

    @property
    def sps(self) -> str:
        """
        Returns SPSS syntax representation of the variable.

        Returns:
            str: SPSS syntax string.

        Example:

            >>> gender = Variable(polars.Series("gender", ["Male", "Female", "Male"]))

            >>> gender.sps
            VARIABLE LABELS gender 'gender'.
            VALUE LABELS gender 1 'Female'
            2 'Male'.
            VARIABLE LEVEL gender (NOMINAL).

            >>> hobby = Variable(polars.Series("hobby", [["Sport", Book"], ["Sport", "Movie"], ["Movie"]]))

            >>> hooby.sps
            VARIABLE LABELS hobby_1 '[Book] hobby'.
            VARIABLE LABELS hobby_2 '[Movie] hobby'.
            VARIABLE LABELS hobby_3 '[Sport] hobby'.
            VALUE LABELS hobby_1 1 'Book'.
            VALUE LABELS hobby_2 1 'Movie'.
            VALUE LABELS hobby_3 1 'Sport'.
            VARIABLE LEVEL hobby_1 (NOMINAL).
            VARIABLE LEVEL hobby_2 (NOMINAL).
            VARIABLE LEVEL hobby_3 (NOMINAL).
            MRSETS /MDGROUP NAME=$hobby
            LABEL='hobby'
            CATEGORYLABELS=COUNTEDVALUES VALUE=1
            VARIABLES=hobby_1 hobby_2 hobby_3
            /DISPLAY NAME=[$hobby].
        """
        return self.strategy.get_sps(self.label)

    def get_df(
        self, dtype: Literal["number", "text", "compact"] = "text"
    ) -> polars.DataFrame:
        """
        Returns a processed DataFrame representation of the variable.

        Args:
            dtype (Literal["number", "text", "compact"], optional):
                Output format. Defaults to "text". "compact" only use for MULTISELECT.

        Returns:
            polars.DataFrame: Processed DataFrame.

        Example:

            >>> gender = Variable(polars.Series("gender", ["Male", "Female", "Male"]))
            >>> gender.get_df("text")
            shape: (3, 1)
            ┌────────┐
            │ gender │
            │ ---    │
            │ str    │
            ╞════════╡
            │ Male   │
            │ Female │
            │ Male   │
            └────────┘

            >>> gender.get_df("number")
            shape: (3, 1)
            ┌────────┐
            │ gender │
            │ ---    │
            │ i64    │
            ╞════════╡
            │ 2      │
            │ 1      │
            │ 2      │
            └────────┘

            >>> hobby = Variable(polars.Series("hobby", [["Sport", Book"], ["Sport", "Movie"], ["Movie"]]))
            >>> hobby.get_df("compact")
            shape: (3, 1)
            ┌────────────────────┐
            │ hobby              │
            │ ---                │
            │ list[str]          │
            ╞════════════════════╡
            │ ["Book", "Sport"]  │
            │ ["Movie", "Sport"] │
            │ ["Movie"]          │
            └────────────────────┘

            >>> hobby.get_df("text")
            shape: (3, 3)
            ┌─────────┬─────────┬─────────┐
            │ hobby_1 ┆ hobby_2 ┆ hobby_3 │
            │ ---     ┆ ---     ┆ ---     │
            │ str     ┆ str     ┆ str     │
            ╞═════════╪═════════╪═════════╡
            │ Book    ┆ null    ┆ Sport   │
            │ null    ┆ Movie   ┆ Sport   │
            │ null    ┆ Movie   ┆ null    │
            └─────────┴─────────┴─────────┘

            >>> hobby.get_df("number")
            shape: (3, 3)
            ┌─────────┬─────────┬─────────┐
            │ hobby_1 ┆ hobby_2 ┆ hobby_3 │
            │ ---     ┆ ---     ┆ ---     │
            │ i8      ┆ i8      ┆ i8      │
            ╞═════════╪═════════╪═════════╡
            │ 1       ┆ 0       ┆ 1       │
            │ 0       ┆ 1       ┆ 1       │
            │ 0       ┆ 1       ┆ 0       │
            └─────────┴─────────┴─────────┘


            >>> yob = Variable(polars.Series("yob", [2000, 1999, 1998]))

            >>> yob.get_df()
            shape: (3, 1)
            ┌──────┐
            │ yob  │
            │ ---  │
            │ i64  │
            ╞══════╡
            │ 2000 │
            │ 1999 │
            │ 1998 │
            └──────┘
        """
        return self.strategy.get_df(dtype=dtype)
