#!/usr/bin/env python3
"""
Fetch all data models from the master URLs file and save them locally.

This creates a local cache of data models in the data_models/ directory,
similar to how template_configs/ caches template configuration files.
"""

import json
import sys
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

def fetch_json(url: str) -> dict:
    """Fetch JSON data from a URL."""
    with urlopen(url) as response:
        return json.loads(response.read().decode('utf-8'))

def main():
    master_file = Path('data_model_urls.csv')
    output_dir = Path('data_models')
    output_dir.mkdir(exist_ok=True)

    if not master_file.exists():
        print(f"Error: {master_file} not found. Run extract_templates.py first to generate it.")
        sys.exit(1)

    # Read the master file
    import csv
    with master_file.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        projects = list(reader)

    print(f"Fetching data models for {len(projects)} projects...")
    print()

    success_count = 0
    fail_count = 0

    for project in projects:
        project_name = project['Project']
        model_url = project['Data Model URL']

        if not model_url:
            print(f"⚠️  {project_name}: No data model URL")
            fail_count += 1
            continue

        output_file = output_dir / f"{project_name}_data_model.jsonld"

        try:
            print(f"📥 Fetching {project_name}...")
            data = fetch_json(model_url)

            # Save to file
            with output_file.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            print(f"✅ {project_name}: Saved to {output_file}")
            success_count += 1

        except (HTTPError, URLError) as e:
            print(f"❌ {project_name}: Failed to fetch - {e}")
            fail_count += 1
        except Exception as e:
            print(f"❌ {project_name}: Error - {e}")
            fail_count += 1

    print()
    print(f"Summary: {success_count} succeeded, {fail_count} failed")
    print(f"Data models saved to {output_dir}/")

if __name__ == '__main__':
    main()
