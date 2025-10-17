#!/usr/bin/env python3
"""Parse attribute risk batch results and generate summary artifacts."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import matplotlib.pyplot as plt  # type: ignore
except ImportError as exc:  # pragma: no cover - import guard
    plt = None
    IMPORT_ERROR = exc  # capture for runtime messaging
else:
    IMPORT_ERROR = None


EXPECTED_RISKS = ["High", "Moderate", "Low", "NeedsReview"]


def _coalesce_text(message: Dict[str, Any]) -> Optional[str]:
    """Extract textual content from a chat-completions message payload."""
    content = message.get("content")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        fragments: List[str] = []
        for item in content:
            if isinstance(item, dict):
                if "text" in item and isinstance(item["text"], str):
                    fragments.append(item["text"])
                elif "content" in item and isinstance(item["content"], str):
                    fragments.append(item["content"])
        if fragments:
            return "".join(fragments).strip()

    return None


def _parse_choice(choice: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert a single choice payload into the expected risk dictionary."""
    parsed = choice.get("parsed")
    if isinstance(parsed, dict):
        return parsed

    message = choice.get("message", {})
    if not isinstance(message, dict):
        return None

    parsed_message = message.get("parsed")
    if isinstance(parsed_message, dict):
        return parsed_message

    text = _coalesce_text(message)
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _parse_record(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract the risk payload from a batch record."""
    response = record.get("response", {})
    if not isinstance(response, dict):
        return None

    body = response.get("body")
    choices = None
    if isinstance(body, dict):
        choices = body.get("choices")
        if not choices:
            output = body.get("output")
            if isinstance(output, dict):
                choices = output.get("choices")

    if not choices or not isinstance(choices, list):
        return None

    for choice in choices:
        if isinstance(choice, dict):
            parsed = _parse_choice(choice)
            if parsed:
                return parsed

    return None


def load_results(path: Path) -> List[Dict[str, Any]]:
    """Load and parse all result lines from a JSONL file."""
    results: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            payload = _parse_record(record)
            if payload:
                results.append(payload)
    return results


def render_chart(counter: Counter, output: Path) -> None:
    if plt is None:  # pragma: no cover - handled at runtime
        raise RuntimeError(
            "matplotlib is required to build charts (pip install matplotlib)."
        ) from IMPORT_ERROR

    categories = EXPECTED_RISKS
    counts = [counter.get(cat, 0) for cat in categories]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(categories, counts, color=["#d14", "#f7a21b", "#4c9f70", "#7e7e7e"])
    ax.set_ylabel("Attributes")
    ax.set_title("Attribute Risk Classification Counts")
    ax.set_ylim(0, max(counts + [1]) * 1.2)
    ax.bar_label(bars, labels=[str(c) for c in counts], padding=4)
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150)
    plt.close(fig)


def write_markdown_table(rows: List[Dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = ["| Attribute ID | Project | Rationale |", "| --- | --- | --- |"]
    for item in rows:
        attr = item.get("attribute_id", "")
        proj = item.get("project", "")
        rationale = (item.get("rationale", "") or "").replace("\n", "<br>")
        lines.append(f"| {attr} | {proj} | {rationale} |")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_results_csv(results: List[Dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["attribute_id", "project", "risk", "rationale"])
        for item in results:
            rationale = (item.get("rationale", "") or "").replace("\n", " ")
            writer.writerow([
                item.get("attribute_id", ""),
                item.get("project", ""),
                item.get("risk", ""),
                rationale,
            ])


def summarize(results: List[Dict[str, Any]]) -> Tuple[Counter, List[Dict[str, Any]], List[Dict[str, Any]]]:
    counter: Counter = Counter()
    high_risk: List[Dict[str, Any]] = []
    needs_review: List[Dict[str, Any]] = []

    for item in results:
        risk = item.get("risk")
        if isinstance(risk, str):
            counter[risk] += 1
            if risk == "High":
                high_risk.append(item)
            elif risk == "NeedsReview":
                needs_review.append(item)

    return counter, high_risk, needs_review


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze attribute risk batch results and generate summary artifacts."
    )
    parser.add_argument("results_file", type=Path, help="Path to the batch output JSONL file (from OpenAI Batch API).")
    parser.add_argument(
        "--chart",
        type=Path,
        default=Path("notebook_data/attribute_risk_distribution.png"),
        help="Destination path for the risk distribution bar chart.",
    )
    parser.add_argument(
        "--high-risk-table",
        type=Path,
        default=Path("notebook_data/high_risk_attributes.md"),
        help="Destination path for a Markdown table of High risk attributes.",
    )
    parser.add_argument(
        "--needs-review-table",
        type=Path,
        default=Path("notebook_data/needs_review_attributes.md"),
        help="Destination path for a Markdown table of Needs-review attributes.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("notebook_data/attribute_risk_results.csv"),
        help="Optional CSV export of all parsed results.",
    )
    args = parser.parse_args()

    if not args.results_file.is_file():
        raise FileNotFoundError(f"Results file not found: {args.results_file}")

    results = load_results(args.results_file)
    if not results:
        raise SystemExit("No valid results parsed from the provided JSONL file.")

    counter, high_risk, needs_review = summarize(results)

    write_results_csv(results, args.csv)
    write_markdown_table(high_risk, args.high_risk_table)
    write_markdown_table(needs_review, args.needs_review_table)
    render_chart(counter, args.chart)

    print("Parsed records:", len(results))
    for risk in EXPECTED_RISKS:
        print(f"  {risk:12s}: {counter.get(risk, 0)}")
    print(f"High risk entries exported to: {args.high_risk_table}")
    print(f"Needs-review entries exported to: {args.needs_review_table}")
    print(f"Chart saved to: {args.chart}")
    print(f"CSV summary written to: {args.csv}")


if __name__ == "__main__":
    main()
