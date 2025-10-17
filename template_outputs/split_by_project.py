
import csv

def split_csv_by_project():
    project_files = {}
    project_writers = {}
    header = []

    with open('/home/avu/sage/data_curator_config/template_outputs/metadata_attribute_union.csv', 'r') as f_in:
        reader = csv.reader(f_in)
        header = next(reader)  # Capture the header

        for row in reader:
            project = row[0]
            if project not in project_files:
                file_path = f'/home/avu/sage/data_curator_config/template_outputs/project_splits/{project}.csv'
                f_out = open(file_path, 'w', newline='')
                project_files[project] = f_out
                writer = csv.writer(f_out)
                writer.writerow(header)
                project_writers[project] = writer
            
            project_writers[project].writerow(row)

    for f in project_files.values():
        f.close()

if __name__ == "__main__":
    split_csv_by_project()
