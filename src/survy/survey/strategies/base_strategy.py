from abc import ABC, abstractmethod

import polars


class BaseStrategy(ABC):
    @abstractmethod
    def get_df(self, **kwargs) -> polars.DataFrame: ...

    @property
    @abstractmethod
    def sub_bases(self) -> dict: ...

    @abstractmethod
    def get_sps(self, label: str) -> str: ...
