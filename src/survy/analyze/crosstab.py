import polars
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

    if percent:
        col_sub_bases = col.sub_bases
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
):
    if filter is None:
        filter = _default_filter(col.len)

    if filter.qtype == QuestionType.NUMBER:
        raise DataTypeError("Can not filter by NUMBER")

    results = {}

    col_df = _get_df(col, as_num=False)
    row_df = _get_df(row, as_num)
    filter_df = _get_df(filter)
    df = col_df.join(row_df, on="ID", how="left").join(filter_df, on="ID", how="left")

    for option, _ in filter.mapping.items():
        filtered_df = df.filter(polars.col(filter.id) == option)

        if as_num:
            results[option] = _crosstab_num(filtered_df, col, row)
        else:
            results[option] = _crosstab_category(filtered_df, col, row, as_percent)

    return results
