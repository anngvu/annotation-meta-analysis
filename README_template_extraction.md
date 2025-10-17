# Template Extraction Script

This script extracts template information from JSON-LD data models used in the Data Curator App (DCA) configuration.

## Overview

The script analyzes data models to identify templates (classes with dependent properties) and extracts:
- **Template ID**: The schema/class name
- **Species**: Inferred from template properties (Human, Mouse, Multi-species, etc.)
- **File Type**: For annotation templates, the specific file format (FASTQ, BAM, VCF, etc.)
- **Configured Template Role**: When a template config exists, confirms whether the template is deployed for record or annotation submission

## Structure Understanding

### What are Templates?

In the data model:
- **Templates** are defined as `rdfs:Class` entries that have `sms:requiresDependency` properties
- These dependencies list the required fields/properties for that template
- Templates represent complete data submission forms (e.g., "WGSTemplate" for whole genome sequencing data)

### Template Configuration

Some projects have a `dca-template-config.json` file that provides additional metadata:
- Display names for templates
- Template type (file-based or record-based)
- Record-based templates are typically clinical/biospecimen data
- File-based templates are typically assay metadata and are surfaced in the output as **annotation** templates. The README refers to these as *annotation* templates to make it explicit that they carry file-level metadata rather than tabular record schemas.
- If a matching config is downloaded into `template_configs/<project>_template_config.json`, the script reads it locally before attempting to fetch the remote URL, ensuring the `configured_template_role` column reflects the `submitted_as`/`type` value tracked in production.

## Usage

### Process a single project

```bash
python3 extract_templates.py --project NF-OSI
```

### Process all projects

```bash
python3 extract_templates.py
```

The script excludes `demo` and `demo_upsert` projects from the master data_model_urls.csv file entirely. To process additional ignored projects at runtime:

```bash
# Skip CB during processing
python3 extract_templates.py --ignore-project CB
```

### Include all templates (including attributes)

By default, the script filters out "Attribute" type templates (simple properties like Age, Dose, etc.). To include everything:

```bash
python3 extract_templates.py --project NF-OSI --include-all
```

### Specify custom paths

```bash
python3 extract_templates.py \
  --data-model-urls /path/to/urls.csv \
  --output-dir /path/to/output
```

## Output

The script generates a CSV file for each project with the following columns:

| Column | Description |
|--------|-------------|
| template_id | The class/schema name (e.g., "WGSTemplate") |
| display_name | Human-readable name |
| species | Inferred species (Human, Mouse, Multi-species, Not specified, Animal model) |
| file_type | Specific file format for annotation templates (FASTQ, BAM, VCF, etc.) |
| configured_template_role | Value from the template config (when available) indicating whether the template is configured as a **record** template or an **annotation** template |
| description | Template description from the data model |

### Example Output

```csv
template_id,display_name,species,file_type,configured_template_role,description
WGSTemplate,WGSTemplate,Multi-species,FASTQ,Annotation,Template for describing raw data from Whole Genome Sequencing (WGS)
HumanCohortTemplate,HumanCohortTemplate,Human,N/A,Record,Data of biosamples from human patients...
```

## Summarizing Results

After extracting templates, you can generate a summary table across all projects:

```bash
python3 summarize_template_outputs.py
```

This produces a markdown table showing:
- **Total**: Total number of templates per project
- **Annotation**: Count of templates with `configured_template_role == "Annotation"`
- **Record**: Count of templates with `configured_template_role == "Record"`
- **N/A**: Count of templates with no configured role

### Example Summary Output

```
| Project | Total | Annotation | Record | N/A |
| --- | --- | --- | --- | --- |
| ADKP | 32 | 1 | 28 | 3 |
| EL | 17 | 11 | 4 | 2 |
| HTAN | 135 | 62 | 27 | 46 |
| NF-OSI | 49 | 23 | 1 | 25 |
| Grand Total | 490 | 171 | 104 | 215 |
```

### Summary Options

```bash
# Include demo projects (excluded by default)
python3 summarize_template_outputs.py --include-demo

# Specify custom output directory
python3 summarize_template_outputs.py --outputs /path/to/outputs
```

## Inference Logic

### Species Inference

The script looks for a `Species` dependency and examines the template name, display name, and description:
- **Human**: Mentions "human", "patient", or "participant" in any text field
- **Mouse**: Mentions "mouse" or "mice" in any text field
- **Animal model**: Mentions "animal", "non_human", or "nonhuman" in any text field
- **Multi-species**: Has Species dependency but no specific mention
- **Not specified**: No Species dependency

### Template Role Inference

1. **Template Config Alignment**: When available, the template config is the primary source for determining template role
   - `submitted_as: "record"` (or `type: "record"`) → Sets `configured_template_role` to `Record`
   - `submitted_as: "annotation"` (or `type: "file"`) → Sets `configured_template_role` to `Annotation`
   - The detected config role is recorded in the `configured_template_role` column for quick cross-checking with production DCA configurations

2. **Fallback to Heuristics** (when configs are missing):
   - Templates without a template config entry will have `configured_template_role` set to `N/A`
   - Heuristics are still used internally to determine file types for annotation templates

### File Type Inference

For annotation templates, infers specific file types:
- **Sequencing**: FASTQ (raw) or BAM/CRAM (processed)
- **Variants**: VCF
- **Expression**: Expression matrix
- **Methylation Arrays**: IDAT
- **Imaging**: Image files (DICOM/TIFF/etc.)
- **Proteomics**: Mass spec data
- **Flow Cytometry**: FCS
- **Protocols/Reports**: PDF/Document

## Requirements

- Python 3.6+
- Standard library only (no external dependencies)

## Input File Format

The script expects a CSV file (`data_model_urls.csv` by default) with columns:
- `Project`: Project name (e.g., "NF-OSI")
- `Data Model URL`: URL to the JSON-LD data model
- `Template Config URL`: Location of the template config used by DCA

When the default master file path is used, the script automatically regenerates this CSV by scanning each project's `dca_config.json`. Example:
```csv
Project,Data Model URL,Template Config URL
NF-OSI,https://raw.githubusercontent.com/nf-osi/nf-metadata-dictionary/v10.07.0/NF.jsonld,https://raw.githubusercontent.com/nf-osi/nf-metadata-dictionary/v10.07.0/dca-template-config.json
ADKP,https://raw.githubusercontent.com/adknowledgeportal/data-models/main/AD.model.jsonld,https://raw.githubusercontent.com/adknowledgeportal/data-models/main/dca-template-config.json
```

## Extending the Script

### Custom Master Files

If you provide a custom master CSV via `--data-model-urls`, ensure it includes the `Template Config URL` column. The script will still attempt to backfill missing template config URLs by consulting local `dca_config.json` files when possible.

### Improving Inference Logic

To improve species, data type, or file type inference, modify the respective functions:
- `infer_species()` - Line 82
- `infer_type_and_filetype()` - Line 110
- `infer_filetype_from_name()` - Line 176

## Notes

- The script automatically filters out attribute-type templates by default (use `--include-all` to include them)
- Some templates are abstract (parent classes) and may not be used directly for data submission
- File type inference is heuristic-based and may need refinement for specific projects
- The script handles network errors gracefully and will continue processing other projects if one fails
