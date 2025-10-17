"""Submit an OpenAI Batch request for the annotation attribute risk review."""
import argparse
from pathlib import Path

from openai import OpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload JSONL and submit an OpenAI Batch job.")
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the JSONL file produced for batch submission.",
    )
    parser.add_argument(
        "--completion-window",
        dest="completion_window",
        default="24h",
        help="Batch completion window (e.g. 24h, 4h). Defaults to 24h.",
    )
    parser.add_argument(
        "--endpoint",
        default="/v1/chat/completions",
        help="Target endpoint for the batch (must match the request URLs in the JSONL).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input_file.is_file():
        raise FileNotFoundError(f"Input file not found: {args.input_file}")

    client = OpenAI()

    print(f"Uploading {args.input_file} ...")
    with args.input_file.open("rb") as fh:
        upload = client.files.create(file=fh, purpose="batch")
    print(f"Uploaded file id: {upload.id}")

    batch = client.batches.create(
        input_file_id=upload.id,
        endpoint=args.endpoint,
        completion_window=args.completion_window,
    )
    print("Batch submitted successfully")
    print(f"Batch id: {batch.id}")
    print(f"Status: {batch.status}")
    print("You can check progress with: python scripts/get_batch_status.py {batch_id}".format(batch_id=batch.id))


if __name__ == "__main__":
    main()
