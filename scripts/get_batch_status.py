"""Retrieve OpenAI batch status details for a given batch id."""
import argparse
import json
from openai import OpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retrieve status for an OpenAI batch job.")
    parser.add_argument("batch_id", help="The OpenAI batch identifier (e.g. batch_abc123).")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the raw JSON response instead of a short summary.",
    )
    return parser.parse_args()


def format_error(err) -> str:
    if hasattr(err, "model_dump"):
        payload = err.model_dump()
    elif isinstance(err, dict):
        payload = err
    else:
        return repr(err)

    err_type = payload.get("type") or payload.get("code") or "unknown"
    message = payload.get("message") or payload.get("detail") or payload
    if isinstance(message, (dict, list)):
        message = json.dumps(message)
    return f"type={err_type} message={message}"


def main() -> None:
    args = parse_args()
    client = OpenAI()
    batch = client.batches.retrieve(args.batch_id)

    if args.json:
        print(json.dumps(batch.model_dump(), indent=2))
        return

    print(f"Batch id   : {batch.id}")
    print(f"Status     : {batch.status}")
    print(f"Created at : {batch.created_at}")
    print(f"Completion window: {batch.completion_window}")
    if getattr(batch, "request_counts", None):
        rc = batch.request_counts
        print(
            "Requests   : total={total} completed={completed} failed={failed}".format(
                total=getattr(rc, "total", 0),
                completed=getattr(rc, "completed", 0),
                failed=getattr(rc, "failed", 0),
            )
        )
    if getattr(batch, "input_file_id", None):
        print(f"Input file id : {batch.input_file_id}")
    if getattr(batch, "output_file_id", None):
        print(f"Output file id: {batch.output_file_id}")
    if getattr(batch, "error_file_id", None):
        print(f"Error file id : {batch.error_file_id}")
    if getattr(batch, "errors", None) and getattr(batch.errors, "data", None):
        print("Errors     :")
        for err in batch.errors.data:
            print(f"  - {format_error(err)}")


if __name__ == "__main__":
    main()
