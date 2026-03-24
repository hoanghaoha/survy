import polars
from copy import deepcopy

from survy.errors import DataTypeError
from survy.survey._utils import QuestionType
from survy.survey.question import Question


def _get_df(question: Question, as_num: bool = False):
    if question.qtype == QuestionType.MULTISELECT:
        df = question.get_df(dtype="text", compact=True).explode(question.id)
        if as_num:
            df = df.select(
                polars.col(question.id).replace_strict(question.mapping, default=None)
            )
    elif question.qtype == QuestionType.SELECT:
        df = question.get_df(dtype="number" if as_num else "text")
    else:
        df = question.get_df(dtype="number")

    return df.with_row_index("ID")


def _crosstab_category(
    df: polars.DataFrame, col: Question, row: Question, percent: bool
):
    result = df.pivot(
        on=col.id,
        index=row.id,
        values="ID",
        aggregate_function=polars.element().n_unique(),
    ).fill_null(0)

    row_total = polars.DataFrame(
        {
            row.id: list(row.sub_bases.keys()) + ["Total"],
            "Total": list(row.sub_bases.values()) + [row.base],
        },
    )

    col_total = polars.DataFrame(col.sub_bases)

    result = polars.concat(
        [
            result,
            col_total.with_columns(polars.lit("Total").alias(row.id)).select(
                result.columns
            ),
        ],
        how="vertical_relaxed",
    ).join(row_total, on=row.id, how="left")

    if percent:
        col_sub_bases = {**col.sub_bases, **{"Total": col.base}}
        result = result.with_columns(
            [
                polars.col(col) / col_sub_bases[col]
                for col in result.columns
                if col != row.id
            ]
        )

    return result


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
        mapping={"Total": 1},
        values=polars.Series("FILTER", ["Total" for _ in range(len_)]),
    )


def crosstab(
    col: Question,
    row: Question,
    filter: Question | None = None,
    as_num: bool = False,
    as_percent: bool = False,
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

    for option, _ in filter.mapping.items():
        filtered_df = df.filter(polars.col(filter.id) == option)

        if as_num:
            results[option] = _crosstab_num(filtered_df, col, row)
        else:
            results[option] = _crosstab_category(filtered_df, col, row, as_percent)

    return results
