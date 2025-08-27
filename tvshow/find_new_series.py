import csv
import json
import os

def get_existing_titles(json_file):
    """Get all series titles from JSON file"""
    existing_titles = set()
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                for series in data:
                    if 'title' in series:
                        existing_titles.add(series['title'].lower())
    except FileNotFoundError:
        print(f"Warning: {json_file} not found. Starting with empty list of existing titles.")
    
    return existing_titles

def process_csv(input_csv, output_csv, json_file):
    """Process the CSV and create a new CSV with only new series"""
    existing_titles = get_existing_titles(json_file)
    new_series = []
    
    with open(input_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            title = row['title']
            if title.lower() not in existing_titles:
                new_series.append({'title': title, 'year': row['year']})
    
    # Write new series to output CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
        fieldnames = ['title', 'year']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_series)
    
    return len(new_series)

if __name__ == "__main__":
    # Define file paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir)
    input_csv = os.path.join(base_dir, 'track-server', 'series_title_year.csv')
    output_csv = os.path.join(base_dir, 'track-server', 'new_series_to_add.csv')
    json_file = os.path.join(base_dir, 'track-server', 'for_help.series.json')
    
    print(f"Processing {input_csv}...")
    print(f"Comparing against {json_file}...")
    count = process_csv(input_csv, output_csv, json_file)
    print(f"Found {count} new series to add. Saved to {output_csv}")
