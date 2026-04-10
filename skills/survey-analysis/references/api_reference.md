# survy API Reference

## Module-level Functions

### survy.read_csv(path, compact_ids=None, compact_separator=";", auto_detect=False, name_pattern="id(_multi)?") → Survey
Reads a `.csv` file. Raises `FileTypeError` if not `.csv`.

### survy.read_excel(path, compact_ids=None, compact_separator=";", auto_detect=False, name_pattern="id(_multi)?") → Survey
Reads a `.xlsx` file. Same params as `read_csv`.

### survy.read_spss(path, name_pattern="id(_multi)?") → Survey
Reads a `.sav` file. Raises `FileTypeError` if not `.sav`. Always wide format — no `compact_ids` or `auto_detect`. Value labels applied automatically (text, not numeric codes). Requires `pyreadstat`.

### survy.read_json(path) → Survey
Reads survy-format JSON with `{"variables": [...]}` structure.

### survy.read_polars(raw_df, compact_ids=None, compact_separator=";", auto_detect=False, name_pattern="id(_multi)?", exclude_null=True) → Survey
Converts a `polars.DataFrame` into a Survey. `exclude_null=True` drops columns with all-null or all-empty-list data.

### survy.crosstab(column, row, filter=None, aggfunc="count", alpha=0.05) → dict[str, polars.DataFrame]
Cross-tabulate `row` across `column` categories.
- `column` (Variable): grouping variable (becomes columns)
- `row` (Variable): analyzed variable (becomes rows)
- `filter` (Variable|None): optional segmentation variable
- `aggfunc`: `"count"` | `"percent"` | `"mean"` | `"median"` | `"sum"`
- `alpha` (float): significance level for stat tests
- Returns: dict mapping filter values (or `"Total"`) to DataFrames

---

## Survey Methods

### survey[variable_id] → Variable
Raises `KeyError` if not found.

### survey.add(variable: Variable | polars.Series) → None
Adds a variable. Auto-deduplicates ID with `#N` suffix.

### survey.drop(id: str) → None
Removes variable by ID. Silent if not found.

### survey.sort(key=lambda var: var.id, reverse=False) → None
Sorts variables in-place.

### survey.update(metadata: list[dict]) → None
Batch update. Each dict: `{"id": str, "label": str?, "value_indices": dict?}`.
Warns on unknown IDs. Skips `value_indices` for NUMBER. Missing `"label"` key resets to `""`.

### survey.filter(variable_id, values) → Survey
Returns new filtered Survey. `values` can be single value or list.

### survey.get_df(select_dtype="text", multiselect_dtype="compact") → polars.DataFrame
- `select_dtype`: `"text"` | `"number"`
- `multiselect_dtype`: `"compact"` | `"text"` | `"number"`

### survey.sps → str (property)
Full SPSS syntax string.

### survey.to_csv(path, name="survey", compact=False, compact_separator=";") → None
Writes 3 files: `{name}_data.csv` (responses), `{name}_variables_info.csv` (id/vtype/label), `{name}_values_info.csv` (id/text/index). Default `compact=False` expands multiselect to wide columns.

### survey.to_excel(path, name="survey", compact=False, compact_separator=";") → None
Same as to_csv but `.xlsx`.

### survey.to_spss(path, name="survey", encoding="utf-8") → None
Writes `{name}.sav` + `{name}.sps`.

### survey.to_json(path, name="survey", encoding="utf-8") → None
Writes `{name}.json`. Output includes `"vtype"` per variable (ignored by `read_json` on re-read).

---

## Variable Properties & Methods

| Member | Type | Notes |
|--------|------|-------|
| `id` | `str` (r/w) | Renames underlying Series |
| `label` | `str` (r/w) | Falls back to `id` if unset |
| `vtype` | `VarType` (ro) | SELECT, MULTISELECT, or NUMBER |
| `value_indices` | `dict[str,int]` (r/w) | Empty for NUMBER; setter validates coverage |
| `base` | `int` (ro) | Non-null count |
| `len` | `int` (ro) | Total rows |
| `dtype` | `polars.DataType` (ro) | |
| `frequencies` | `polars.DataFrame` (ro) | Columns: [var_id, count, proportion] |
| `sps` | `str` (ro) | SPSS syntax for this variable |
| `series` | `polars.Series` | Raw data |

### variable.replace(mapping: dict[str, str]) → None
Recodes values in-place. Works for SELECT and MULTISELECT. Rebuilds `value_indices`.

### variable.get_df(dtype="text") → polars.DataFrame
- `"text"` / `"number"` / `"compact"` (`"compact"` only valid for MULTISELECT)

### variable.to_dict() → dict
Keys: `id`, `data`, `label`, `value_indices`, `vtype`.
