#!/usr/bin/env python3
"""Summarize template outputs by project.

Produces a table showing total templates, how many are configured as annotation
submissions, how many are configured as record submissions, and how many remain
unclassified (N/A).

By default the summary skips the demo configurations. Use `--include-demo`
if you want to keep them.
"""

import argparse
import csv
from pathlib import Path
from typing import Dict

DEFAULT_IGNORE = {"demo", "demo_upsert"}


def summarize_project(csv_path: Path) -> Dict[str, int]:
    """Return summary counts for a single project CSV."""
    total = annotation = record = na = 0
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total += 1
            role = (row.get("configured_template_role") or "").strip()
            if role == "Annotation":
                annotation += 1
            elif role == "Record":
                record += 1
            elif role == "N/A":
                na += 1
    return {
        "total": total,
        "annotation": annotation,
        "record": record,
        "na": na,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize template outputs by project")
    parser.add_argument(
        "--outputs",
        type=Path,
        default=Path("template_outputs"),
        help="Directory containing *_templates.csv files (default: template_outputs)",
    )
    parser.add_argument(
        "--include-demo",
        action="store_true",
        help="Include demo and demo_upsert projects in the summary",
    )
    args = parser.parse_args()

    ignore = set() if args.include_demo else set(DEFAULT_IGNORE)

    print("| Project | Total | Annotation | Record | N/A |")
    print("| --- | --- | --- | --- | --- |")

    grand_totals = {"total": 0, "annotation": 0, "record": 0, "na": 0}

    for csv_file in sorted(args.outputs.glob("*_templates.csv")):
        project = csv_file.stem.replace("_templates", "")
        if project in ignore:
            continue

        summary = summarize_project(csv_file)
        grand_totals["total"] += summary["total"]
        grand_totals["annotation"] += summary["annotation"]
        grand_totals["record"] += summary["record"]
        grand_totals["na"] += summary["na"]

        print(
            f"| {project} | {summary['total']} | {summary['annotation']} | "
            f"{summary['record']} | {summary['na']} |"
        )

    print(
        f"| Grand Total | {grand_totals['total']} | {grand_totals['annotation']} | "
        f"{grand_totals['record']} | {grand_totals['na']} |"
    )


if __name__ == "__main__":
    main()
