# Data Curator App - Data Model Review Repository

This repository aggregates and transforms data models from across multiple Sage Bionetworks DCCs for systematic review and analysis.

### What This Repository Does

- **Aggregates**: Collects JSON-LD data models from 11 DCC projects
- **Transforms**: Converts models to RDF/Turtle for linkage and easier querying
- **Enriches**: Adds template type, species, and file type metadata
- **Analyzes**: Provides tools and notebooks, report exports for systematic review

### Use Cases

This repository supports:
- **Metadata Risk Assessment**: Identifying what annotations are exposed to third parties
- **Cross-Project Analysis**: Finding common patterns and inconsistencies
- **Data Dictionary Generation**: Documenting available attributes and validation rules
- **Schema Review**: Understanding template dependencies and relationships

## Repository Structure

```
.
├── data_models_jsonld/          # Latest mirror of JSON-LD data models (11 projects)
├── data_models_rdf/             # Converted Turtle format for SPARQL queries
├── template_enrichment_rdf/     # Template metadata (type, species, file types)
├── scripts/                     # ETL and utility scripts
├── notebook_data/               # Analysis outputs and exports
├── template_outputs/            # Template extraction CSVs
├── template_configs/            # Latest mirror of template configuration files
└── README*.md                   # Documentation files
```

## Quick Start

### 1. Convert Data Models to RDF

```bash
# Convert all projects
python3 convert_to_rdf.py

# Convert specific project
python3 convert_to_rdf.py --project ADKP
```

**Output**: `data_models_rdf/*.ttl` (283,000+ triples)

### 2. Extract and Enrich Template Metadata

```bash
# Extract template information
python3 extract_templates.py

# Generate enrichment RDF
python3 enrich_templates_to_rdf.py
```

**Output**:
- `template_outputs/*.csv` - Template analysis
- `template_enrichment_rdf/*.ttl` - Type/species/file type metadata

### 3. Export Annotation Attributes

```bash
# Export all annotation template attributes
python3 scripts/annotation_attributes_export.py

# Custom output location
python3 scripts/annotation_attributes_export.py -o my_output.csv
```

**Output**: `notebook_data/template_attributes.csv`

### 4. Interactive Analysis

```bash
# Install dependencies
pip install -r requirements_notebook.txt

# Launch notebook
jupyter notebook DCC_managed_data_review_strategy.ipynb
```

## Key Features

### RDF Knowledge Graph

The data models are converted to RDF/Turtle format enabling:

- **SPARQL Queries**: Query across all projects with standard semantic web tools
- **Cross-Project Analysis**: Find common attributes, templates, and patterns
- **Validation**: Check model consistency and relationships
- **Integration**: Link with external ontologies and vocabularies

See [README_rdf.md](README_rdf.md) for complete documentation.

### Template Metadata

Templates are enriched with:

- **Type Classification**: Annotation, Record, or Unconfigured
- **Species Information**: Human, Animal model, or Multi-species
- **File Types**: FASTQ, BAM, VCF, Mass spec data, etc.
- **Validation Rules**: Data type and format requirements

See [README_template_extraction.md](README_template_extraction.md) for details.

### Annotation Attributes Export

Export detailed attribute information from Annotation Templates:

- Prefixed URIs (e.g., `mc2:FileName`)
- Attribute labels and descriptions
- Validation rules
- Valid values (or "free text")

See [README_export_attributes.md](README_export_attributes.md) for usage.

### Metadata Sensitivity Analysis

Interactive Jupyter notebook for reviewing annotation metadata:

- Template distribution across projects
- Attribute-level analysis
- Example templates from each DCC
- Visualization of template strategies
- Export functionality

Key questions addressed:
- What metadata becomes annotations (visible to third parties)?
- Which DCCs use conservative vs. liberal annotation strategies?
- What attributes are commonly used across projects?

## Use Cases

### 1. Data Dictionary Creation

Export comprehensive attribute documentation:

```bash
python3 scripts/annotation_attributes_export.py -o data_dictionary.csv
```

### 2. Schema Analysis

Query template dependencies and validation rules:

```sparql
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
SELECT ?template ?attribute ?required
WHERE {
  ?template a dca:AnnotationTemplate ;
            dca:requiresDependency ?attribute .
  ?attribute dca:required ?required .
}
```

### 3. Metadata Risk Assessment

Identify what annotations are exposed:

```bash
jupyter notebook DCC_managed_data_review_strategy.ipynb
```

Review Annotation Templates to assess sensitivity of exposed metadata.

### 4. Cross-Project Comparison

Find common attributes across projects:

```sparql
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
SELECT ?attribute (COUNT(DISTINCT ?project) as ?projectCount)
WHERE {
  ?template a dca:AnnotationTemplate ;
            dca:requiresDependency ?attribute .
  BIND(REPLACE(STR(?template), "https://dca.app.sagebionetworks.org/([^/]+)/.*", "$1") AS ?project)
}
GROUP BY ?attribute
HAVING (COUNT(DISTINCT ?project) > 1)
ORDER BY DESC(?projectCount)
```

## Documentation

### Additional
- **[README_rdf.md](README_rdf.md)** - RDF conversion and enrichment guide
- **[README_template_extraction.md](README_template_extraction.md)** - Template analysis documentation
- **[README_export_attributes.md](README_export_attributes.md)** - Attribute export script usage
- **[README_test_export.md](README_test_export.md)** - Testing export functionality

### Notebooks
- **DCC_managed_data_review_strategy.ipynb** - Interactive metadata review analysis
- **DCC_managed_data_review_strategy.md** - Original strategy document (static)

## Requirements

### Core Dependencies
```bash
pip install rdflib pandas
```

### Notebook Dependencies
```bash
pip install -r requirements_notebook.txt
```

Includes: rdflib, pandas, matplotlib, seaborn, jupyter

## Data Model Vocabulary

### Namespaces
- **Project**: `https://dca.app.sagebionetworks.org/{PROJECT}/`
- **DCA Vocab**: `https://dca.app.sagebionetworks.org/vocab/`

### Classes
- `dca:Template` - Base template class
- `dca:RecordTemplate` - Recording entity templates
- `dca:AnnotationTemplate` - File/data annotation templates
- `dca:UnconfiguredTemplate` - Uncategorized templates
- `dca:DataProperty` - Attribute/property definitions

### Properties
- `dca:displayName` - Human-readable name
- `dca:required` - Required field (boolean)
- `dca:requiresDependency` - Template dependencies
- `dca:validationRules` - Validation rules (RDF list)
- `dca:species` - Species applicability
- `dca:fileType` - Expected file type

## Outputs

### CSV Exports (in `notebook_data/`)
- **template_attributes.csv** - All annotation attributes with metadata (1,322 rows)
- **annotation_templates_detail.csv** - List of annotation templates by project (171 rows)
- **template_distribution_summary.csv** - Template counts by type and project

### RDF Files
- **data_models_rdf/*.ttl** - 11 Turtle files with complete data models
- **template_enrichment_rdf/*.ttl** - 11 Turtle files with enrichment metadata

### Analysis Files
- **template_outputs/*.csv** - Template extraction results per project

## Statistics

- **490 total templates** across 11 projects
- **171 Annotation templates** producing visible annotations
- **104 Record templates** for internal data storage
- **215 Unconfigured templates** not in production
- **283,773 RDF triples** in combined knowledge graph
- **1,322 unique attributes** in Annotation templates

## References

- [Synapse Documentation - Annotating Data With Metadata](https://help.synapse.org/docs/Annotating-Data-With-Metadata.2667708522.html)
- [Data Curator App](https://dca.app.sagebionetworks.org/)

## License

See individual project documentation for licensing information.
