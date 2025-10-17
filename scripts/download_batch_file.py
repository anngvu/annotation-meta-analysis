"""Download an OpenAI batch file (input/output/error) to disk."""
import argparse
from pathlib import Path
from openai import OpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download an OpenAI batch file by id.")
    parser.add_argument("file_id", help="The OpenAI file identifier (e.g. file-abc123).")
    parser.add_argument(
        "--out",
        type=Path,
        help="Destination path. Defaults to <file_id>.jsonl in the current directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = OpenAI()
    destination = args.out or Path(f"{args.file_id}.jsonl")
    print(f"Downloading {args.file_id} -> {destination}")
    response = client.files.content(args.file_id)
    destination.write_bytes(response.read())
    print("Download complete")


if __name__ == "__main__":
    main()
