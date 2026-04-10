---
name: survey-analysis
description: >
  Use this skill whenever the user wants to work with survey data using the `survy` Python library.
  Triggers include: loading or reading survey CSV/Excel/JSON files, handling multiselect (multi-choice)
  questions, computing frequency tables or crosstabs, exporting survey data to SPSS (.sav) or other formats,
  updating variable labels or value indices, transforming survey data between wide/compact formats,
  filtering respondents, replacing values, adding/dropping/sorting variables, or any task involving
  survy's API (read_csv, read_excel, read_json, read_polars, crosstab, survey["Q1"],
  to_spss, to_csv, to_excel, to_json, etc.).
  Also trigger when the user says things like "analyze my survey", "process questionnaire data",
  "build a survey analysis script", or "help me with survy". Always read this skill before writing
  any survy code — it contains the correct API, patterns, and gotchas.
---

# survy — Survey Data Analysis Skill

`survy` is a lightweight Python library for processing, transforming, and analyzing survey data.
Its central design principle is treating survey constructs — especially multiselect questions — as
first-class concepts rather than awkward DataFrame workarounds.

**Install**: Always install the latest version — `pip install --upgrade survy`
**Powered by**: Polars (all DataFrames returned are Polars, not pandas)

---

## 1. Core Objects

### Survey

Top-level container. Created via `read_*` functions — never instantiate directly.
Access variables with `survey["Q1"]`. Print for a compact summary.

### Variable

Wraps a single Polars Series plus survey metadata. Key attributes:

| Attribute         | Type                | Description |
|-------------------|---------------------|-------------|
| `id`              | `str`               | Column name (read/write via property) |
| `label`           | `str`               | Human-readable label (read/write); defaults to `id` if unset |
| `vtype`           | `VarType`           | One of `VarType.SELECT`, `VarType.MULTISELECT`, `VarType.NUMBER` |
| `value_indices`   | `dict[str, int]`    | Answer code → numeric index mapping; always empty `{}` for NUMBER |
| `base`            | `int`               | Count of non-null/non-empty responses |
| `len`             | `int`               | Total row count including nulls |
| `dtype`           | `polars.DataType`   | Underlying Polars dtype |
| `frequencies`     | `polars.DataFrame`  | Frequency table (value, count, proportion) |
| `sps`             | `str`               | SPSS syntax for this variable |

---

## 2. Reading Data

All readers return a `Survey` object. The key challenge survy
solves at read time is recognizing **multiselect questions** —
questions where one respondent can choose multiple answers.
Raw data encodes these in two very different layouts, and survy
needs to know which layout it's looking at so it can merge the
data into a single logical variable.

### Multiselect: Compact Format vs Wide Format

**Compact format** stores all selected answers in a single
cell, joined by a separator (typically `;`).
One column = one question.

```
id,  gender,  hobby
1,   Male,    Sport;Book
2,   Female,  Sport;Movie
3,   Male,    Movie
```

Here `hobby` is one column. The cell `"Sport;Book"` means the
respondent chose both Sport and Book. survy splits this cell on
the separator to recover the individual choices.

**Wide format** spreads each possible answer across its own
column, using a shared prefix plus a numeric suffix
(`_1`, `_2`, ...). Multiple columns = one question.

```
id,  gender,  hobby_1,  hobby_2,  hobby_3
1,   Male,    Book,     ,         Sport
2,   Female,  ,         Movie,    Sport
3,   Male,    ,         Movie,
```

Here `hobby_1`, `hobby_2`, `hobby_3` are three columns that
together represent the single `hobby` question. survy groups
them by matching the prefix pattern and merges them into one
multiselect variable named `hobby`.

**After reading**, both formats produce the exact same Survey
variable internally — a `MULTISELECT` variable whose data is a
sorted list of chosen values per respondent:

```
hobby: [["Book", "Sport"], ["Movie", "Sport"], ["Movie"]]
```

### How survy detects each format

**Wide format** is detected via `name_pattern` — a format template (NOT a raw regex)
with two named tokens and a set of reserved separators:

- **Tokens**: `id` (base variable name), `multi` (suffix for wide columns)
- **Reserved separators**: `_`, `.`, `:` — these are always treated as delimiters
  between tokens when parsing column names

With the default pattern `"id(_multi)?"`:

- `hobby_1` → `id="hobby"`, `multi="1"` → grouped as wide multiselect
- `hobby_2` → same `id="hobby"` → merged with `hobby_1`
- `gender` → no suffix → normal column

Other patterns:

- `"id.multi"` → matches `Q1.1`, `Q1.2`, ...
- `"id:multi"` → matches `Q1:a`, `Q1:b`, ...

**Separator conflict warning**: If a column name contains more than one reserved
separator (e.g. `my.var_1`), `parse_id` will fail because it can't unambiguously
split the name into tokens. Before loading, rename such columns so only one
separator is used (e.g. rename `my.var_1` to `myvar_1` or `my@var_1`).

**Compact format** is NOT detected by default because a semicolon in a cell
could be regular text. You must tell survy which columns are compact in one of two ways:

1. **`compact_ids`** — explicitly list the column IDs that are compact multiselect.
2. **`auto_detect=True`** — survy scans every column for the `compact_separator`
   character; any column containing it in at least one cell is treated as compact.

**Rule**: Do NOT combine `auto_detect=True` with `compact_ids` in the same call.

### Shared Reader Parameters (read_csv, read_excel, read_polars only)

These parameters control multiselect detection and apply to
`read_csv`, `read_excel`, and `read_polars`. They do NOT apply
to `read_json` (which reads survy's own format where variable
types are already resolved).

| Parameter           | Type              | Default          | Description |
|---------------------|-------------------|------------------|-------------|
| `compact_ids`       | `list[str] \| None` | `None`           | Column IDs to treat as compact multiselect |
| `compact_separator` | `str`             | `";"`            | Separator used to split compact cells |
| `auto_detect`       | `bool`            | `False`          | Auto-detect compact columns by scanning for separator |
| `name_pattern`      | `str`             | `"id(_multi)?"` | Format template for wide column names. Tokens: `id`, `multi`. Separators: `_` `.` `:`. Not a raw regex. |

### read_csv / read_excel

```python
import survy

# --- Compact format data ---

# Option A: you know which columns are compact
survey = survy.read_csv("data_compact.csv", compact_ids=["hobby"], compact_separator=";")

# Option B: let survy scan for the separator automatically
survey = survy.read_csv("data_compact.csv", auto_detect=True, compact_separator=";")

# --- Wide format data ---
# Wide detection is automatic via name_pattern (default works for Q1_1, Q1_2, ...)
survey = survy.read_csv("data_wide.csv")

# Custom name_pattern if your columns use a different suffix convention
survey = survy.read_csv("data_wide.csv", name_pattern="id(_multi)?")

# --- Mixed: some columns are wide, some are compact ---
survey = survy.read_csv("data_mixed.csv", name_pattern="id(_multi)?", auto_detect=True)

# Excel — identical API to read_csv
survey = survy.read_excel("data.xlsx", auto_detect=True, compact_separator=";")
```

### read_json

Reads a survy-format JSON file. The file must have this exact structure:

```json
{
  "variables": [
    {
      "id": "gender",
      "data": ["Male", "Female", "Male"],
      "label": "Gender of respondent",
      "value_indices": {"Female": 1, "Male": 2}
    },
    {
      "id": "yob",
      "data": [2000, 1999, 1998],
      "label": "",
      "value_indices": {}
    },
    {
      "id": "hobby",
      "data": [["Book", "Sport"], ["Movie", "Sport"], ["Movie"]],
      "label": "Hobbies",
      "value_indices": {"Book": 1, "Movie": 2, "Sport": 3}
    }
  ]
}
```

**Key rules for the JSON structure:**

- Top-level key must be `"variables"` (a list of variable objects).
- Each variable must have `"id"`, `"data"`, `"label"`, and `"value_indices"`.
- SELECT variables: `"data"` is a flat list of strings (or nulls).
- NUMBER variables: `"data"` is a flat list of numbers;
  `"value_indices"` must be `{}`.
- MULTISELECT variables: `"data"` is a list of lists of strings.
- `"value_indices"` maps each answer text to a numeric index;
  only applied when non-empty.
- **Read vs Write difference**: `to_json()` writes an extra
  `"vtype"` field per variable (e.g. `"select"`,
  `"multi_select"`, `"number"`). `read_json()` ignores this
  field — it re-infers the type from the data. So if you're
  building JSON manually, you can omit `"vtype"`.

```python
survey = survy.read_json("data.json")
```

### read_polars

Construct a Survey from an existing Polars DataFrame.
Extra parameter `exclude_null` (default `True`) drops columns
with no responses or all-empty lists.
read_polars also have same concepts of wide/ compact format
as read_csv.

```python
import polars, survy

df = polars.DataFrame({
    "gender": ["Male", "Female", "Male"],
    "yob": [2000, 1999, 1998],
    "hobby": ["Sport;Book", "Sport;Movie", "Movie"],
    "animal_1": ["Cat", "", "Cat"],
    "animal_2": ["Dog", "Dog", ""],
})
survey = survy.read_polars(df, auto_detect=True)
```

---

## 3. Modifying the Survey

### survey.update() — batch label/value_indices

```python
survey.update([
    {"id": "Q1", "label": "Satisfaction", "value_indices": {"good": 1, "bad": 2}},
    {"id": "Q2", "label": "Channels used"},
])
```

Silently skips `value_indices` for NUMBER variables.
Warns and skips unknown IDs.

### survey.add() — add a variable

```python
survey.add(some_variable)           # Variable object
survey.add(polars.Series("new", [1, 2, 3]))  # auto-wrapped into Variable
```

If the ID already exists, a numeric suffix is appended (e.g. `"Q1#1"`).

### survey.drop() — remove a variable

```python
survey.drop("Q3")   # silently ignored if not found
```

### survey.sort() — reorder variables

```python
survey.sort()                                      # alphabetical by id (default)
survey.sort(key=lambda v: v.base, reverse=True)    # by response count desc
```

### variable.replace() — recode values

```python
survey["gender"].replace({"Male": "M", "Female": "F"})
```

Works for both SELECT and MULTISELECT. Automatically rebuilds `value_indices`.

### Direct property assignment

```python
v = survey["Q1"]
v.id = "satisfaction"
v.label = "Overall satisfaction"
v.value_indices = {"very_satisfied": 1, "satisfied": 2, "neutral": 3}
```

**Caution on value_indices setter**: Raises
`DataStructureError` if any existing value in the data is
missing from the new mapping. You must cover ALL values
present in the data.

---

## 4. Filtering

Returns a **new** Survey (original is not mutated).

```python
filtered = survey.filter("hobby", ["Sport", "Book"])
filtered = survey.filter("gender", "Male")   # single value also works
```

For MULTISELECT, a row is kept if **any** of its selected values appears in the filter list.

---

## 5. Getting a DataFrame

```python
df = survey.get_df(
    select_dtype="text",          # "text" | "number"
    multiselect_dtype="compact",  # "compact" | "text" | "number"
)
```

**`select_dtype`**: `"text"` keeps string codes (default); `"number"` converts via `value_indices`.

**`multiselect_dtype`**:

- `"compact"` → one `List[str]` column per multiselect (default)
- `"text"` → expands to wide columns `Q_1`, `Q_2`, ... with string or `null`
- `"number"` → expands to wide columns with `1`/`0` binary flags

**Returns Polars DataFrame** — use Polars methods, not pandas.

**Valid dtype literals**: `"text"`, `"number"`, `"compact"`. Never `"numeric"` or `"string"`.

---

## 6. Analysis

### Frequency table

```python
survey["Q1"].frequencies
# → Polars DataFrame: columns [variable_id, "count", "proportion"]
```

### Crosstab

```python
result = survy.crosstab(
    column=survey["gender"],     # grouping variable (columns)
    row=survey["hobby"],         # analyzed variable (rows)
    filter=None,                 # optional: segment by another variable
    aggfunc="count",             # "count" | "percent" | "mean" | "median" | "sum"
    alpha=0.05,                  # significance level for stat tests
)
# Returns dict[str, polars.DataFrame]
# Key is "Total" when no filter, or each filter-value when filter is provided
```

**aggfunc options**:

- `"count"` — cell counts with significance letter labels (z-test)
- `"percent"` — column-wise proportions with significance labels
- Numeric (`"mean"`, `"median"`, `"sum"`) — aggregates row variable; Welch's t-test for significance

**filter**: Pass a Variable to segment the crosstab into one table per filter value.

---

## 7. Exporting

All exports take a **directory path** (not file path) + optional `name` (base filename).

### to_csv / to_excel

Writes three files per export:

- **`{name}_data.csv`** — the actual survey responses. Format depends on `compact` param.
- **`{name}_variables_info.csv`** — variable metadata with columns: `id`, `vtype` (SINGLE/MULTISELECT/NUMBER), `label`.
- **`{name}_values_info.csv`** — value-to-index mappings with columns: `id`, `text`, `index`.

The `compact` parameter (default `False`) controls how multiselect variables appear in the
data file: `True` joins values into one cell (e.g. `"Book;Sport"`), `False` expands into
wide columns (e.g. `hobby_1`, `hobby_2`, `hobby_3`).

```python
# Default (compact=False) — multiselect expanded to wide columns
survey.to_csv("output/", name="results")

# Compact mode — multiselect joined into single cells
survey.to_csv("output/", name="results", compact=True, compact_separator=";")

# Excel — identical API and output structure (.xlsx files instead of .csv)
survey.to_excel("output/", name="results")
survey.to_excel("output/", name="results", compact=True)
```

### to_spss

Writes `{name}.sav` (data) + `{name}.sps` (syntax). Requires `pyreadstat`.

```python
survey.to_spss("output/", name="results")
```

### to_json

Writes `{name}.json` in the same structure `read_json` expects (see Section 2), plus an
extra `"vtype"` field per variable that `read_json` ignores on re-read. Pretty-printed
with 4-space indent, non-ASCII preserved (`ensure_ascii=False`).

```python
survey.to_json("output/", name="results")
```

**Common mistake**: Do NOT pass `"output/results.csv"`. Pass directory + `name=`.

### SPSS Syntax

```python
print(survey.sps)  # full syntax: VARIABLE LABELS, VALUE LABELS, MRSETS, CTABLES
```

---

## 8. Gotchas & Rules

1. **`auto_detect` vs `compact_ids`**: Never combine both.
2. **`value_indices` setter must cover all existing data values** —
   raises `DataStructureError` otherwise.
3. **`value_indices` is silently skipped for NUMBER variables**
   (in `update()` and direct set).
4. **Export path is a directory, not a file**.
5. **`get_df()` returns Polars, not pandas**.
6. **`filter()` returns a new Survey** — does not mutate.
7. **Empty strings become `None`** during CSV/Excel read.
8. **Multiselect values are sorted alphabetically** within each row.
9. **All variables in a crosstab must have the same row count**.
10. **`read_csv` raises `FileTypeError`** if the file extension
    is not `.csv`. Same for `read_excel` with non-`.xlsx`.
11. **`to_csv`/`to_excel` default is `compact=False`** —
    multiselect variables are expanded to wide columns unless
    you explicitly pass `compact=True`.
12. **Column names must not contain multiple reserved separators**
    (`_`, `.`, `:`). If a column like `my.var_1` uses more than
    one, `parse_id` will fail. Rename before loading so only one
    separator appears (e.g. `myvar_1`).

---

## 9. Quick Reference

| Task | Code |
|---|---|
| Load CSV auto-detect | `survy.read_csv("f.csv", auto_detect=True, compact_separator=";")` |
| Load CSV explicit compact | `survy.read_csv("f.csv", compact_ids=["Q2"], compact_separator=";")` |
| Load CSV wide format | `survy.read_csv("f.csv", name_pattern="id(_multi)?")` (wide detected automatically) |
| Load JSON | `survy.read_json("f.json")` |
| Load from Polars DF | `survy.read_polars(df, auto_detect=True)` |
| Inspect variable | `survey["Q1"].vtype`, `.base`, `.len`, `.label`, `.value_indices`, `.dtype` |
| Frequencies | `survey["Q1"].frequencies` |
| Crosstab count | `survy.crosstab(survey["Q1"], survey["Q2"])` |
| Crosstab percent | `survy.crosstab(survey["Q1"], survey["Q2"], aggfunc="percent")` |
| Crosstab with filter | `survy.crosstab(survey["col"], survey["row"], filter=survey["seg"])` |
| Crosstab mean | `survy.crosstab(survey["col"], survey["row"], aggfunc="mean")` |
| Filter respondents | `survey.filter("Q1", ["a", "b"])` |
| Replace values | `survey["Q1"].replace({"old": "new"})` |
| Add variable | `survey.add(polars.Series("x", [1,2,3]))` |
| Drop variable | `survey.drop("Q3")` |
| Sort variables | `survey.sort(key=lambda v: v.id)` |
| Batch update labels | `survey.update([{"id":"Q1","label":"...","value_indices":{...}}])` |
| Get compact DF | `survey.get_df()` |
| Get wide binary DF | `survey.get_df(multiselect_dtype="number")` |
| Export CSV | `survey.to_csv("output/", name="results")` |
| Export SPSS | `survey.to_spss("output/", name="results")` |
| Export JSON | `survey.to_json("output/", name="results")` |
| SPSS syntax string | `survey.sps` |
| Serialize variable | `survey["Q1"].to_dict()` |

---

## 10. Reference Files

- `references/api_reference.md` — Complete method signatures with all parameters and return types
- `scripts/validate_survey.py` — Loads a survey file, checks missing labels/value_indices, prints report
- `scripts/batch_export.py` — Reads a survey and exports to CSV, Excel, SPSS, and JSON
- `assets/sample_data.csv` — Wide-format sample dataset
- `assets/sample_data_compact.csv` — Compact-format sample dataset
