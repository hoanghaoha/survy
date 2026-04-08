import polars

from survy.io.polars import read_polars

print("\n")
df = polars.DataFrame(
    {
        "gender": ["Male", "Female", "Male"],
        "yob": [2000, 1999, 1998],
        "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
        "animal_1": ["Cat", "", "Cat"],
        "animal_2": ["Dog", "Dog", ""],
    }
)

survey = read_polars(df, auto_detect=True)
print(survey.get_df())
