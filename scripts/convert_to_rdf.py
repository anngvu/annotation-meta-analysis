#!/usr/bin/env python3
"""
Convert JSON-LD data models to RDF/Turtle format.

This script transforms data model JSON-LD files into Turtle (.ttl) format with
project-specific namespaces for easier querying and linkage.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import quote as url_quote


def escape_turtle_string(s: str) -> str:
    """Escape special characters in Turtle string literals."""
    if s is None:
        return '""'
    s = str(s)
    # Escape backslashes first, then quotes, then newlines
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    s = s.replace('\n', '\\n')
    s = s.replace('\r', '\\r')
    s = s.replace('\t', '\\t')
    return f'"{s}"'


def needs_uri_escaping(local_name: str) -> bool:
    """Check if a local name needs to be escaped as a full URI."""
    # According to Turtle spec, only certain characters are allowed in prefixed names
    # If the local name doesn't match the pattern, it needs full URI escaping

    # Simple check: if it contains any special characters or starts/ends with problematic chars
    special_chars = ['/', '\\', '?', '#', '[', ']', '@', '!', '$', '&', "'", '(', ')', '*', '+', ',', ';', '=', ' ', '%', '.', '<', '>', '`', '{', '}', '|', '^', '"']

    if any(char in local_name for char in special_chars):
        return True

    # Also check if it starts with a digit or hyphen (not allowed in Turtle local names)
    if local_name and (local_name[0].isdigit() or local_name[0] == '-'):
        return True

    return False


def percent_encode_uri(uri: str) -> str:
    """Percent-encode special characters in a URI for use in Turtle."""
    # Characters that need encoding in URIs when used in Turtle angle brackets
    # We need to be careful to preserve the basic URI structure
    safe_chars = "-._~:/?#[]@!$&'()*+,;="  # Generally safe in URIs
    # But some break Turtle parsing, so encode them
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


def format_uri(uri: str, project: str, namespace_map: Dict[str, str]) -> str:
    """Convert a URI to its prefixed form or project-specific namespace."""
    # Check if it's in standard namespaces
    for prefix, ns_uri in namespace_map.items():
        if uri.startswith(ns_uri):
            local_name = uri.replace(ns_uri, '')
            # If local name has special chars, use full URI
            if needs_uri_escaping(local_name):
                return f"<{uri}>"
            return f"{prefix}:{local_name}"

    # Convert bts: to project namespace
    if uri.startswith('http://schema.biothings.io/'):
        local_name = uri.replace('http://schema.biothings.io/', '')
        # If local name has special chars, use full URI
        if needs_uri_escaping(local_name):
            full_uri = f"https://dca.app.sagebionetworks.org/{project}/{local_name}"
            return f"<{percent_encode_uri(full_uri)}>"
        return f"{project.lower()}:{local_name}"
    elif uri.startswith('bts:'):
        local_name = uri.replace('bts:', '')
        # If local name has special chars, use full URI
        if needs_uri_escaping(local_name):
            full_uri = f"https://dca.app.sagebionetworks.org/{project}/{local_name}"
            return f"<{percent_encode_uri(full_uri)}>"
        return f"{project.lower()}:{local_name}"

    # Return as full URI if not recognized
    return f"<{percent_encode_uri(uri)}>"


def format_validation_rules(rules: List[str]) -> str:
    """Format validation rules as an RDF list."""
    if not rules:
        return "( )"

    escaped_rules = [escape_turtle_string(rule) for rule in rules]
    return f"( {' '.join(escaped_rules)} )"


def format_dependencies(deps: List[Dict], project: str, namespace_map: Dict[str, str]) -> str:
    """Format requiresDependency as a comma-separated list."""
    dep_uris = [dep.get('@id', '') for dep in deps if dep.get('@id')]
    formatted = [format_uri(uri, project, namespace_map) for uri in dep_uris]
    return ', '.join(formatted)


def format_subclass(subclass: Any, project: str, namespace_map: Dict[str, str]) -> str:
    """Format rdfs:subClassOf which can be a dict or list."""
    if isinstance(subclass, dict):
        uri = subclass.get('@id', '')
        return format_uri(uri, project, namespace_map)
    elif isinstance(subclass, list):
        uris = [sc.get('@id', '') for sc in subclass if isinstance(sc, dict) and sc.get('@id')]
        formatted = [format_uri(uri, project, namespace_map) for uri in uris]
        return ', '.join(formatted)
    return ''


def format_types(types: Any) -> List[str]:
    """Format @type which can be a string or list."""
    if isinstance(types, str):
        return [types]
    elif isinstance(types, list):
        return types
    return []


def convert_item_to_turtle(item: Dict, project: str, namespace_map: Dict[str, str]) -> str:
    """Convert a single JSON-LD item to Turtle format."""
    item_id = item.get('@id', '')
    if not item_id:
        return ''

    subject = format_uri(item_id, project, namespace_map)

    # Start building the Turtle representation
    lines = []

    # Add types
    types = format_types(item.get('@type', []))
    type_parts = []
    for t in types:
        if t.startswith('rdfs:') or t.startswith('schema:'):
            type_parts.append(t)
        else:
            type_parts.append(format_uri(t, project, namespace_map))

    if type_parts:
        lines.append(f"{subject} a {', '.join(type_parts)} ;")
    else:
        lines.append(f"{subject}")

    # Add label
    label = item.get('rdfs:label')
    if label:
        lines.append(f"    rdfs:label {escape_turtle_string(label)} ;")

    # Add comment
    comment = item.get('rdfs:comment')
    if comment:
        lines.append(f"    rdfs:comment {escape_turtle_string(comment)} ;")

    # Add subClassOf
    subclass = item.get('rdfs:subClassOf')
    if subclass:
        formatted_subclass = format_subclass(subclass, project, namespace_map)
        if formatted_subclass:
            lines.append(f"    rdfs:subClassOf {formatted_subclass} ;")

    # Add DCA-specific properties
    display_name = item.get('sms:displayName')
    if display_name:
        lines.append(f"    dca:displayName {escape_turtle_string(display_name)} ;")

    required = item.get('sms:required')
    if required is not None:
        req_value = 'true' if required == 'sms:true' or required is True else 'false'
        lines.append(f"    dca:required {req_value} ;")

    # Add requiresDependency
    requires_dep = item.get('sms:requiresDependency')
    if requires_dep:
        formatted_deps = format_dependencies(requires_dep, project, namespace_map)
        if formatted_deps:
            lines.append(f"    dca:requiresDependency {formatted_deps} ;")

    # Add validationRules
    validation_rules = item.get('sms:validationRules')
    if validation_rules is not None:
        formatted_rules = format_validation_rules(validation_rules)
        lines.append(f"    dca:validationRules {formatted_rules} ;")

    # Remove trailing semicolon from last line and add period
    if lines:
        lines[-1] = lines[-1].rstrip(' ;') + ' .'

    return '\n'.join(lines)


def convert_jsonld_to_turtle(jsonld_path: Path, project: str, output_path: Path) -> None:
    """Convert a JSON-LD data model to Turtle format."""

    # Define namespace mappings
    namespace_map = {
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'schema': 'http://schema.org/',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
    }

    # Load JSON-LD
    with jsonld_path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    # Start building Turtle output
    turtle_lines = []

    # Add prefixes
    project_lower = project.lower()
    turtle_lines.append(f"@prefix {project_lower}: <https://dca.app.sagebionetworks.org/{project}/> .")
    turtle_lines.append(f"@prefix dca: <https://dca.app.sagebionetworks.org/vocab/> .")
    turtle_lines.append(f"@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    turtle_lines.append(f"@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    turtle_lines.append(f"@prefix schema: <http://schema.org/> .")
    turtle_lines.append(f"@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .")
    turtle_lines.append("")

    # Convert each item in @graph
    graph = data.get('@graph', [])

    for item in graph:
        turtle_item = convert_item_to_turtle(item, project, namespace_map)
        if turtle_item:
            turtle_lines.append(turtle_item)
            turtle_lines.append("")

    # Write to output file
    with output_path.open('w', encoding='utf-8') as f:
        f.write('\n'.join(turtle_lines))

    print(f"✅ Converted {project}: {len(graph)} items → {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert JSON-LD data models to RDF/Turtle format'
    )
    parser.add_argument(
        '--project',
        help='Specific project to convert (e.g., CB, ADKP). If not specified, converts all.'
    )
    parser.add_argument(
        '--input-dir',
        type=Path,
        default=Path('data_models'),
        help='Directory containing JSON-LD data models (default: data_models)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('data_models_rdf'),
        help='Directory for output Turtle files (default: data_models_rdf)'
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(exist_ok=True)

    # Find JSON-LD files
    if args.project:
        jsonld_files = list(args.input_dir.glob(f"{args.project}_data_model.jsonld"))
        if not jsonld_files:
            print(f"Error: No data model found for project '{args.project}'")
            return
    else:
        jsonld_files = list(args.input_dir.glob("*_data_model.jsonld"))

    if not jsonld_files:
        print(f"Error: No data models found in {args.input_dir}")
        return

    print(f"Converting {len(jsonld_files)} data model(s)...\n")

    # Convert each file
    for jsonld_path in sorted(jsonld_files):
        # Extract project name from filename
        project = jsonld_path.stem.replace('_data_model', '')

        # Create output path
        output_path = args.output_dir / f"{project}_data_model.ttl"

        try:
            convert_jsonld_to_turtle(jsonld_path, project, output_path)
        except Exception as e:
            print(f"❌ Error converting {project}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n✅ Conversion complete. Files saved to {args.output_dir}/")


if __name__ == '__main__':
    main()
