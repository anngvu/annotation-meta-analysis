import argparse
import csv
import json
from pathlib import Path

MODEL_NAME = "gpt-5-mini-2025-08-07"

SYSTEM_PROMPT = """You are a data privacy analyst tasked with classifying metadata attributes by sensitivity.
Classifications:
- High: Direct identifiers or information revealing personal identity, contact, precise location, financial, or highly sensitive clinical/behavioral data.
- Moderate: Quasi-identifiers (e.g., demographics, longitudinal visit markers, cohort identifiers), biospecimen or individual IDs that, while expected to be anonymized, could still aid re-identification, or sensitive contextual metadata.
- Low: Non-personal technical metadata (e.g., file properties, instrument settings) or general study logistics.
- NeedsReview: Insufficient information (descriptions like TBD/unknown) or unclear scope.
Enum values and validation rules may encode masking or constraint logic—review them carefully alongside descriptions before deciding. Choose exactly one class and provide a concise rationale referencing the attribute details."""

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "risk_assessment",
        "schema": {
            "type": "object",
            "properties": {
                "attribute_id": {"type": "string"},
                "project": {"type": "string"},
                "risk": {
                    "type": "string",
                    "enum": ["High", "Moderate", "Low", "NeedsReview"],
                },
                "rationale": {"type": "string"},
            },
            "required": ["attribute_id", "project", "risk", "rationale"],
            "additionalProperties": False,
        },
    },
}


def derive_project(attribute_id: str) -> str:
    if ":" in attribute_id:
        prefix = attribute_id.split(":", 1)[0]
        return prefix.upper()
    return "UNKNOWN"


def normalize_value(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return "(none)"
    if cleaned == "http://www.w3.org/1999/02/22-rdf-syntax-ns#nil":
        return "(none)"
    return cleaned


def build_user_content(row: dict) -> str:
    details = [
        "Classify the attribute described below.",
        "Return a JSON object with keys attribute_id, project, risk, rationale.",
        "Use one of High, Moderate, Low, NeedsReview for risk.",
        "Do not include any additional commentary.",
        "",
        f"attribute_id: {row['attribute_id']}",
        f"project: {row['project']}",
        f"label: {row['label']}",
        f"description: {row['description']}",
        f"validation_rules: {row['validation_rules']}",
        f"valid_values: {row['valid_values']}",
    ]
    return "\n".join(details)


def make_body(row: dict) -> dict:
    return {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_content(row)},
        ],
        "max_completion_tokens": 300,
        "response_format": RESPONSE_FORMAT,
    }


def build_record(row: dict) -> dict:
    attribute_id = row["attribute_id"].strip()
    custom_id = "risk_" + attribute_id.lower().replace(":", "_")
    project = derive_project(attribute_id)

    normalized = {
        "attribute_id": attribute_id,
        "project": project,
        "label": (row.get("label") or "").strip(),
        "description": (row.get("description") or "").strip() or "(none)",
        "validation_rules": normalize_value(row.get("validation_rules", "")),
        "valid_values": normalize_value(row.get("valid_values", "")),
    }

    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": make_body(normalized),
    }


def generate_dataset(csv_path: Path, output_path: Path) -> int:
    with csv_path.open(newline="", encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        reader = csv.DictReader(src)
        count = 0
        for row in reader:
            record = build_record(row)
            dst.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Create OpenAI batch JSONL for attribute risk review.")
    parser.add_argument(
        "--csv",
        default="notebook_data/annotation_template_attributes.csv",
        type=Path,
        help="Path to the source attribute CSV.",
    )
    parser.add_argument(
        "--out",
        default="notebook_data/annotation_template_attributes_batch.jsonl",
        type=Path,
        help="Destination JSONL file for batch submission.",
    )
    args = parser.parse_args()

    if not args.csv.is_file():
        raise FileNotFoundError(f"Source CSV not found: {args.csv}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    total = generate_dataset(args.csv, args.out)
    print(f"Wrote {total} records to {args.out}")
    print("Before submission, export your API key, e.g. 'export OPENAI_API_KEY=...'")


if __name__ == "__main__":
    main()
