from abc import ABC, abstractmethod

import polars


class _BaseStrategy(ABC):
    """
    Abstract base class for all variable processing strategies.

    A strategy defines how a variable's raw data is:
    - Transformed into a DataFrame
    - Aggregated into sub-bases
    - Converted into SPSS syntax

    Concrete implementations must handle specific variable types
    (e.g., select, multiselect, number).
    """

    @abstractmethod
    def get_df(self, **kwargs) -> polars.DataFrame:
        """
        Generate a processed DataFrame representation of the variable.

        This method is responsible for transforming raw input data into
        a structured format suitable for analysis or reporting.

        Args:
            **kwargs: Strategy-specific parameters (e.g., dtype, compact).

        Returns:
            polars.DataFrame: Processed DataFrame.
        """
        ...

    @property
    @abstractmethod
    def frequencies(self) -> polars.DataFrame:
        """Frequency counts and proportions for each value of the variable.

        Subclasses compute this differently based on variable type:
        - SELECT: counts per category, nulls excluded from counts
        - MULTISELECT: counts per option after exploding list responses
        - NUMBER: counts per numeric value, nulls excluded from counts

        Returns:
            A DataFrame with columns:
                - value name: the category, option, or numeric value
                - "count": number of respondents for that value
                - "proportion": count divided by total number of respondents
        """
        ...

    @abstractmethod
    def get_sps(self, label: str) -> str:
        """
        Generate SPSS syntax for the variable.

        Args:
            label (str): The display label of the variable.

        Returns:
            str: SPSS syntax string.
        """
        ...
