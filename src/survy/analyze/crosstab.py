from copy import deepcopy

import polars as pl
from statsmodels.stats.proportion import proportions_ztest

from survy.errors import DataStructureError, DataTypeError
from survy.survey._utils import VarType
from survy.survey.variable import Variable


def _get_filter(col: Variable, row: Variable, filter: Variable | None) -> Variable:
    if filter:
        if filter.vtype == VarType.NUMBER:
            raise DataTypeError("Can not filter by NUMBER")

        f = deepcopy(filter)
        f.series = f.series.rename(f.series.name + "_FILTER")
        return f

    return Variable(series=pl.Series("FILTER", ["Total"] * col.len))


def _get_df(question: Variable, as_num: bool = False) -> pl.DataFrame:
    if question.vtype == VarType.MULTISELECT:
        df = question.get_df(dtype="compact").explode(question.id)
        if as_num:
            df = df.select(
                pl.col(question.id).replace_strict(question.value_indices, default=None)
            )
    elif question.vtype == VarType.SELECT:
        df = question.get_df(dtype="number" if as_num else "text")
    else:
        df = question.get_df(dtype="number")

    return df.with_row_index("ID")


def _merge_element_dfs(df1: pl.DataFrame, df2: pl.DataFrame, on_columns: list[str]):
    if df1.height < df2.height:
        raise DataStructureError("Unexpected df shape format")

    if df1.height > df2.height:
        pad = pl.DataFrame(
            [[""] * len(df2.columns)] * (df1.height - df2.height),
            schema=df2.columns,
            orient="row",
        )
        df2 = pl.concat([df2, pad])

    return df1.with_columns(
        [
            (pl.col(c).cast(pl.String) + pl.lit(" ") + df2[c].cast(pl.String)).alias(c)
            if c in on_columns
            else pl.col(c)
            for c in df1.columns
        ]
    )


class Crosstaber:
    def __init__(self, col: Variable, row: Variable, filter: Variable | None = None):
        self.col = deepcopy(col)
        self.row = deepcopy(row)
        self.filter = _get_filter(col, row, filter)

    def get_df(self, as_num: bool) -> pl.DataFrame:
        col_df = _get_df(self.col, as_num=False)
        row_df = _get_df(self.row, as_num=as_num)
        filter_df = _get_df(self.filter, as_num=False)

        return col_df.join(row_df, on="ID", how="left").join(
            filter_df, on="ID", how="left"
        )

    def _build_count_df(self, filtered_option: str) -> pl.DataFrame:
        df = self.get_df(as_num=False)

        filtered_df = df.filter(pl.col(self.filter.id) == filtered_option)

        count_df = filtered_df.pivot(
            on=self.col.id,
            index=self.row.id,
            values="ID",
            aggregate_function=pl.element().n_unique(),
        ).fill_null(0)

        return count_df.with_columns(pl.col(self.row.id).cast(pl.String))

    def _add_totals(self, count_df: pl.DataFrame) -> pl.DataFrame:
        count_df = count_df.with_columns(pl.col(self.row.id).cast(pl.String))

        col_total = pl.DataFrame(self.col.frequencies, orient="row")

        col_total = col_total.with_columns(pl.lit("Total").alias(self.row.id)).select(
            count_df.columns
        )

        result = pl.concat([count_df, col_total], how="vertical_relaxed")

        row_keys = list(self.row.frequencies.keys())
        row_vals = list(self.row.frequencies.values())

        row_total = pl.DataFrame(
            {
                self.row.id: [str(k) for k in row_keys] + ["Total"],
                "Total": row_vals + [self.row.base],
            }
        )

        return result.join(row_total, on=self.row.id, how="left")

    def crosstab_count(self, filtered_option: str) -> pl.DataFrame:
        count_df = self._build_count_df(filtered_option)
        return self._add_totals(count_df)

    def crosstab_percent(self, filtered_option: str) -> pl.DataFrame:
        df = self.crosstab_count(filtered_option)

        col_totals = {**self.col.frequencies, "Total": self.col.base}

        return df.with_columns(
            [(pl.col(c) / col_totals[c]) for c in df.columns if c != self.row.id]
        )

    def crosstab_number(self, filtered_option: str) -> pl.DataFrame:
        df = self.get_df(as_num=True)
        filtered_df = df.filter(pl.col(self.filter.id) == filtered_option)

        return (
            filtered_df.group_by(self.col.id)
            .agg(
                pl.col(self.row.id).mean().alias("mean"),
                pl.col(self.row.id).std().alias("std"),
                pl.col(self.row.id).var().alias("var"),
                pl.col(self.row.id).median().alias("median"),
                pl.col(self.row.id).max().alias("max"),
                pl.col(self.row.id).min().alias("min"),
            )
            .sort(self.col.id)
        )

    def sig_test(self, filtered_option: str, sig_level: float) -> pl.DataFrame:
        df = self._build_count_df(filtered_option).drop(self.row.id)

        def _get_total(i):
            return self.col.frequencies[df.columns[i]]

        def _is_diff(count, nobs):
            if any(n == 0 for n in nobs) or any(c == 0 for c in count):
                return False
            _, p = proportions_ztest(count, nobs)
            return p < sig_level

        def _col_label(n):
            s = ""
            while n >= 0:
                s = chr(n % 26 + 65) + s
                n = n // 26 - 1
            return s

        results = []
        for row in df.iter_rows():
            row_res = []
            for i, val in enumerate(row):
                label = ""
                for j, other in enumerate(row):
                    if i != j and _is_diff(
                        [val, other], [_get_total(i), _get_total(j)]
                    ):
                        label += _col_label(j)
                row_res.append(label)
            results.append(row_res)

        return pl.DataFrame(results, schema=df.columns, orient="row")

    def run(self, as_num: bool, as_percent: bool, sig_level: float):
        results = {}

        for option in self.filter.value_indices.keys():
            if as_num:
                results[option] = self.crosstab_number(option)
                continue

            base_df = (
                self.crosstab_percent(option)
                if as_percent
                else self.crosstab_count(option)
            )

            sig_df = self.sig_test(option, sig_level)

            results[option] = _merge_element_dfs(
                base_df,
                sig_df,
                [c for c in base_df.columns if c not in [self.row.id, "Total"]],
            )

        return results


def crosstab(
    col: Variable,
    row: Variable,
    filter: Variable | None = None,
    as_num: bool = False,
    as_percent: bool = False,
    sig_level: float = 0,
) -> dict[str, pl.DataFrame]:
    crosstaber = Crosstaber(col, row, filter)
    return crosstaber.run(as_num, as_percent, sig_level)
