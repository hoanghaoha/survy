# survy

[![PyPI version](https://img.shields.io/pypi/v/survy.svg)](https://pypi.org/project/survy/)
[![License](https://img.shields.io/pypi/l/survy.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/survy.svg)](https://pypi.org/project/survy/)
[![CI](https://github.com/hoanghaoha/survy/actions/workflows/ci.yml/badge.svg)](https://github.com/hoanghaoha/survy/actions)

**Process, transform, and analyze survey-format data with a clean and simple API.**

---

## 📦 Overview

`survy` is a lightweight Python library built for working efficiently with survey data.
It simplifies the full workflow—from raw data ingestion to transformation and analysis—while preserving survey-specific structures like multiselect questions.

---

## ✨ Features

* 🔹 Multiselect as a first-class concept
* 🔹 Read & write multiple formats: CSV, Excel, JSON, SPSS, etc.
* 🔹 Clean, minimal, and expressive API
* 🔹 Built-in tools for validation, tracking, and analysis

---

## 🚀 Installation

```bash
pip install survy
```

---

## ⚡ Quick Demo

### Sample data 

`data.csv`
```csv
id,Q1,Q2_1,Q2_2,Q2_3
1,a,a,b,
2,b,a,,c
3,a,,b,c
```

`data_compact.csv`
```csv
id,Q1,Q2
1,a,a;b
2,b,a
3,a,b;c
```

---

### Load and analyze

```python
import survy

# Load dataset with compact multiselect column
survey = survy.read_csv("data.csv")
#or
survey = survy.read_csv(
    "data_compact.csv",
    compact_ids=["Q2"],
    compact_separator=";"
)

# Inspect variable
q1 = survey["Q1"]
print(q1.frequencies)

# Crosstab analysis
crosstab = survy.crosstab(survey["Q1"], survey["Q2"])
print(crosstab)
```

---

## 📥 Usage

### Load data

```python
survey = survy.read_csv("data.csv")
```

With compact multiselect:

```python
survey = survy.read_csv(
    "data.csv",
    compact_ids=["Q2"],
    compact_separator=";"
)
```

---

### Get DataFrame

```python
survey.get_df(select_dtype="text", multiselect_dtype="compact")
```

---

### Work with variables

```python
q1 = survey["Q1"]

print(q1.vtype)
print(q1.value_indices)
print(q1.base)
print(q1.frequencies)
```

---

### Update variables

```python
q1.label = "Question 1"
q1.value_indices = {"b": 1, "a": 2}
```

Batch update:

```python
survey.update([
    {
        "id": "Q1",
        "label": "Question 1",
        "value_indices": {"b": 1, "a": 2}
    }
])
```

---

### Export

```python
survey.to_csv(name="output")
survey.to_spss(name="output")
```

---

### Analyze

```python
crosstab = survy.crosstab(survey["Q1"], survey["Q2"])
print(crosstab)
```

---

## 🧠 Design Philosophy

* Keep survey logic explicit (variables, labels, value mappings)
* Treat multiselect questions as a core data type
* Provide a clean abstraction over high-performance data processing

---

## 🤝 Contributing

Contributions are welcome!
Feel free to open issues or submit pull requests.

---

## 📄 License

MIT License

---

## 🔗 References

* Powered by **Polars** for fast data processing

---
