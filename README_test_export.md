# Template Attributes Export Test

This document describes the test script for querying and exporting template attributes from the RDF graph.

## Test Objective

**Query**: Get the union of all attributes used in Annotation or Unconfigured templates

**Returns**:
- Attribute ID (URI)
- Attribute label
- Attribute description
- Validation rules (if any)

## Test Script

**File**: `scripts/annotation_attributes_export.py`

### What it does:

1. **Loads RDF Graph**
   - Loads all data model TTL files (11 projects)
   - Loads all enrichment TTL files (11 projects)
   - Total: 283,773 triples

2. **Executes SPARQL Query**
   ```sparql
   PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
   PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

   SELECT DISTINCT ?attribute ?label ?description ?validationRules
   WHERE {
     ?template a ?templateType .
     FILTER(?templateType IN (dca:AnnotationTemplate, dca:UnconfiguredTemplate))

     ?template dca:requiresDependency ?attribute .
     ?attribute rdfs:label ?label .

     OPTIONAL { ?attribute rdfs:comment ?description }
     OPTIONAL {
       ?attribute dca:validationRules ?rulesList .
       BIND(STR(?rulesList) AS ?validationRules)
     }
   }
   ORDER BY ?label
   ```

3. **Exports Results**
   - CSV format: `template_attributes.csv`
   - JSON format: `template_attributes.json`

4. **Validates Exports**
   - Checks file readability
   - Verifies row/object counts match
   - Validates data structure

## Test Results

### Query Results

- **Total attributes found**: 2,174
- **Attributes with validation rules**: 2,174 (100%)
- **Attributes without validation rules**: 0 (0%)

### Export Files

| Format | File | Size | Records |
|--------|------|------|---------|
| CSV | `template_attributes.csv` | 437 KB | 2,174 rows |
| JSON | `template_attributes.json` | 629 KB | 2,174 objects |

### Sample Data

**CSV Format:**
```csv
attribute,label,description,validationRules
https://dca.app.sagebionetworks.org/MC2/10xVisiumAuxiliaryFilesId,10xVisiumAuxiliaryFilesId,"Unique row identifier, used as a primary key for record updates",n5e292e9150da42a5a07b42e299eb87d0b299
https://dca.app.sagebionetworks.org/MC2/10xVisiumAuxiliaryFilesKey,10xVisiumAuxiliaryFilesKey,Unique 10xVisiumAuxiliaryFiles_id foreign key(s) that link metadata entries as part of the same Dataset.,n5e292e9150da42a5a07b42e299eb87d0b239
```

**JSON Format:**
```json
[
  {
    "attribute": "https://dca.app.sagebionetworks.org/MC2/10xVisiumAuxiliaryFilesId",
    "label": "10xVisiumAuxiliaryFilesId",
    "description": "Unique row identifier, used as a primary key for record updates",
    "validationRules": "n5e292e9150da42a5a07b42e299eb87d0b299"
  },
  {
    "attribute": "https://dca.app.sagebionetworks.org/MC2/10xVisiumAuxiliaryFilesKey",
    "label": "10xVisiumAuxiliaryFilesKey",
    "description": "Unique 10xVisiumAuxiliaryFiles_id foreign key(s) that link metadata entries as part of the same Dataset.",
    "validationRules": "n5e292e9150da42a5a07b42e299eb87d0b239"
  }
]
```

## Running the Test

### Prerequisites

```bash
# Ensure RDF graph files exist
ls data_models_rdf/*.ttl
ls template_enrichment_rdf/*.ttl
```

### Execute Test

```bash
python3 scripts/annotation_attributes_export.py
```

### Expected Output

```
========================================================================================================================
TEST: Query and Export Template Attributes
========================================================================================================================

Objective: Get all attributes used in Annotation or Unconfigured templates
Returns: attribute ID, label, description, and validation rules

Loading data model TTL files...
  ✓ ADKP_data_model.ttl
  ✓ AMP-AIM_data_model.ttl
  ...

📊 Total graph: 283,773 triples loaded

🔍 Executing SPARQL query...
✅ Found 2174 unique attributes

📥 CSV exported to: template_attributes.csv
📥 JSON exported to: template_attributes.json

✅ Data validation passed

🎉 All tests passed!
```

## Test Features

### 1. Graph Loading
- Loads all TTL files from both directories
- Reports loading progress
- Shows total triple count

### 2. Query Execution
- Uses SPARQL to find attributes
- Filters by template type (Annotation or Unconfigured)
- Retrieves all metadata fields

### 3. Result Display
- Shows sample results (first 10)
- Formats URIs for readability
- Truncates long text for display

### 4. Validation Analysis
- Counts attributes with/without validation rules
- Calculates percentages
- Shows sample validation rules

### 5. Export Functionality
- Exports to CSV with proper escaping
- Exports to JSON with proper structure
- Saves files to disk

### 6. Validation
- Reads exported files back
- Verifies row/object counts
- Checks data structure consistency

## Use Cases

This query and export is useful for:

1. **Data Dictionary Creation**
   - Generate complete attribute documentation
   - Include validation constraints
   - Export for team review

2. **Schema Analysis**
   - Understand what fields are used across templates
   - Identify common attributes
   - Review validation patterns

3. **Data Integration**
   - Export attribute metadata for ETL processes
   - Provide field definitions to downstream systems
   - Document API responses

4. **Quality Assurance**
   - Verify all attributes have descriptions
   - Check validation rule coverage
   - Audit metadata completeness

## Integration with Chatbot

This same query can be executed in the chatbot by asking:

> "Show me all attributes used in Annotation or Unconfigured templates with their descriptions and validation rules"

The chatbot will:
1. Convert the question to SPARQL
2. Execute the query
3. Display results
4. Provide download buttons for CSV and JSON export

## Files Generated

- `template_attributes.csv` - CSV export with 2,174 attributes
- `template_attributes.json` - JSON export with 2,174 attributes
- `scripts/annotation_attributes_export.py` - Test script (reusable)
- `README_test_export.md` - This documentation

## Notes

- The query finds attributes from both Annotation AND Unconfigured templates (union)
- All 2,174 attributes have validation rules (100% coverage)
- Validation rules are stored as RDF blank nodes, shown as node IDs in results
- Full URIs are preserved in exports for machine readability
- Shortened URIs are shown in console output for human readability
