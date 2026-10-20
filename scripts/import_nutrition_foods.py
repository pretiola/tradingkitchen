"""Import selected USDA SR Legacy foods from its official, downloaded CSV archive."""
import argparse
import csv
import json
from pathlib import Path
from nutrition import NUTRIENTS

parser = argparse.ArgumentParser()
parser.add_argument('csv_directory', type=Path)
parser.add_argument('mapping', type=Path, help='JSON mapping of local food keys to FDC IDs')
parser.add_argument('--output', type=Path, default=Path('data/nutrition/foods.json'))
args = parser.parse_args()
mapping = json.loads(args.mapping.read_text())
selected = {str(value): key for key, value in mapping.items()}
foods = {}
with (args.csv_directory / 'food.csv').open() as handle:
    for row in csv.DictReader(handle):
        if row['fdc_id'] in selected:
            foods[selected[row['fdc_id']]] = {'fdc_id': int(row['fdc_id']), 'description': row['description'],
                'source_url': f'https://fdc.nal.usda.gov/food-details/{row["fdc_id"]}/nutrients',
                'dataset': 'USDA SR Legacy, April 2018', 'per_100g': {}, 'portions': []}
ids = {food['fdc_id']: food for food in foods.values()}
nutrient_ids = {value[0]: key for key, value in NUTRIENTS.items()}
with (args.csv_directory / 'food_nutrient.csv').open() as handle:
    for row in csv.DictReader(handle):
        food = ids.get(int(row['fdc_id']))
        if food is not None and row['nutrient_id'] in nutrient_ids:
            food['per_100g'][nutrient_ids[row['nutrient_id']]] = row['amount']
with (args.csv_directory / 'food_portion.csv').open() as handle:
    for row in csv.DictReader(handle):
        food = ids.get(int(row['fdc_id']))
        if food is not None:
            food['portions'].append({'amount': row['amount'], 'description': row['modifier'], 'grams': row['gram_weight']})
if set(mapping) != set(foods):
    raise SystemExit(f'Unknown food IDs: {set(mapping) - set(foods)}')
existing = json.loads(args.output.read_text()) if args.output.exists() else {'source': 'https://fdc.nal.usda.gov/download-datasets/', 'foods': {}}
existing['foods'].update(foods)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + '\n')
print(f'Imported {len(foods)} foods; catalog now has {len(existing["foods"])} records.')
