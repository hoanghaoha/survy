from typing import Tuple
import polars
from copy import deepcopy
from statsmodels.stats.proportion import proportions_ztest

from survy.errors import DataStructureError, DataTypeError
from survy.survey._utils import QuestionType
from survy.survey.question import Question


def _get_df(question: Question, as_num: bool = False):
    if question.qtype == QuestionType.MULTISELECT:
        df = question.get_df(dtype="text", compact=True).explode(question.id)
        if as_num:
            df = df.select(
                polars.col(question.id).replace_strict(
                    question.option_indices, default=None
                )
            )
    elif question.qtype == QuestionType.SELECT:
        df = question.get_df(dtype="number" if as_num else "text")
    else:
        df = question.get_df(dtype="number")

    return df.with_row_index("ID")


def _sig_test_category(
    count_df: polars.DataFrame, cols_total: dict[str, int], sig_level: float
) -> polars.DataFrame:
    def _get_item_total(index):
        return cols_total[count_df.columns[index]]

    def _is_different(count: list[int], nobs: list[int], sig_level: float) -> bool:
        if any(n == 0 for n in nobs):
            return False

        if any(c == 0 for c in count):
            return False

        _, p_value = proportions_ztest(count, nobs)
        if p_value < sig_level:
            return True
        return False

    def _num_to_col(n: int) -> str:
        result = ""
        while True:
            result = chr(n % 26 + ord("A")) + result
            n = n // 26 - 1
            if n < 0:
                break
        return result

    def _test_row(row: Tuple[int]) -> list[str]:
        assert all([isinstance(r, int) for r in row])

        results = []

        for current_index, current_value in enumerate(row):
            result = ""
            for compare_index, compare_value in enumerate(row):
                if current_index == compare_index:
                    continue
                else:
                    count = [current_value, compare_value]
                    nobs = [
                        _get_item_total(current_index),
                        _get_item_total(compare_index),
                    ]
                    result += (
                        _num_to_col(compare_index)
                        if _is_different(count, nobs, sig_level)
                        else ""
                    )
            results.append(result)

        assert len(results) == len(row)

        return results

    test_results = [_test_row(row) for row in count_df.iter_rows()]

    return polars.DataFrame(test_results, schema=count_df.columns, orient="row")


def _merge_element_dfs(
    df1: polars.DataFrame, df2: polars.DataFrame, on_columns: list[str]
):
    df1 = deepcopy(df1)
    df2 = deepcopy(df2)
    diff = df1.shape[0] - df2.shape[0]
    if diff > 0:
        df2 = polars.concat(
            [
                df2,
                polars.DataFrame(
                    data=[["" for _ in df2.columns] for _ in range(diff)],
                    schema=df2.columns,
                    orient="row",
                ),
            ]
        )
    else:
        raise DataStructureError("Unexpected df shape format")

    return df1.with_columns(
        [
            (
                polars.col(c).cast(polars.String)
                + polars.lit(" ").cast(polars.String)
                + df2[c].cast(polars.String)
            ).alias(c)
            if c in on_columns
            else polars.col(c).alias(c)
            for c in df1.columns
        ]
    )


def _crosstab_category(
    df: polars.DataFrame, col: Question, row: Question, percent: bool, sig_level: float
):
    def _get_total_count_df(count_df: polars.DataFrame):
        row_total = polars.DataFrame(
            {
                row.id: list(row.sub_bases.keys()) + ["Total"],
                "Total": list(row.sub_bases.values()) + [row.base],
            },
        )

        col_total = polars.DataFrame(col.sub_bases)

        return polars.concat(
            [
                count_df,
                col_total.with_columns(polars.lit("Total").alias(row.id)).select(
                    count_df.columns
                ),
            ],
            how="vertical_relaxed",
        ).join(row_total, on=row.id, how="left")

    def _get_total_percent_df(total_count_df: polars.DataFrame):
        col_sub_bases = {**col.sub_bases, **{"Total": col.base}}
        return total_count_df.with_columns(
            [
                polars.col(col) / col_sub_bases[col]
                for col in total_count_df.columns
                if col != row.id
            ]
        )

    count_df = df.pivot(
        on=col.id,
        index=row.id,
        values="ID",
        aggregate_function=polars.element().n_unique(),
    ).fill_null(0)

    total_count_df = _get_total_count_df(count_df)

    if sig_level:
        sig_test_df = _sig_test_category(
            count_df.drop(row.id), col.sub_bases, sig_level
        )
        if not percent:
            return _merge_element_dfs(
                total_count_df,
                sig_test_df,
                [c for c in total_count_df.columns if c not in [row.id, "Total"]],
            )
        else:
            total_percent_df = _get_total_percent_df(total_count_df)
            return _merge_element_dfs(
                total_percent_df,
                sig_test_df,
                [c for c in total_percent_df.columns if c not in [row.id, "Total"]],
            )
    else:
        if not percent:
            return total_count_df
        else:
            total_percent_df = _get_total_percent_df(total_count_df)
            return total_percent_df


def _crosstab_num(df: polars.DataFrame, col: Question, row: Question):
    return (
        df.group_by(by=col.id)
        .agg(
            polars.col(row.id).mean().alias("mean"),
            polars.col(row.id).std().alias("std"),
            polars.col(row.id).var().alias("var"),
            polars.col(row.id).median().alias("median"),
            polars.col(row.id).max().alias("max"),
            polars.col(row.id).min().alias("min"),
        )
        .rename({"by": col.id})
        .sort(col.id)
    )


def _default_filter(len_: int):
    return Question(
        label="FILTER",
        option_indices={"Total": 1},
        values=polars.Series("FILTER", ["Total" for _ in range(len_)]),
    )


def crosstab(
    col: Question,
    row: Question,
    filter: Question | None = None,
    as_num: bool = False,
    as_percent: bool = False,
    sig_level: float = 0,
) -> dict[str, polars.DataFrame]:
    col = deepcopy(col)
    row = deepcopy(row)
    filter = deepcopy(filter)

    if filter is None:
        filter = _default_filter(col.len)

    if filter.id in [col.id, row.id]:
        filter.values = filter.values.rename(filter.values.name + "_FILTER")

    if filter.qtype == QuestionType.NUMBER:
        raise DataTypeError("Can not filter by NUMBER")

    if col.qtype == QuestionType.NUMBER:
        raise DataTypeError("Can not categorize by NUMBER")

    if row.qtype == QuestionType.NUMBER:
        as_num = True

    results = {}

    col_df = _get_df(col, as_num=False)
    row_df = _get_df(row, as_num)
    filter_df = _get_df(filter, as_num=False)
    df = col_df.join(row_df, on="ID", how="left").join(filter_df, on="ID", how="left")

    for option, _ in filter.option_indices.items():
        filtered_df = df.filter(polars.col(filter.id) == option)

        if as_num:
            results[option] = _crosstab_num(filtered_df, col, row)
        else:
            results[option] = _crosstab_category(
                filtered_df, col, row, as_percent, sig_level
            )

    return results
