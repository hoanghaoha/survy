import polars

import survy

df = polars.DataFrame(
    {
        "gender": ["Male", "Female", "Male"],
        "yob": [2000, 1999, 1998],
        "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
        "animal_1": ["Cat", "", "Cat"],
        "animal_2": ["Dog", "Dog", ""],
    }
)

survey = survy.read_polars(df, auto_detect=True)
print("\n")
print(survey.sps)
