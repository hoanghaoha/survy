from abc import ABC, abstractmethod

import polars


class BaseStrategy(ABC):
    """
    Abstract base class for all question processing strategies.

    A strategy defines how a question's raw data is:
    - Transformed into a DataFrame
    - Aggregated into sub-bases
    - Converted into SPSS syntax

    Concrete implementations must handle specific question types
    (e.g., select, multiselect, number).
    """

    @abstractmethod
    def get_df(self, **kwargs) -> polars.DataFrame:
        """
        Generate a processed DataFrame representation of the question.

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
    def sub_bases(self) -> dict:
        """
        Compute sub-base counts for the question.

        Sub-bases typically represent counts per category/option,
        depending on the question type.

        Returns:
            dict: Mapping of category/option to count.
        """
        ...

    @abstractmethod
    def get_sps(self, label: str) -> str:
        """
        Generate SPSS syntax for the question.

        Args:
            label (str): The display label of the question.

        Returns:
            str: SPSS syntax string.
        """
        ...

