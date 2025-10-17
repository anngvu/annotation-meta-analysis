#!/usr/bin/env python3
"""
Export template attributes to CSV.

This script queries for all attributes used in Annotation templates
and exports them to a CSV file with prefixed URIs and valid values.
"""

from rdflib import Graph
from pathlib import Path
import csv
import argparse


def load_graph():
    """Load both data model and enrichment RDF graphs."""
    g = Graph()

    # Load data models
    print("Loading data model TTL files...")
    for f in sorted(Path('data_models_rdf').glob('*.ttl')):
        g.parse(f, format='turtle')
        print(f"  ✓ {f.name}")

    # Load enrichment
    print("\nLoading enrichment TTL files...")
    for f in sorted(Path('template_enrichment_rdf').glob('*.ttl')):
        g.parse(f, format='turtle')
        print(f"  ✓ {f.name}")

    print(f"\n📊 Total graph: {len(g):,} triples loaded\n")
    return g


def shorten_uri(uri: str) -> str:
    """Convert full URI to prefixed format."""
    uri_str = str(uri)

    # Map base URIs to prefixes
    base_uri = "https://dca.app.sagebionetworks.org/"

    if uri_str.startswith(base_uri):
        # Extract project and local name
        remainder = uri_str[len(base_uri):]
        parts = remainder.split('/', 1)
        if len(parts) == 2:
            project = parts[0].lower()
            local_name = parts[1]
            return f"{project}:{local_name}"
        else:
            # Just project level
            return remainder

    # Handle other common prefixes
    if uri_str.startswith("http://www.w3.org/2000/01/rdf-schema#"):
        return uri_str.replace("http://www.w3.org/2000/01/rdf-schema#", "rdfs:")
    if uri_str.startswith("http://schema.org/"):
        return uri_str.replace("http://schema.org/", "schema:")

    return uri_str


def extract_valid_values(graph, attribute_uri):
    """Extract valid values/range values for an attribute."""
    # Query for range values (schema:rangeIncludes)
    query = f"""
PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?value ?label
WHERE {{
  <{attribute_uri}> schema:rangeIncludes ?value .
  OPTIONAL {{ ?value rdfs:label ?label }}
}}
"""

    results = graph.query(query)
    valid_values = []

    for row in results:
        if row.label:
            valid_values.append(str(row.label))
        else:
            # Use the URI if no label
            valid_values.append(shorten_uri(row.value))

    return ", ".join(valid_values) if valid_values else ""


def query_template_attributes(graph):
    """
    Get all attributes used in Annotation templates.
    Returns id, label, description, validation rules, and valid values.
    """
    query = """
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?attribute ?label ?description ?validationRules
WHERE {
  # Find templates that are Annotation
  ?template a dca:AnnotationTemplate .

  # Get their dependencies (attributes)
  ?template dca:requiresDependency ?attribute .

  # Get attribute label
  ?attribute rdfs:label ?label .

  # Optional: Get description
  OPTIONAL { ?attribute rdfs:comment ?description }

  # Optional: Get validation rules (as a formatted string)
  OPTIONAL {
    ?attribute dca:validationRules ?rulesList .
    BIND(STR(?rulesList) AS ?validationRules)
  }
}
ORDER BY ?label
"""

    print("🔍 Executing SPARQL query...")
    print("Query: Get all attributes used in Annotation templates\n")

    results = list(graph.query(query))

    print(f"✅ Found {len(results)} unique attributes")
    print("📝 Extracting valid values for each attribute...\n")

    # Enrich results with valid values
    enriched_results = []
    for i, row in enumerate(results, 1):
        if i % 100 == 0:
            print(f"   Processing attribute {i}/{len(results)}...")

        valid_values = extract_valid_values(graph, row.attribute)
        enriched_results.append({
            'attribute': row.attribute,
            'label': row.label,
            'description': row.description,
            'validationRules': row.validationRules,
            'validValues': valid_values
        })

    print(f"✅ Enrichment complete\n")
    return enriched_results


def export_to_csv(results, output_path='template_attributes.csv'):
    """Export results to CSV format with prefixed URIs."""
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow(['attribute_id', 'label', 'description', 'validation_rules', 'valid_values'])

        # Write rows
        for row in results:
            # Use prefixed URI for attribute ID
            attr_id = shorten_uri(row['attribute'])
            label = str(row['label']) if row['label'] else ""
            description = str(row['description']) if row['description'] else ""
            validation_rules = str(row['validationRules']) if row['validationRules'] else ""
            valid_values = row['validValues'] if row['validValues'] else "free text"

            writer.writerow([attr_id, label, description, validation_rules, valid_values])

    print(f"📥 CSV exported to: {output_path}")
    return output_path


def display_sample_results(result_list, limit=10):
    """Display a sample of the results."""
    print(f"\n📊 Sample Results (showing first {min(limit, len(result_list))} of {len(result_list)}):")
    print("=" * 120)

    for i, row in enumerate(result_list[:limit], 1):
        # Use prefixed URI
        attr_id = shorten_uri(row['attribute'])
        label = str(row['label'])
        desc = str(row['description']) if row['description'] else "N/A"
        rules = str(row['validationRules']) if row['validationRules'] else "N/A"
        valid_vals = row['validValues'] if row['validValues'] else "free text"

        # Truncate long text
        if len(desc) > 60:
            desc = desc[:57] + "..."
        if len(rules) > 60:
            rules = rules[:57] + "..."
        if len(valid_vals) > 60:
            valid_vals = valid_vals[:57] + "..."

        print(f"\n{i}. Attribute: {attr_id}")
        print(f"   Label: {label}")
        print(f"   Description: {desc}")
        print(f"   Validation: {rules}")
        print(f"   Valid Values: {valid_vals}")

    if len(result_list) > limit:
        print(f"\n... and {len(result_list) - limit} more attributes")

    print("\n" + "=" * 120)


def validate_csv(csv_path='template_attributes.csv'):
    """Validate that the CSV file is readable and contains data."""
    print("\n✅ Validating CSV export...")

    with open(csv_path, 'r', encoding='utf-8') as f:
        csv_reader = csv.DictReader(f)
        csv_rows = list(csv_reader)

        if csv_rows:
            print(f"   Rows: {len(csv_rows)}")
            print(f"   Columns: {list(csv_rows[0].keys())}")

            # Count rows with valid values
            with_valid_values = sum(1 for row in csv_rows if row.get('valid_values'))
            print(f"   Attributes with valid values: {with_valid_values} ({100*with_valid_values/len(csv_rows):.1f}%)")

    return csv_rows


def analyze_results(result_list):
    """Analyze results statistics."""
    print("\n📈 Results Analysis:")
    print("-" * 80)

    total = len(result_list)
    with_rules = sum(1 for row in result_list if row['validationRules'])
    with_values = sum(1 for row in result_list if row['validValues'])

    print(f"  Total attributes: {total}")
    print(f"  With validation rules: {with_rules} ({100*with_rules/total:.1f}%)")
    print(f"  With valid values: {with_values} ({100*with_values/total:.1f}%)")

    # Sample valid values
    if with_values > 0:
        print("\n  Sample attributes with valid values:")
        count = 0
        for row in result_list:
            if row['validValues'] and count < 5:
                label = str(row['label'])
                values = row['validValues']
                if len(values) > 80:
                    values = values[:77] + "..."
                print(f"    • {label}: {values}")
                count += 1


def main():
    """Main script - export template attributes to CSV."""
    parser = argparse.ArgumentParser(
        description='Export template attributes from RDF graph to CSV'
    )
    parser.add_argument(
        '-o', '--output',
        default='notebook_data/template_attributes.csv',
        help='Output CSV file path (default: notebook_data/template_attributes.csv)'
    )
    parser.add_argument(
        '--sample',
        type=int,
        default=10,
        help='Number of sample results to display (default: 10)'
    )

    args = parser.parse_args()

    print("=" * 120)
    print("Export Template Attributes to CSV")
    print("=" * 120)
    print("\nQuery: Get all attributes used in Annotation templates")
    print("Output: attribute_id, label, description, validation_rules, valid_values\n")

    # Create output directory if it doesn't exist
    import os
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Load graph
    graph = load_graph()

    # Execute query and enrich with valid values
    results = query_template_attributes(graph)

    # Display sample results
    display_sample_results(results, limit=args.sample)

    # Analyze results
    analyze_results(results)

    # Export to CSV
    print("\n" + "-" * 80)
    csv_path = export_to_csv(results, args.output)

    # Validate CSV
    csv_rows = validate_csv(csv_path)

    # Summary
    print("\n" + "=" * 120)
    print("📋 SUMMARY")
    print("=" * 120)
    print(f"✅ Query executed successfully")
    print(f"✅ Found {len(results)} unique attributes")
    print(f"✅ CSV exported: {csv_path} ({len(csv_rows)} rows)")
    print(f"✅ Data validation passed")
    print("\n🎉 Export complete!\n")


if __name__ == '__main__':
    main()
