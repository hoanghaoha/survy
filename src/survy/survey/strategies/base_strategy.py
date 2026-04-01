from abc import ABC, abstractmethod

import polars


class BaseStrategy(ABC):
    @property
    @abstractmethod
    def sub_bases(self) -> dict: ...

    @abstractmethod
    def get_df(self, **kwargs) -> polars.DataFrame: ...
