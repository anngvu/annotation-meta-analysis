
import csv

def classify_attribute(attribute):
    # Red category: Highly sensitive, likely PII
    red_keywords = [
        'id', 'name', 'location', 'address', 'phone', 'email', 'subject', 'patient',
        'donor', 'barcode', 'serial', 'number', 'code', 'zip', 'post', 'coordinate',
        'lat', 'lon', 'geo', 'date', 'time', 'age', 'sex', 'gender', 'race',
        'ethnicity', 'demographics', 'family', 'history', 'record', 'dob'
    ]
    # Yellow category: Potentially sensitive, requires context
    yellow_keywords = [
        'sample', 'specimen', 'diagnosis', 'treatment', 'assay', 'aliquot', 'analyte',
        'array', 'batch', 'block', 'case', 'cell', 'cohort', 'culture', 'data',
        'device', 'disease', 'drug', 'event', 'experiment', 'extract', 'facility',
        'flowcell', 'fragment', 'image', 'individual', 'institution', 'instrument',
        'isolate', 'kit', 'lab', 'lane', 'library', 'lot', 'marker', 'method',
        'molecule', 'mouse', 'nucleus', 'operator', 'organ', 'organism', 'panel',
        'participant', 'passage', 'platform', 'pool', 'portion', 'prep',
        'preservation', 'procedure', 'project', 'protein', 'protocol', 'reagent',
        'read', 'region', 'result', 'run', 'scan', 'section', 'sequence',
        'sequencing', 'series', 'serum', 'site', 'slide', 'software', 'source',
        'stain', 'stage', 'strain', 'study', 'sub', 'submitter', 'survey',
        'system', 'target', 'test', 'tissue', 'tube', 'tumor', 'type', 'unit',
        'use', 'well', 'workflow'
    ]

    attribute_lower = attribute.lower()

    for keyword in red_keywords:
        if keyword in attribute_lower:
            return "Red"
    for keyword in yellow_keywords:
        if keyword in attribute_lower:
            return "Yellow"
    return "Green"

def main():
    with open('/home/avu/sage/data_curator_config/template_outputs/unique_attributes.txt', 'r') as f_in, \
         open('/home/avu/sage/data_curator_config/template_outputs/classified_attributes.csv', 'w', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["Attribute", "Classification"])
        for attribute in f_in:
            attribute = attribute.strip()
            if attribute:
                classification = classify_attribute(attribute)
                writer.writerow([attribute, classification])

if __name__ == "__main__":
    main()
