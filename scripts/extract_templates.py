#!/usr/bin/env python3
"""
Extract template information from data models for DCA configuration.

This script processes JSON-LD data models to extract:
- Template ID (schema_name)
- Inferred species (from Species property if available)
- File type (for annotation templates)
- Configured template role (record vs annotation when template config is available)

Output: CSV file for each model with the extracted information.
"""

import json
import csv
import sys
import argparse
from urllib.request import urlopen
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_MASTER = Path('data_model_urls.csv')
MASTER_FIELDS = ['Project', 'Data Model URL', 'Template Config URL']
DEFAULT_IGNORE_PROJECTS = {'demo', 'demo_upsert'}


def discover_projects_from_configs(root: Path) -> List[Dict[str, str]]:
    """Scan local project directories for dca_config.json files and load model metadata."""
    rows: List[Dict[str, str]] = []
    for config_path in sorted(root.glob('*/dca_config.json')):
        project = config_path.parent.name

        # Skip demo projects entirely
        if project in DEFAULT_IGNORE_PROJECTS:
            continue

        with config_path.open('r', encoding='utf-8') as fh:
            data = json.load(fh)

        dcc_block = data.get('dcc', {})
        data_model_url = dcc_block.get('data_model_url', '')
        template_config_url = dcc_block.get('template_menu_config_file', '')

        if not data_model_url:
            continue

        rows.append({
            'Project': project,
            'Data Model URL': data_model_url,
            'Template Config URL': template_config_url
        })

    return rows


def write_master_file(master_file: Path, rows: List[Dict[str, str]]) -> None:
    """Persist project metadata to the master CSV file."""
    with master_file.open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=MASTER_FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def fetch_json(url: str) -> dict:
    """Fetch JSON data from a URL."""
    with urlopen(url) as response:
        return json.loads(response.read().decode('utf-8'))


def load_local_data_model(project_name: str) -> Optional[Dict]:
    """Load a data model previously downloaded to data_models/."""
    local_dir = Path('data_models')
    candidate = local_dir / f"{project_name}_data_model.jsonld"
    if candidate.exists():
        try:
            return json.loads(candidate.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: Could not read local data model for {project_name}: {exc}")
    return None


def extract_templates_from_model(model_url: str, project_name: str = None) -> List[Dict]:
    """
    Extract template classes from a JSON-LD data model.

    Templates are defined as classes that have sms:requiresDependency properties.

    Returns:
        List of dictionaries containing template information
    """
    # Try to load from local cache first
    if project_name:
        local_data = load_local_data_model(project_name)
        if local_data is not None:
            print(f"Using local data model for {project_name}...")
            data = local_data
            graph = data.get('@graph', [])
        else:
            print(f"Fetching data model from {model_url}...")
            data = fetch_json(model_url)
            graph = data.get('@graph', [])
    else:
        print(f"Fetching data model from {model_url}...")
        data = fetch_json(model_url)
        graph = data.get('@graph', [])

    templates = []
    for item in graph:
        if item.get('@type') == 'rdfs:Class':
            label = item.get('rdfs:label', '')
            requires_dep = item.get('sms:requiresDependency', [])

            # Templates have required dependencies
            if requires_dep:
                templates.append({
                    'id': item.get('@id', ''),
                    'label': label,
                    'displayName': item.get('sms:displayName', ''),
                    'comment': item.get('rdfs:comment', ''),
                    'requiresDependency': requires_dep,
                    'subClassOf': item.get('rdfs:subClassOf', [])
                })

    return templates


def load_local_template_config(project_name: str) -> Optional[Dict]:
    """Load a template config previously downloaded to template_configs/."""
    local_dir = Path('template_configs')
    candidate = local_dir / f"{project_name}_template_config.json"
    if candidate.exists():
        try:
            return json.loads(candidate.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: Could not read local template config for {project_name}: {exc}")
    return None


def get_template_config(project_name: str, config_url: Optional[str]) -> Optional[Dict]:
    """
    Fetch the template configuration file if available.

    This file contains additional metadata about templates like display names
    and whether they are file or record based.
    """
    local_config = load_local_template_config(project_name)
    if local_config is not None:
        return local_config

    if not config_url:
        return None

    try:
        print(f"Fetching template config from {config_url}...")
        return fetch_json(config_url)
    except Exception as e:
        print(f"Warning: Could not fetch template config for {project_name}: {e}")
        return None


def infer_species(template: Dict) -> str:
    """
    Infer species from template dependencies and naming.

    Returns:
        - "Human" if mentions human in name/description
        - "Mouse" if mentions mouse in name/description
        - "Animal model" if mentions animal/non-human in name/description
        - "Multi-species" if has Species dependency but no specific mention
        - "Not specified" if no Species dependency and no species keywords
    """
    requires_dep = template.get('requiresDependency', [])
    has_species = any(dep.get('@id', '').endswith(':Species') for dep in requires_dep)

    comment = template.get('comment', '').lower()
    label = template.get('label', '').lower()
    display_name = template.get('displayName', '').lower()

    # Combine all text for searching
    all_text = ' '.join([comment, label, display_name])

    # Check for species mentions in any text (regardless of Species dependency)
    # Check non-human patterns first (before general human check)
    if 'non_human' in all_text or 'nonhuman' in all_text or 'non-human' in all_text:
        return "Animal model"
    elif 'human' in all_text or 'patient' in all_text or 'participant' in all_text:
        return "Human"
    elif 'mouse' in all_text or 'mice' in all_text:
        return "Mouse"
    elif 'animal' in all_text:
        return "Animal model"
    elif has_species:
        # Has Species dependency but no specific mention
        return "Multi-species"
    else:
        return "Not specified"


def normalize_config_role(raw_role: str) -> str:
    """Map config role values onto canonical labels used in the output."""
    if not raw_role:
        return 'N/A'
    role_lower = raw_role.lower()
    if role_lower in {'annotation', 'file', 'file_annotation', 'fileonly', 'file_only'}:
        return 'Annotation'
    if role_lower in {'record', 'record_submission', 'recordonly', 'record_only', 'table'}:
        return 'Record'
    return raw_role.replace('_', ' ').title()


def heuristic_type_and_filetype(label_lower: str, comment_lower: str,
                               display_name_lower: str) -> Tuple[str, str]:
    """Infer data type/file type from template naming patterns."""
    text_blocks = ' '.join(filter(None, [label_lower, comment_lower, display_name_lower]))

    attribute_keywords = ['age', 'dose', 'depth', 'length', 'distance', 'timepoint',
                          'datatype', 'workflow']
    if any(keyword in label_lower for keyword in attribute_keywords):
        return 'Attribute', 'N/A'

    if any(keyword in label_lower for keyword in ['portal', 'publication']):
        return 'Reference', 'N/A'

    clinical_keywords = ['clinical', 'patient', 'participant', 'biospecimen',
                         'individual', 'cohort', 'demographics', 'epidemiology']
    if any(keyword in text_blocks for keyword in clinical_keywords):
        return 'Clinical data', 'N/A'

    if 'metadata' in text_blocks or 'annotation' in text_blocks:
        return 'Metadata', infer_filetype_from_name(label_lower or display_name_lower)

    if any(keyword in text_blocks for keyword in ['assay', 'template', 'sequencing', 'imaging',
                                                  'proteomics', 'genomics', 'epigenetics',
                                                  'methylation', 'microscopy']):
        return 'Metadata', infer_filetype_from_name(label_lower)

    if any(keyword in text_blocks for keyword in ['protocol', 'documentation', 'report', 'code']):
        return 'Metadata', 'Document'

    if 'processed' in text_blocks:
        return 'Metadata', infer_filetype_from_name(label_lower)

    return 'Unknown', 'N/A'


def infer_type_and_filetype(template: Dict, template_config: Optional[Dict]) -> Tuple[str, str, str]:
    """
    Infer whether template is for clinical data or metadata, and if metadata, what filetype.

    Returns:
        Tuple of (data_type, file_type, configured_role) where:
        - data_type: "Clinical data", "Metadata", "Record", or "Attribute"
        - file_type: specific file format if metadata, otherwise "N/A"
        - configured_role: "Record", "Annotation", another value from config, or "N/A"
    """
    label = template.get('label', '')
    comment = template.get('comment', '')
    display_name = template.get('displayName', '')
    label_lower = label.lower()
    comment_lower = comment.lower()
    display_name_lower = display_name.lower()
    configured_role = 'N/A'
    data_type = None
    file_type = 'N/A'

    template_schema_name = template.get('id', '').split(':')[-1]
    template_display = template.get('displayName', '')

    # Priority 1: Template Config Alignment (when available)
    if template_config:
        manifest_schemas = template_config.get('manifest_schemas', [])
        for schema in manifest_schemas:
            schema_name = schema.get('schema_name', '')
            if not schema_name:
                continue
            if schema_name not in {template.get('label'), template_schema_name, template_display}:
                continue

            config_role_raw = schema.get('submitted_as') or schema.get('type', '')
            configured_role = normalize_config_role(config_role_raw)
            schema_display_name = schema.get('display_name', '').lower()

            # Config determines data type
            if configured_role == 'Annotation':
                data_type = 'Metadata'
                file_type = infer_filetype_from_name(schema_display_name or label_lower)
            elif configured_role == 'Record':
                data_type = 'Clinical data'
                file_type = 'N/A'
            # For non-standard config roles, keep as Unknown to fall through to heuristics
            break

    # Priority 2: Fallback to heuristics (when config is missing or inconclusive)
    if data_type is None:
        data_type, file_type = heuristic_type_and_filetype(label_lower, comment_lower, display_name_lower)

    # Ensure metadata templates always have a file type string
    if data_type == 'Metadata' and file_type == 'N/A':
        file_type = infer_filetype_from_name(label_lower or display_name_lower)

    return data_type, file_type, configured_role


def infer_filetype_from_name(name: str) -> str:
    """
    Infer specific file type from template name.

    Returns specific assay/data type like "FASTQ", "BAM", "VCF", etc.
    """
    name_lower = name.lower()

    # Sequencing data types
    if any(seq in name_lower for seq in ['wgs', 'wes', 'rnaseq', 'rna-seq', 'scrna', 'chip-seq', 'chipseq']):
        if 'processed' in name_lower or 'aligned' in name_lower:
            if 'variant' in name_lower:
                return "VCF"
            elif 'expression' in name_lower:
                return "Expression matrix"
            else:
                return "BAM/CRAM"
        else:
            return "FASTQ"

    # Methylation
    if 'methylation' in name_lower or 'epigenetic' in name_lower:
        if 'array' in name_lower:
            return "IDAT"
        else:
            return "FASTQ"

    # Imaging
    if 'imaging' in name_lower or 'mri' in name_lower:
        return "Image files (DICOM/TIFF/etc.)"

    # Proteomics
    if 'proteomics' in name_lower:
        return "Mass spec data"

    # FACS/Flow cytometry
    if 'facs' in name_lower or 'flow' in name_lower:
        return "FCS"

    # Generic processed data
    if 'processed' in name_lower:
        return "Processed data"

    # Protocols/documents
    if 'protocol' in name_lower or 'report' in name_lower:
        return "PDF/Document"

    return "Various"


def process_model(project_name: str, model_url: str, template_config_url: Optional[str],
                  output_dir: Path, include_all: bool = False) -> None:
    """
    Process a single data model and generate CSV output.

    Args:
        project_name: Name of the project (e.g., "NF-OSI")
        model_url: URL to the JSON-LD data model
        template_config_url: Optional URL to the template configuration
        output_dir: Directory to write output CSV
        include_all: If False, filters out Attribute-type templates (default: False)
    """
    print(f"\n{'='*80}")
    print(f"Processing {project_name}")
    print(f"{'='*80}")

    # Fetch data
    templates = extract_templates_from_model(model_url, project_name)
    template_config = get_template_config(project_name, template_config_url)

    print(f"Found {len(templates)} templates")

    # Process each template
    results = []
    for template in templates:
        template_id = template['label']
        species = infer_species(template)
        data_type, file_type, configured_role = infer_type_and_filetype(template, template_config)

        # Optionally filter out attributes (these are not full templates)
        if not include_all and data_type == 'Attribute':
            continue

        results.append({
            'template_id': template_id,
            'display_name': template.get('displayName', template_id),
            'species': species,
            'file_type': file_type,
            'configured_template_role': configured_role,
            'description': template.get('comment', '')
        })

    # Write to CSV
    output_file = output_dir / f"{project_name}_templates.csv"
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                'template_id',
                'display_name',
                'species',
                'file_type',
                'configured_template_role',
                'description'
            ]
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nWrote {len(results)} templates to {output_file}")

    # Print summary
    print("\nSummary by template role:")
    roles = {}
    for r in results:
        role = r['configured_template_role']
        roles[role] = roles.get(role, 0) + 1

    for role, count in sorted(roles.items()):
        print(f"  {role}: {count}")

    # File type breakdown for annotation templates
    annotation_templates = [r for r in results if r['configured_template_role'] == 'Annotation']
    if annotation_templates:
        print("\nAnnotation file types:")
        file_types = {}
        for r in annotation_templates:
            ft = r['file_type']
            file_types[ft] = file_types.get(ft, 0) + 1
        for ft, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {ft}: {count}")


def main():
    parser = argparse.ArgumentParser(
        description='Extract template information from DCA data models'
    )
    parser.add_argument(
        '--project',
        help='Specific project to process (e.g., NF-OSI). If not specified, processes all.'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('template_outputs'),
        help='Directory for output CSV files (default: template_outputs)'
    )
    parser.add_argument(
        '--data-model-urls',
        type=Path,
        default=Path('data_model_urls.csv'),
        help='CSV file containing project names and data model URLs'
    )
    parser.add_argument(
        '--include-all',
        action='store_true',
        help='Include all templates including attributes (default: filters out attributes)'
    )
    parser.add_argument(
        '--ignore-project',
        action='append',
        default=None,
        help='Project name to skip (repeatable). Use "none" to clear default ignores (demo, demo_upsert).'
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(exist_ok=True)

    # Build or load project metadata index
    try:
        use_default_master = args.data_model_urls.resolve() == DEFAULT_MASTER.resolve()
    except FileNotFoundError:
        use_default_master = args.data_model_urls == DEFAULT_MASTER

    if use_default_master:
        projects = discover_projects_from_configs(Path('.'))
        write_master_file(args.data_model_urls, projects)
    else:
        if not args.data_model_urls.exists():
            print(f"Error: Master file '{args.data_model_urls}' not found")
            sys.exit(1)

        with open(args.data_model_urls, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            projects = list(reader)

        if not projects:
            print(f"Error: No projects found in {args.data_model_urls}")
            sys.exit(1)

        if 'Template Config URL' not in (reader.fieldnames or []):
            discovered = {row['Project']: row for row in discover_projects_from_configs(Path('.'))}
            for row in projects:
                row['Template Config URL'] = discovered.get(row['Project'], {}).get('Template Config URL', '')
        else:
            discovered = None
            if any(not row.get('Template Config URL') for row in projects):
                discovered = {row['Project']: row for row in discover_projects_from_configs(Path('.'))}

            if discovered:
                for row in projects:
                    if not row.get('Template Config URL'):
                        row['Template Config URL'] = discovered.get(row['Project'], {}).get('Template Config URL', '')

    ignore_projects = set(DEFAULT_IGNORE_PROJECTS)
    if args.ignore_project:
        for value in args.ignore_project:
            if value.lower() == 'none':
                ignore_projects.clear()
            else:
                ignore_projects.add(value)

    # Filter if specific project requested
    if args.project:
        projects = [p for p in projects if p['Project'] == args.project]
        if not projects:
            print(f"Error: Project '{args.project}' not found in {args.data_model_urls}")
            sys.exit(1)
    elif ignore_projects:
        ignored_before = len(projects)
        projects = [p for p in projects if p['Project'] not in ignore_projects]
        ignored_after = len(projects)
        skipped = ignored_before - ignored_after
        if skipped:
            print(f"Skipping {skipped} project(s): {', '.join(sorted(ignore_projects))}")

    # Process each project
    for project in projects:
        project_name = project['Project']
        model_url = project['Data Model URL']

        template_config_url = project.get('Template Config URL', '').strip() or None

        try:
            process_model(project_name, model_url, template_config_url,
                         args.output_dir, args.include_all)
        except Exception as e:
            print(f"Error processing {project_name}: {e}")
            import traceback
            traceback.print_exc()
            continue

if __name__ == '__main__':
    main()
