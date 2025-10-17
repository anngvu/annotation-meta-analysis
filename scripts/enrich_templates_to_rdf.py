#!/usr/bin/env python3
"""
Convert template analysis CSV files to RDF/Turtle format.

This script enriches the RDF data with template type information (Record/Annotation),
species information, and file types extracted from the template analysis.
"""

import csv
import argparse
from pathlib import Path
from typing import Dict, List


def escape_turtle_string(s: str) -> str:
    """Escape special characters in Turtle string literals."""
    if s is None or s == '':
        return '""'
    s = str(s)
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    s = s.replace('\n', '\\n')
    s = s.replace('\r', '\\r')
    s = s.replace('\t', '\\t')
    return f'"{s}"'


def needs_uri_escaping(local_name: str) -> bool:
    """Check if a local name needs to be escaped as a full URI."""
    special_chars = ['/', '\\', '?', '#', '[', ']', '@', '!', '$', '&', "'", '(', ')', '*', '+', ',', ';', '=', ' ', '%', '.', '<', '>', '`', '{', '}', '|', '^', '"']

    if any(char in local_name for char in special_chars):
        return True

    if local_name and (local_name[0].isdigit() or local_name[0] == '-'):
        return True

    return False


def percent_encode_uri(uri: str) -> str:
    """Percent-encode special characters in a URI for use in Turtle."""
    result = uri
    result = result.replace('>', '%3E')
    result = result.replace('<', '%3C')
    result = result.replace('`', '%60')
    result = result.replace('{', '%7B')
    result = result.replace('}', '%7D')
    result = result.replace('|', '%7C')
    result = result.replace('^', '%5E')
    result = result.replace('\\', '%5C')
    result = result.replace('"', '%22')
    return result


def convert_csv_to_turtle(csv_path: Path, project: str, output_path: Path) -> None:
    """Convert a template CSV to Turtle format with enrichment metadata."""

    # Read CSV
    templates = []
    with csv_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            templates.append(row)

    if not templates:
        print(f"⚠️  {project}: No templates found")
        return

    # Start building Turtle
    lines = []

    # Add prefixes
    project_lower = project.lower()
    lines.append(f"@prefix {project_lower}: <https://dca.app.sagebionetworks.org/{project}/> .")
    lines.append(f"@prefix dca: <https://dca.app.sagebionetworks.org/vocab/> .")
    lines.append(f"@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    lines.append("")

    # Convert each template
    for template in templates:
        template_id = template['template_id']
        template_role = template.get('configured_template_role', 'N/A')
        species = template.get('species', 'Not specified')
        file_type = template.get('file_type', 'N/A')

        # Build template URI (match the format from data models)
        if needs_uri_escaping(template_id):
            full_uri = f"https://dca.app.sagebionetworks.org/{project}/{template_id}"
            template_uri = f"<{percent_encode_uri(full_uri)}>"
        else:
            template_uri = f"{project_lower}:{template_id}"

        # Add template type assertion
        if template_role == 'Record':
            lines.append(f"{template_uri} a dca:RecordTemplate .")
        elif template_role == 'Annotation':
            lines.append(f"{template_uri} a dca:AnnotationTemplate .")
        elif template_role == 'N/A':
            lines.append(f"{template_uri} a dca:UnconfiguredTemplate .")

        # Add species information
        if species and species != 'Not specified':
            lines.append(f"{template_uri} dca:species {escape_turtle_string(species)} .")

        # Add file type for annotation templates
        if file_type and file_type != 'N/A':
            lines.append(f"{template_uri} dca:fileType {escape_turtle_string(file_type)} .")

        lines.append("")

    # Write to file
    with output_path.open('w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    record_count = sum(1 for t in templates if t.get('configured_template_role') == 'Record')
    annotation_count = sum(1 for t in templates if t.get('configured_template_role') == 'Annotation')
    unconfigured_count = sum(1 for t in templates if t.get('configured_template_role') == 'N/A')

    print(f"✅ {project}: {len(templates)} templates ({record_count} Record, {annotation_count} Annotation, {unconfigured_count} Unconfigured) → {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert template analysis CSVs to enrichment RDF/Turtle'
    )
    parser.add_argument(
        '--project',
        help='Specific project to convert (e.g., CB, ADKP). If not specified, converts all.'
    )
    parser.add_argument(
        '--input-dir',
        type=Path,
        default=Path('template_outputs'),
        help='Directory containing template CSV files (default: template_outputs)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('template_enrichment_rdf'),
        help='Directory for output Turtle files (default: template_enrichment_rdf)'
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(exist_ok=True)

    # Find CSV files
    if args.project:
        csv_files = list(args.input_dir.glob(f"{args.project}_templates.csv"))
        if not csv_files:
            print(f"Error: No template CSV found for project '{args.project}'")
            return
    else:
        csv_files = list(args.input_dir.glob("*_templates.csv"))

    if not csv_files:
        print(f"Error: No template CSVs found in {args.input_dir}")
        return

    print(f"Converting {len(csv_files)} template CSV(s)...\n")

    # Convert each file
    for csv_path in sorted(csv_files):
        # Extract project name from filename
        project = csv_path.stem.replace('_templates', '')

        # Skip demo projects
        if project in {'demo', 'demo_upsert'}:
            continue

        # Create output path
        output_path = args.output_dir / f"{project}_enrichment.ttl"

        try:
            convert_csv_to_turtle(csv_path, project, output_path)
        except Exception as e:
            print(f"❌ Error converting {project}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n✅ Conversion complete. Files saved to {args.output_dir}/")


if __name__ == '__main__':
    main()
