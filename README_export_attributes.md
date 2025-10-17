# Export Annotation Attributes Script

Script to export all attributes used in Annotation templates to CSV format.

## Script

**File**: `scripts/annotation_attributes_export.py`

## Features

- ✅ Queries RDF graph for template attributes
- ✅ Exports to CSV with prefixed URIs (e.g., `mc2:FileName` instead of full URL)
- ✅ Includes valid values list for each attribute
- ✅ Command-line interface with options
- ✅ Progress reporting for large datasets
- ✅ Data validation

## Output Columns

| Column | Description | Example |
|--------|-------------|---------|
| `attribute_id` | Prefixed URI of the attribute | `mc2:FileName` |
| `label` | Human-readable label | `FileName` |
| `description` | Attribute description/documentation | `Name of the file...` |
| `validation_rules` | RDF node containing validation rules | `n5e292e915...` |
| `valid_values` | Comma-separated list of valid values | `BAM, FASTQ, VCF` |

## Usage

### Basic Usage

```bash
python3 scripts/annotation_attributes_export.py
```

This will:
- Load all RDF data (283,773 triples)
- Query for attributes in Annotation templates (171 templates)
- Export to `template_attributes.csv`

### Custom Output File

```bash
python3 scripts/annotation_attributes_export.py -o my_attributes.csv
```

### Adjust Sample Display

```bash
python3 scripts/annotation_attributes_export.py --sample 20
```

Shows 20 sample results instead of the default 10.

### Command-Line Options

```
usage: annotation_attributes_export.py [-h] [-o OUTPUT] [--sample SAMPLE]

Export template attributes from RDF graph to CSV

options:
  -h, --help           show this help message and exit
  -o, --output OUTPUT  Output CSV file path (default: template_attributes.csv)
  --sample SAMPLE      Number of sample results to display (default: 10)
```

## Sample Output

### Console Output

```
========================================================================================================================
Export Template Attributes to CSV
========================================================================================================================

Query: Get all attributes used in Annotation templates
Output: attribute_id, label, description, validation_rules, valid_values

Loading data model TTL files...
  ✓ ADKP_data_model.ttl
  ✓ AMP-AIM_data_model.ttl
  ...

📊 Total graph: 283,773 triples loaded

🔍 Executing SPARQL query...
✅ Found 1322 unique attributes
📝 Extracting valid values for each attribute...

   Processing attribute 100/1322...
   Processing attribute 200/1322...
   ...

✅ Enrichment complete

📊 Sample Results (showing first 10 of 1322):
========================================================================================================================

1. Attribute: mc2:10xVisiumAuxiliaryFilesId
   Label: 10xVisiumAuxiliaryFilesId
   Description: Unique row identifier, used as a primary key for record updates
   Validation: n2ef41e76cb7644de93b86d3d93215ee0b299
   Valid Values: N/A

...

📈 Results Analysis:
--------------------------------------------------------------------------------
  Total attributes: 1322
  With validation rules: 1322 (100.0%)
  With valid values: 0 (0.0%)

📥 CSV exported to: template_attributes.csv

✅ Validating CSV export...
   Rows: 1322
   Columns: ['attribute_id', 'label', 'description', 'validation_rules', 'valid_values']

🎉 Export complete!
```

### CSV Output Sample

```csv
attribute_id,label,description,validation_rules,valid_values
mc2:10xVisiumAuxiliaryFilesId,10xVisiumAuxiliaryFilesId,"Unique row identifier, used as a primary key for record updates",n2ef41e76cb7644de93b86d3d93215ee0b299,
mc2:FileName,FileName,Name of the file,n5e292e9150da42a5a07b42e299eb87d0b156,
adkp:Species,Species,Species of the sample,n8a3f2b4c...,Human; Mouse; Rat
```

## Query Details

The script executes this SPARQL query:

```sparql
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?attribute ?label ?description ?validationRules
WHERE {
  # Find templates that are Annotation
  ?template a dca:AnnotationTemplate .

  # Get their dependencies (attributes)
  ?template dca:requiresDependency ?attribute .

  # Get attribute metadata
  ?attribute rdfs:label ?label .
  OPTIONAL { ?attribute rdfs:comment ?description }
  OPTIONAL {
    ?attribute dca:validationRules ?rulesList .
    BIND(STR(?rulesList) AS ?validationRules)
  }
}
ORDER BY ?label
```

For each attribute, it also queries for valid values:

```sparql
PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?value ?label
WHERE {
  <attribute_uri> schema:rangeIncludes ?value .
  OPTIONAL { ?value rdfs:label ?label }
}
```

## Results

From the current RDF graph:

- **Annotation templates**: 171
- **Total attributes**: 1,322
- **With validation rules**: 1,322 (100%)
- **With valid values**: 0 (0%)
- **CSV output size**: ~220 KB

## Use Cases

### 1. Data Dictionary Creation

Generate a complete attribute reference for documentation:

```bash
python3 scripts/annotation_attributes_export.py -o data_dictionary.csv
```

### 2. Schema Analysis

Analyze which attributes are used across templates:

```bash
python3 scripts/annotation_attributes_export.py
# Open template_attributes.csv in Excel/Google Sheets
```

### 3. Validation Review

Review validation rules for quality assurance:

```bash
python3 scripts/annotation_attributes_export.py
# Filter CSV by validation_rules column
```

### 4. Integration Documentation

Export for downstream system documentation:

```bash
python3 scripts/annotation_attributes_export.py -o api_fields.csv
```

## Notes

- **Prefixed URIs**: IDs use project prefixes (e.g., `mc2:`, `adkp:`) for readability
- **Valid Values**: Currently 0% of attributes have `schema:rangeIncludes` defined in the RDF
- **Validation Rules**: All attributes have validation rules (stored as RDF blank nodes)
- **Performance**: Processing 1,322 attributes takes ~20-30 seconds
- **Streamlined**: Only includes Annotation templates (excludes Unclassified and Record templates)
- **CSV Format**: Properly escaped for special characters and newlines

## Troubleshooting

### Script runs slowly

The script queries each attribute individually for valid values. For 2,174 attributes, this is normal.

### Empty valid_values column

This is expected if attributes don't use `schema:rangeIncludes` in the RDF graph. Valid values may be encoded differently (e.g., in validation rules).

### CSV encoding issues

The script uses UTF-8 encoding. Open in Excel using "Data > From Text/CSV" and select UTF-8.

## Files

- **Input**:
  - `data_models_rdf/*.ttl` (11 data models)
  - `template_enrichment_rdf/*.ttl` (11 enrichments)

- **Output**:
  - `template_attributes.csv` (default, configurable with `-o`)

## Integration

This same data can be queried in the chatbot (`rdf_chatbot.py`) by asking:

> "Show me all attributes used in Annotation templates with their labels and descriptions"

Then use the **📥 Download CSV** button to export.
