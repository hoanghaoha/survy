import polars

print(
    polars.DataFrame(
        {
            "gender": ["M", "F", "F"],
            "hobby_1": ["A", "", ""],
            "hobby_2": ["B", "B", ""],
        }
    )
)
