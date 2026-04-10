# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.2] - 2026-04-10

### Added

- **`read_spss(path, name_pattern)`** — read SPSS `.sav` files directly into a `Survey`. Value labels are applied automatically (text labels, not numeric codes). Wide multiselect columns (e.g. `hobby_1`, `hobby_2`) are detected and merged via `name_pattern`, consistent with `read_csv` and `read_excel`. Compact multiselect parameters (`compact_ids`, `auto_detect`) are intentionally omitted — SAV is always wide format.
- **Agent skill: `name_pattern` documentation** — `SKILL.md` and `api_reference.md` updated to fully explain the `name_pattern` parameter, including token syntax (`id`, `multi`), reserved separators (`_`, `.`, `:`), and examples for different column naming conventions.

---

## [0.2.1] - 2026-04-09

### Added

- **Agent skill (`SKILL.md`)** — a structured reference document designed for LLM-based coding agents, enabling accurate code generation against the `survy` API. The skill covers the full public API surface including reading, modifying, filtering, analyzing, and exporting survey data, with explicit documentation of compact vs wide multiselect formats, JSON I/O schema, and common gotchas.
- **`references/api_reference.md`** — complete method signatures with all parameters, defaults, and return types for quick agent lookup.
- **`scripts/validate_survey.py`** — utility script that loads a survey file and reports missing labels or unset `value_indices`.
- **`scripts/batch_export.py`** — utility script that reads a survey and exports to CSV, Excel, SPSS, and JSON in one pass.
- **`assets/sample_data.csv`** and **`assets/sample_data_compact.csv`** — sample datasets in wide and compact multiselect formats for testing and demonstration.

### Fixed

- Survey.update() auto set label to "" if not specify.

---

## [0.2.0] - 2026-04-08

### Added

- **Crosstab significance testing** — statistical significance tests are now available as part of crosstab analysis.
- **Docstrings** — comprehensive docstrings added across the entire public API.
- **Integration tests** — expanded test suite with integration-level coverage.

### Notes

- The public API remains largely unchanged from `0.1.x` and existing code should continue to work without modification.

---

## [0.1.4] - 2026-04-06

### Added

- `Survey.__str__()` — human-readable string representation for `Survey` objects.
- `Survey` handle functions — added `add`, `drop`, `filter`, and `sort` operations directly on `Survey`.
- `Variable.id` setter — `id` is now assignable via a property setter.

---

## [0.1.3] - 2026-04-06

### Fixed

- SPSS label handling — `utils.spss` now correctly processes only string labels, preventing errors on non-string label types.

---

## [0.1.2] - 2026-04-06

### Added

- `Variable.__str__()` and `Variable.replace()` — string representation and value replacement support for `Variable` objects.
- `auto_detect` parameter — type inference is now available when reading data via `read_polars`, `read_csv`, and `read_excel`.

### Fixed

- SPSS export — resolved a string encoding error when exporting to SPSS format.
- Export path handling — corrected file path and filename resolution during export.

---

## [0.1.1] - 2026-04-05

### Fixed

- PyPI publishing workflow — resolved an issue with the automated release process using GitHub Actions.
- CI configuration — improved continuous integration setup for reliable automated releases.

---

## [0.1.0] - 2026-04-05

### Added

- **Initial release of `survy`.**
- Data ingestion from CSV, Excel, JSON, and SPSS formats.
- Support for compact multiselect encoding (e.g. `"a;b;c"`).
- Variable-level API including labels, value mappings, frequencies, and base calculation.
- Export to multiple output formats.
- Crosstab analysis utility.

### Notes

- This is the first public release. The API may evolve in future versions.
