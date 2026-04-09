"""
Validate a survey file: check for missing labels, unset value_indices, and print summary.

Usage:
    python validate_survey.py <path_to_csv> [--auto-detect] [--separator=";"]
"""

import sys
import survy


def validate(path: str, auto_detect: bool = True, separator: str = ";"):
    # Load the survey
    if path.endswith(".json"):
        survey = survy.read_json(path)
    elif path.endswith(".xlsx"):
        survey = survy.read_excel(
            path, auto_detect=auto_detect, compact_separator=separator
        )
    else:
        survey = survy.read_csv(
            path, auto_detect=auto_detect, compact_separator=separator
        )

    print(survey)
    print()

    # Check each variable for potential issues
    issues = []
    for var in survey.variables:
        if not var._label:
            issues.append(f"  [{var.id}] label not set (defaults to id)")
        if var.vtype.value != "number" and not var._value_indices:
            issues.append(
                f"  [{var.id}] value_indices auto-generated (not explicitly set)"
            )

    if issues:
        print("Potential issues:")
        for i in issues:
            print(i)
    else:
        print("All variables have labels and explicit value_indices.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data.csv"
    auto = "--auto-detect" in sys.argv
    sep = ";"
    for arg in sys.argv:
        if arg.startswith("--separator="):
            sep = arg.split("=", 1)[1]
    validate(path, auto, sep)
