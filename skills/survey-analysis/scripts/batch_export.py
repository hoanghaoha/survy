"""
Batch export a survey to all supported formats (CSV, Excel, SPSS, JSON).

Usage:
    python batch_export.py <input_path> <output_dir> [--name=survey] [--auto-detect] [--separator=";"]
"""

import sys
import os
import survy


def batch_export(
    input_path: str,
    output_dir: str,
    name: str = "survey",
    auto_detect: bool = True,
    separator: str = ";",
):
    os.makedirs(output_dir, exist_ok=True)

    # Load
    if input_path.endswith(".json"):
        survey = survy.read_json(input_path)
    elif input_path.endswith(".xlsx"):
        survey = survy.read_excel(
            input_path, auto_detect=auto_detect, compact_separator=separator
        )
    else:
        survey = survy.read_csv(
            input_path, auto_detect=auto_detect, compact_separator=separator
        )

    print(f"Loaded: {survey}")
    print()

    # Export CSV (compact + wide)
    survey.to_csv(
        output_dir, name=f"{name}_compact", compact=True, compact_separator=separator
    )
    survey.to_csv(output_dir, name=f"{name}_wide", compact=False)
    print(f"CSV exported to {output_dir}/")

    # Export Excel
    survey.to_excel(output_dir, name=name, compact=True)
    print(f"Excel exported to {output_dir}/")

    # Export JSON
    survey.to_json(output_dir, name=name)
    print(f"JSON exported to {output_dir}/")

    # Export SPSS (may fail if pyreadstat not installed)
    try:
        survey.to_spss(output_dir, name=name)
        print(f"SPSS exported to {output_dir}/")
    except ImportError:
        print("SPSS export skipped (pyreadstat not installed)")


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data.csv"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    name = "survey"
    auto = "--auto-detect" in sys.argv
    sep = ";"
    for arg in sys.argv:
        if arg.startswith("--name="):
            name = arg.split("=", 1)[1]
        if arg.startswith("--separator="):
            sep = arg.split("=", 1)[1]
    batch_export(input_path, output_dir, name, auto, sep)
