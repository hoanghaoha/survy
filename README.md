# survy

[![PyPI version](https://img.shields.io/pypi/v/survy.svg)](https://pypi.org/project/survy/)
[![License](https://img.shields.io/pypi/l/survy.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/survy.svg)](https://pypi.org/project/survy/)
[![CI](https://github.com/hoanghaoha/survy/actions/workflows/ci.yml/badge.svg)](https://github.com/hoanghaoha/survy/actions)

**Process, transform, and analyze survey-format data with a clean and simple API.**

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Installation](#-installation)
- [Quick Demo](#-quick-demo)
  - [Sample Data](#sample-data)
  - [Load and Analyze](#load-and-analyze)
- [Usage](#-usage)
  - [Load Data](#load-data)
  - [Work with Survey](#work-with-survey)
  - [Work with Variables](#work-with-variables)
  - [Analyze](#analyze)
- [Design Philosophy](#-design-philosophy)
- [Contributing](#-contributing)
- [License](#-license)
- [References](#-references)

---

## 📦 Overview

`survy` is a lightweight Python library built for working efficiently with survey data.
It simplifies the full workflow — from raw data ingestion to transformation and analysis — while preserving survey-specific structures like multiselect questions.

---

## ✨ Features

- 🔹 Multiselect as a first-class concept
- 🔹 Read & write multiple formats: CSV, Excel, JSON, SPSS, etc.
- 🔹 Clean, minimal, and expressive API
- 🔹 Built-in tools for validation, tracking, and analysis
- 🔹 Cross-tabulation with significance testing

---

## 🚀 Installation

```bash
pip install survy
```

---

## ⚡ Quick Demo

### Sample Data

**`data.csv`** — multiselect columns in wide (split) format:

| gender | yob  | hobby_1 | hobby_2 | hobby_3 | animal_1 | animal_2 |
|--------|------|---------|---------|---------|----------|----------|
| Male   | 2000 | Book    |         | Sport   | Cat      | Dog      |
| Female | 1999 |         | Movie   |         |          | Dog      |
| Male   | 1998 |         | Movie   |         | Cat      |          |

**`data_compact.csv`** — multiselect columns in compact (delimited) format:

| gender | yob  | hobby        | animal   |
|--------|------|--------------|----------|
| Male   | 2000 | Book; Sport  | Cat; Dog |
| Female | 1999 | Movie; Sport | Dog      |
| Male   | 1998 | Movie        | Cat      |

---

### Load and Analyze

```python
import survy

# Load dataset — parse multiselect split columns
survey = survy.read_csv("data.csv", name_pattern="id(_multi)?")
# Load dataset — auto detect multiselect compact columns
survey = survy.read_csv("data.csv", auto_detect=True)

print(survey.get_df())
# ┌────────┬──────┬────────────────────┬────────────────┐
# │ gender ┆ yob  ┆ hobby              ┆ animal         │
# │ ---    ┆ ---  ┆ ---                ┆ ---            │
# │ str    ┆ i64  ┆ list[str]          ┆ list[str]      │
# ╞════════╪══════╪════════════════════╪════════════════╡
# │ Male   ┆ 2000 ┆ ["Book", "Sport"]  ┆ ["Cat", "Dog"] │
# │ Female ┆ 1999 ┆ ["Movie", "Sport"] ┆ ["Dog"]        │
# │ Male   ┆ 1998 ┆ ["Movie"]          ┆ ["Cat"]        │
# └────────┴──────┴────────────────────┴────────────────┘

# Inspect a variable
gender = survey["gender"]

print(gender.base)
# 3

print(gender.frequencies)
# ┌────────┬───────┬────────────┐
# │ gender ┆ count ┆ proportion │
# │ ---    ┆ ---   ┆ ---        │
# │ str    ┆ u32   ┆ f64        │
# ╞════════╪═══════╪════════════╡
# │ Female ┆ 1     ┆ 0.333333   │
# │ Male   ┆ 2     ┆ 0.666667   │
# └────────┴───────┴────────────┘

# Crosstab analysis
crosstab_count = survy.crosstab(survey["gender"], survey["hobby"])
print(crosstab_count)
# {'Total': shape: (3, 3)
# ┌───────┬──────────┬────────────┐
# │ hobby ┆ Male (A) ┆ Female (B) │
# │ ---   ┆ ---      ┆ ---        │
# │ str   ┆ str      ┆ str        │
# ╞═══════╪══════════╪════════════╡
# │ Book  ┆ 1        ┆ 0          │
# │ Movie ┆ 1        ┆ 1          │
# │ Sport ┆ 1        ┆ 1          │
# └───────┴──────────┴────────────┘}

# Generate SPSS syntax
print(survey.sps)
# VARIABLE LABELS gender 'gender'.
# VALUE LABELS gender 1 'Female'
# 2 'Male'.
# VARIABLE LEVEL gender (NOMINAL).
# ...
```

---

## 📥 Usage

### Load Data

```python
# Available read functions
survy.read_csv
survy.read_excel
survy.read_json
survy.read_polars
```

#### CSV / Excel

```python
survey = survy.read_csv(
    "data.csv",               # Path to data file
    compact_ids=["hobby", "animal"],  # Specify compact multiselect columns
    compact_separator=";",    # Delimiter used to split compact column values
    auto_detect=False,        # Set True to infer multiselect columns automatically
    name_pattern="id(_multi)?",  # Pattern to detect multiselect columns by name
)
```

#### JSON

```python
# Expected format: data.json
# {
#     "variables": [
#         {
#             "id": "gender",
#             "data": ["Male", "Female", "Male"],
#             "label": "",
#             "value_indices": {"Female": 1, "Male": 2},
#         },
#         {"id": "yob", "data": [2000, 1999, 1998], "label": "", "value_indices": {}},
#         {
#             "id": "hobby",
#             "data": [["Book", "Sport"], ["Movie", "Sport"], ["Movie"]],
#             "label": "",
#             "value_indices": {"Book": 1, "Movie": 2, "Sport": 3},
#         },
#         {
#             "id": "animal",
#             "data": [["Cat", "Dog"], ["Dog"], ["Cat"]],
#             "label": "",
#             "value_indices": {"Cat": 1, "Dog": 2},
#         },
#     ]
# }

survey = survy.read_json("data.json")
```

#### Polars DataFrame

```python
# Input df (polars.DataFrame):
# ┌────────┬──────┬─────────────┬──────────┬──────────┐
# │ gender ┆ yob  ┆ hobby       ┆ animal_1 ┆ animal_2 │
# │ ---    ┆ ---  ┆ ---         ┆ ---      ┆ ---      │
# │ str    ┆ i64  ┆ str         ┆ str      ┆ str      │
# ╞════════╪══════╪═════════════╪══════════╪══════════╡
# │ Male   ┆ 2000 ┆ Sport;Book  ┆ Cat      ┆ Dog      │
# │ Female ┆ 1999 ┆ Sport;Movie ┆          ┆ Dog      │
# │ Male   ┆ 1998 ┆ Movie       ┆ Cat      ┆          │
# └────────┴──────┴─────────────┴──────────┴──────────┘

survey = survy.read_polars(df)
```

---

### Work with Survey

```python
print(survey)
# Survey (4 variables)
#   Variable(id=gender, label=gender, value_indices={'Female': 1, 'Male': 2}, base=3)
#   Variable(id=yob, label=yob, value_indices={}, base=3)
#   Variable(id=hobby, label=hobby, value_indices={'Book': 1, 'Movie': 2, 'Sport': 3}, base=3)
#   Variable(id=animal, label=animal, value_indices={'Cat': 1, 'Dog': 2}, base=3)
```

#### Methods & Properties

| Method / Property | Description |
|-------------------|-------------|
| `get_df()` | Return survey data as a `polars.DataFrame` |
| `update()` | Update metadata (labels, value indices) of variables |
| `add()` | Add a variable to the survey |
| `drop()` | Remove a variable from the survey |
| `filter()` | Filter data by given logic |
| `sort()` | Sort variables by given logic |
| `to_csv()` | Export to CSV |
| `to_excel()` | Export to Excel |
| `to_json()` | Export to JSON |
| `to_spss()` | Export to SPSS format |
| `.variables` | Collection of all variables |
| `.sps` | Render SPSS syntax string |

#### DataFrame Output Formats

The `get_df()` method supports flexible output through `select_dtype` and `multiselect_dtype` parameters:

```python
# Compact multiselect (list columns)
print(survey.get_df(select_dtype="text", multiselect_dtype="compact"))
# ┌────────┬──────┬────────────────────┬────────────────┐
# │ gender ┆ yob  ┆ hobby              ┆ animal         │
# │ ---    ┆ ---  ┆ ---                ┆ ---            │
# │ str    ┆ i64  ┆ list[str]          ┆ list[str]      │
# ╞════════╪══════╪════════════════════╪════════════════╡
# │ Male   ┆ 2000 ┆ ["Book", "Sport"]  ┆ ["Cat", "Dog"] │
# │ Female ┆ 1999 ┆ ["Movie", "Sport"] ┆ ["Dog"]        │
# │ Male   ┆ 1998 ┆ ["Movie"]          ┆ ["Cat"]        │
# └────────┴──────┴────────────────────┴────────────────┘

# Wide text format (split columns, numeric category codes)
print(survey.get_df(select_dtype="number", multiselect_dtype="text"))
# ┌────────┬──────┬─────────┬─────────┬─────────┬──────────┬──────────┐
# │ gender ┆ yob  ┆ hobby_1 ┆ hobby_2 ┆ hobby_3 ┆ animal_1 ┆ animal_2 │
# │ ---    ┆ ---  ┆ ---     ┆ ---     ┆ ---     ┆ ---      ┆ ---      │
# │ i64    ┆ i64  ┆ str     ┆ str     ┆ str     ┆ str      ┆ str      │
# ╞════════╪══════╪═════════╪═════════╪═════════╪══════════╪══════════╡
# │ 2      ┆ 2000 ┆ Book    ┆ null    ┆ Sport   ┆ Cat      ┆ Dog      │
# │ 1      ┆ 1999 ┆ null    ┆ Movie   ┆ Sport   ┆ null     ┆ Dog      │
# │ 2      ┆ 1998 ┆ null    ┆ Movie   ┆ null    ┆ Cat      ┆ null     │
# └────────┴──────┴─────────┴─────────┴─────────┴──────────┴──────────┘

# Fully numeric (binary-encoded multiselect)
print(survey.get_df(select_dtype="number", multiselect_dtype="number"))
# ┌────────┬──────┬─────────┬─────────┬─────────┬──────────┬──────────┐
# │ gender ┆ yob  ┆ hobby_1 ┆ hobby_2 ┆ hobby_3 ┆ animal_1 ┆ animal_2 │
# │ ---    ┆ ---  ┆ ---     ┆ ---     ┆ ---     ┆ ---      ┆ ---      │
# │ i64    ┆ i64  ┆ i8      ┆ i8      ┆ i8      ┆ i8       ┆ i8       │
# ╞════════╪══════╪═════════╪═════════╪═════════╪══════════╪══════════╡
# │ 2      ┆ 2000 ┆ 1       ┆ 0       ┆ 1       ┆ 1        ┆ 1        │
# │ 1      ┆ 1999 ┆ 0       ┆ 1       ┆ 1       ┆ 0        ┆ 1        │
# │ 2      ┆ 1998 ┆ 0       ┆ 1       ┆ 0       ┆ 1        ┆ 0        │
# └────────┴──────┴─────────┴─────────┴─────────┴──────────┴──────────┘
```

#### Updating Survey Metadata

```python
survey.update(
    [
        {"id": "gender", "label": "Please indicate your gender."},
        {"id": "hobby", "value_indices": {"Sport": 1, "Book": 2, "Movie": 3}},
    ]
)
print(survey)
# Survey (4 variables)
#   Variable(id=gender, label=Please indicate your gender., value_indices={'Female': 1, 'Male': 2}, base=3)
#   Variable(id=yob, label=yob, value_indices={}, base=3)
#   Variable(id=hobby, label=hobby, value_indices={'Sport': 1, 'Book': 2, 'Movie': 3}, base=3)
#   Variable(id=animal, label=animal, value_indices={'Cat': 1, 'Dog': 2}, base=3)
```

---

### Work with Variables

```python
hobby = survey["hobby"]
print(hobby)
# Variable(id=hobby, label=hobby, value_indices={'Book': 1, 'Movie': 2, 'Sport': 3}, base=3)
```

#### Methods & Properties

| Method / Property | Description |
|-------------------|-------------|
| `get_df()` | Return variable data as a `polars.DataFrame` |
| `to_dict()` | Serialize variable to a dictionary |
| `replace()` | Remap values using a given mapping |
| `.series` | Variable data as a `polars.Series` |
| `.label` | Variable label string |
| `.value_indices` | Mapping of response values to numeric codes |
| `.vtype` | Variable type: `select`, `multi_select`, or `number` |
| `.base` | Count of valid (non-null) responses |
| `.len` | Total number of responses |
| `.frequencies` | DataFrame of counts and proportions per value |
| `.sps` | SPSS syntax string for this variable |

#### Variable DataFrame Formats

```python
hobby = survey["hobby"]

# Compact (list column)
hobby.get_df("compact")
# shape: (3, 1)
# ┌────────────────────┐
# │ hobby              │
# │ ---                │
# │ list[str]          │
# ╞════════════════════╡
# │ ["Book", "Sport"]  │
# │ ["Movie", "Sport"] │
# │ ["Movie"]          │
# └────────────────────┘

# Wide text (split columns)
hobby.get_df("text")
# shape: (3, 3)
# ┌─────────┬─────────┬─────────┐
# │ hobby_1 ┆ hobby_2 ┆ hobby_3 │
# │ ---     ┆ ---     ┆ ---     │
# │ str     ┆ str     ┆ str     │
# ╞═════════╪═════════╪═════════╡
# │ Book    ┆ null    ┆ Sport   │
# │ null    ┆ Movie   ┆ Sport   │
# │ null    ┆ Movie   ┆ null    │
# └─────────┴─────────┴─────────┘

# Binary-encoded (split columns, 0/1)
hobby.get_df("number")
# shape: (3, 3)
# ┌─────────┬─────────┬─────────┐
# │ hobby_1 ┆ hobby_2 ┆ hobby_3 │
# │ ---     ┆ ---     ┆ ---     │
# │ i8      ┆ i8      ┆ i8      │
# ╞═════════╪═════════╪═════════╡
# │ 1       ┆ 0       ┆ 1       │
# │ 0       ┆ 1       ┆ 1       │
# │ 0       ┆ 1       ┆ 0       │
# └─────────┴─────────┴─────────┘
```

#### Updating Variables

```python
hobby.value_indices = {"Sport": 1, "Book": 2, "Movie": 3}
hobby.label = "Please tell us your hobbies."
print(hobby)
# Variable(id=hobby, label=Please tell us your hobbies., value_indices={'Sport': 1, 'Book': 2, 'Movie': 3}, base=3)

hobby.replace({"Book": "Reading"})
print(hobby)
# Variable(id=hobby, label=Please tell us your hobbies., value_indices={'Movie': 1, 'Reading': 2, 'Sport': 3}, base=3)
```

---

### Analyze

#### Cross-tabulation

The `survy.crosstab()` function supports count, percent, and mean aggregations, with optional significance testing and filtering.

**Signature:**
```python
survy.crosstab(
    banner,       # Column variable (e.g., gender)
    stub,         # Row variable (e.g., hobby)
    filter=None,  # Optional filter variable; creates one table per category
    aggfunc="count",  # Aggregation: "count", "percent", or "mean"
    alpha=0.1     # Significance level for column proportion tests
)
```

**Count:**
```python
print(survy.crosstab(survey["gender"], survey["hobby"], aggfunc="count", alpha=0.1))
# {'Total': shape: (3, 3)
# ┌───────┬──────────┬────────────┐
# │ hobby ┆ Male (A) ┆ Female (B) │
# │ ---   ┆ ---      ┆ ---        │
# │ str   ┆ str      ┆ str        │
# ╞═══════╪══════════╪════════════╡
# │ Book  ┆ 1        ┆ 0          │
# │ Movie ┆ 1        ┆ 1          │
# │ Sport ┆ 1        ┆ 1          │
# └───────┴──────────┴────────────┘}
```

**Percent:**
```python
print(survy.crosstab(survey["gender"], survey["hobby"], aggfunc="percent", alpha=0.1))
# {'Total': shape: (3, 3)
# ┌───────┬──────────┬────────────┐
# │ hobby ┆ Male (A) ┆ Female (B) │
# │ ---   ┆ ---      ┆ ---        │
# │ str   ┆ str      ┆ str        │
# ╞═══════╪══════════╪════════════╡
# │ Book  ┆ 0.5      ┆ 0.0        │
# │ Movie ┆ 0.5      ┆ 1.0        │
# │ Sport ┆ 0.5      ┆ 1.0        │
# └───────┴──────────┴────────────┘}
```

**Mean (numeric variable):**
```python
print(survy.crosstab(survey["gender"], survey["yob"], aggfunc="mean", alpha=0.1))
# {'Total': shape: (1, 3)
# ┌─────┬─────────┬─────────┐
# │ yob ┆ Female  ┆ Male    │
# │ --- ┆ ---     ┆ ---     │
# │ str ┆ str     ┆ str     │
# ╞═════╪═════════╪═════════╡
# │ yob ┆ 1999.0  ┆ 1999.0  │
# └─────┴─────────┴─────────┘}
```

**With filter variable** (produces one table per filter category):
```python
print(
    survy.crosstab(
        survey["gender"],
        survey["hobby"],
        filter=survey["animal"],
        aggfunc="count",
        alpha=0.1,
    )
)
# {'Cat': shape: (3, 2)
# ┌───────┬──────────┐
# │ hobby ┆ Male (A) │
# ...
# 'Dog': shape: (3, 3)
# ┌───────┬──────────┬────────────┐
# │ hobby ┆ Male (A) ┆ Female (B) │
# ...
# └───────┴──────────┴────────────┘}
```

---

## 🧠 Design Philosophy

- Keep survey logic explicit — variables, labels, and value mappings are first-class objects
- Treat multiselect questions as a native data type, not a post-processing concern
- Provide a clean abstraction over high-performance data processing

---

## 🤝 Contributing

Contributions are welcome!
Feel free to open issues or submit pull requests on [GitHub](https://github.com/hoanghaoha/survy).

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🔗 References

- Powered by **[Polars](https://pola.rs/)** for fast data processing
