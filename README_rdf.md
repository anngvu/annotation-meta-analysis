# RDF/Turtle Data Models

This directory contains tools and documentation for converting JSON-LD data models to RDF/Turtle format and enriching them with template metadata.

## Overview

The RDF graph is built from two sources:

1. **Base Data Models** (`data_models_rdf/`) - Structure and properties converted from JSON-LD
2. **Template Enrichment** (`template_enrichment_rdf/`) - Template types, species, and file types from CSV analysis

Combined, these create a queryable knowledge graph with **283,773 total triples** across 11 projects.

## Namespace Structure

- **Project namespace**: `https://dca.app.sagebionetworks.org/{PROJECT}/`
- **DCA vocabulary**: `https://dca.app.sagebionetworks.org/vocab/`

### Example
- `cb:BiologicalEntity` - Class in CB project namespace
- `dca:displayName` - Property in DCA vocabulary
- `dca:RecordTemplate` - Template type class

---

## Part 1: RDF Conversion from JSON-LD

### Usage

#### Convert all data models
```bash
python3 convert_to_rdf.py
```

#### Convert a specific project
```bash
python3 convert_to_rdf.py --project CB
```

#### Specify custom directories
```bash
python3 convert_to_rdf.py \
  --input-dir /path/to/jsonld \
  --output-dir /path/to/output
```

### Namespace Mapping

The conversion maps JSON-LD vocabularies to the DCA namespace:

- `bts:BiologicalEntity` → `cb:BiologicalEntity` (project-specific)
- `sms:displayName` → `dca:displayName`
- `sms:required` → `dca:required`
- `sms:requiresDependency` → `dca:requiresDependency`
- `sms:validationRules` → `dca:validationRules`

### Example Output

```turtle
@prefix cb: <https://dca.app.sagebionetworks.org/CB/> .
@prefix dca: <https://dca.app.sagebionetworks.org/vocab/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

cb:FiletoIndividualMap a rdfs:Class, dca:Template ;
    rdfs:label "FiletoIndividualMap" ;
    rdfs:comment "Template that maps each individual to a file in synapse" ;
    rdfs:subClassOf cb:Template ;
    dca:displayName "File to Individual Map" ;
    dca:required false ;
    dca:requiresDependency cb:FileName, cb:IndividualId, cb:Component ;
    dca:validationRules ( ) .

cb:FileName a rdfs:Class, dca:DataProperty ;
    rdfs:label "FileName" ;
    rdfs:comment "Name of the file" ;
    rdfs:subClassOf cb:DataProperty ;
    dca:displayName "fileName" ;
    dca:required true ;
    dca:validationRules ( "str" ) .
```

### Validation Rules Format

Validation rules are preserved as RDF lists:

- Simple: `( "str" )`, `( "int" )`, `( "num" )`
- URLs: `( "url" )`, `( "url warning" )`
- Lists: `( "list" )`, `( "list like" )`
- Regex: `( "regex match <pattern>" )`, `( "regex search <pattern>" )`
- Multiple: `( "list" "regex match syn\\d+" )`

### Output Location

Turtle files are saved to `data_models_rdf/` directory:

- `ADKP_data_model.ttl`
- `CB_data_model.ttl`
- `EL_data_model.ttl`
- etc.

---

## Part 2: Template Enrichment

### Enrichment Data

Template metadata is enriched with additional classification:

#### Template Types
- `dca:RecordTemplate` - Templates for recording entities (e.g., Biospecimen, Individual)
- `dca:AnnotationTemplate` - Templates for annotating files/data (e.g., assays, file metadata)
- `dca:UnconfiguredTemplate` - Templates that haven't been categorized

#### Species Information
- `dca:species` - Species the template is designed for
  - `"Human"` - Human-specific templates
  - `"Animal model"` - Non-human organism templates
  - `"Multi-species"` - Templates that work across species

#### File Types
- `dca:fileType` - Expected file type for annotation templates
  - Examples: `"FASTQ"`, `"BAM"`, `"VCF"`, `"Mass spec data"`, `"Various"`

### Example Enrichment

```turtle
@prefix el: <https://dca.app.sagebionetworks.org/EL/> .
@prefix dca: <https://dca.app.sagebionetworks.org/vocab/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

# Record template with species
el:IndividualHumanTemplate a dca:RecordTemplate .
el:IndividualHumanTemplate dca:species "Human" .

# Annotation template with species and file type
el:AssayRNAseqTemplate a dca:AnnotationTemplate .
el:AssayRNAseqTemplate dca:fileType "FASTQ" .
```

### Generating Enrichment

#### 1. Extract Templates
```bash
python3 extract_templates.py
```

This analyzes data models and creates CSV files in `template_outputs/` with:
- Template identification
- Role classification (Record/Annotation)
- Species inference
- File type detection

#### 2. Convert to RDF
```bash
python3 enrich_templates_to_rdf.py
```

This reads the CSV files and generates Turtle files in `template_enrichment_rdf/` with type assertions and metadata.

### Statistics

From the current enrichment (11 projects):

- **104 Record templates** - For recording clinical/experimental data
- **171 Annotation templates** - For annotating files and datasets
- **215 Unconfigured templates** - Templates needing categorization
- **773 total enrichment triples**

---

## SPARQL Queries

### Basic Template Queries

#### Get template description and dependencies
```sparql
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?template ?description ?dependency
WHERE {
  ?template a dca:Template ;
            rdfs:comment ?description ;
            dca:requiresDependency ?dependency .
}
```

#### Find all required properties
```sparql
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>

SELECT ?property ?displayName
WHERE {
  ?property a dca:DataProperty ;
            dca:displayName ?displayName ;
            dca:required true .
}
```

### Enrichment Queries

#### Find all Record templates
```sparql
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?template ?label
WHERE {
  ?template a dca:RecordTemplate ;
            rdfs:label ?label .
}
```

#### Find Human Annotation templates
```sparql
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?template ?label ?fileType
WHERE {
  ?template a dca:AnnotationTemplate ;
            rdfs:label ?label ;
            dca:species "Human" .
  OPTIONAL { ?template dca:fileType ?fileType }
}
```

#### Count templates by type
```sparql
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>

SELECT ?type (COUNT(?template) as ?count)
WHERE {
  ?template a ?type .
  FILTER(?type IN (dca:RecordTemplate, dca:AnnotationTemplate, dca:UnconfiguredTemplate))
}
GROUP BY ?type
```

### Cross-Project Queries

```sparql
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?project ?template ?label
WHERE {
  ?template a dca:Template ;
            rdfs:label ?label .
  FILTER(STRSTARTS(STR(?template), "https://dca.app.sagebionetworks.org/"))
  BIND(REPLACE(STR(?template), "https://dca.app.sagebionetworks.org/([^/]+)/.*", "$1") AS ?project)
}
```

---

## Using with RDF Tools

### Python (rdflib)

```python
from rdflib import Graph

# Load both data models and enrichment
g = Graph()
g.parse("data_models_rdf/CB_data_model.ttl", format="turtle")
g.parse("template_enrichment_rdf/CB_enrichment.ttl", format="turtle")

# Query templates
query = """
PREFIX dca: <https://dca.app.sagebionetworks.org/vocab/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?template ?label ?type WHERE {
  ?template a ?type ;
            rdfs:label ?label .
  FILTER(?type IN (dca:RecordTemplate, dca:AnnotationTemplate))
}
"""

for row in g.query(query):
    print(f"{row.template}: {row.label} ({row.type})")
```

### RDF Triple Stores

Load the Turtle files into an RDF triple store:

- **Apache Jena Fuseki** - for SPARQL queries
- **GraphDB** - for semantic reasoning
- **Blazegraph** - for federated queries

### Interactive Chatbot

The chatbot (`rdf_chatbot.py`) automatically loads both data model and enrichment files:

1. **Load Graph** button loads from both directories
2. Ask natural language questions:
   - "Show me all Record templates"
   - "What Annotation templates are for Human samples?"
   - "How many templates of each type are there?"

The LLM converts these to SPARQL queries using the complete vocabulary.

---

## Complete Vocabulary

All data uses the DCA vocabulary namespace:
- Namespace: `https://dca.app.sagebionetworks.org/vocab/`
- Prefix: `dca:`

### Classes
- `dca:Template` - Base template class
- `dca:RecordTemplate` - Template for recording entities
- `dca:AnnotationTemplate` - Template for annotating files
- `dca:UnconfiguredTemplate` - Template not yet categorized
- `dca:DataProperty` - Data property/attribute

### Properties (from base models)
- `dca:displayName` - Human-readable display name
- `dca:required` - Whether property is required (boolean)
- `dca:requiresDependency` - Template dependencies
- `dca:validationRules` - Property validation rules (RDF list)

### Properties (from enrichment)
- `dca:species` - Species applicability (string literal)
- `dca:fileType` - Expected file type (string literal)

---

## Files and Scripts

### Input Files
- `data_models_jsonld/*.jsonld` - Original JSON-LD data models
- `template_outputs/*.csv` - Template analysis results

### Output Files
- `data_models_rdf/*.ttl` - Base data models in Turtle format
- `template_enrichment_rdf/*.ttl` - Enrichment metadata in Turtle format

### Scripts
- `convert_to_rdf.py` - Convert JSON-LD to Turtle
- `extract_templates.py` - Analyze data models, generate CSVs
- `enrich_templates_to_rdf.py` - Convert CSVs to Turtle enrichment
- `rdf_chatbot.py` - Interactive SPARQL chatbot

### Validation
All RDF files are validated using rdflib to ensure syntactic correctness before loading.
