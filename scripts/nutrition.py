"""Build transparent, estimated nutrition from pinned food data and weighed ingredients."""
from decimal import Decimal, ROUND_HALF_UP
from html import escape
import json
from pathlib import Path
import re

NUTRIENTS = {
    'calories': ('1008', 'Calories', 'calories', 'calories'),
    'fat': ('1004', 'Fat', 'g', 'fatContent'),
    'saturated_fat': ('1258', 'Saturated', 'g', 'saturatedFatContent'),
    'trans_fat': ('1257', 'Trans', 'g', 'transFatContent'),
    'carbohydrate': ('1005', 'Carbohydrate', 'g', 'carbohydrateContent'),
    'fiber': ('1079', 'Fibre', 'g', 'fiberContent'),
    'sugar': ('2000', 'Sugars', 'g', 'sugarContent'),
    'protein': ('1003', 'Protein', 'g', 'proteinContent'),
    'cholesterol': ('1253', 'Cholesterol', 'mg', 'cholesterolContent'),
    'sodium': ('1093', 'Sodium', 'mg', 'sodiumContent'),
    'potassium': ('1092', 'Potassium', 'mg', None),
    'calcium': ('1087', 'Calcium', 'mg', None),
    'iron': ('1089', 'Iron', 'mg', None),
}
DAILY_VALUES = {'fat': 75, 'fiber': 28, 'sugar': 100, 'sodium': 2300,
                'potassium': 3400, 'calcium': 1300, 'iron': 18}
DV_URL = 'https://www.canada.ca/en/health-canada/services/technical-documents-labelling-requirements/table-daily-values/nutrition-labelling.html'
FDC_URL = 'https://fdc.nal.usda.gov/download-datasets/'
JSON_LD = re.compile(r'(<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>)([\s\S]*?)(</script\s*>)', re.I)


def decimal(value):
    number = Decimal(str(value))
    if not number.is_finite() or number < 0:
        raise ValueError(f'Invalid nutrition quantity: {value!r}')
    return number


def recipes_in(value):
    if isinstance(value, dict):
        if value.get('@type') == 'Recipe':
            yield value
        for item in value.values():
            yield from recipes_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from recipes_in(item)


def validate_inputs(config, foods, ingredient_texts):
    mapped = [item['recipe_text'] for item in config['ingredients']]
    if mapped != ingredient_texts:
        raise ValueError(f"{config['page']}: nutrition ingredient mapping is stale or incomplete")
    portions = config['portions']
    ids = [portion['id'] for portion in portions]
    if len(set(ids)) != len(ids) or config['default_portion'] not in ids:
        raise ValueError('Nutrition portions need unique IDs and a valid default')
    for portion in portions:
        count = portion['count']
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError('Nutrition serving count must be a positive integer')
        if not portion['label'] or not portion['batch_label']:
            raise ValueError('Nutrition serving descriptions are required')
    for item in config['ingredients']:
        if item.get('excluded'):
            if not item.get('reason'):
                raise ValueError('Excluded ingredients need a visible explanation')
            continue
        if item['food'] not in foods or decimal(item['grams']) <= 0:
            raise ValueError(f"Unknown food or invalid weight: {item}")
        if not item.get('weight_source', '').startswith('https://'):
            raise ValueError('Each ingredient weight needs a source')
        for amount in foods[item['food']]['per_100g'].values():
            if amount is not None:
                decimal(amount)


def batch_nutrients(config, foods):
    totals = {key: Decimal(0) for key in NUTRIENTS}
    for item in config['ingredients']:
        if item.get('excluded'):
            continue
        nutrients = foods[item['food']]['per_100g']
        for key in totals:
            value = nutrients.get(key)
            if value is None:
                totals[key] = None
            elif totals[key] is not None:
                totals[key] += decimal(value) * decimal(item['grams']) / 100
    return totals


def per_serving(totals, count):
    return {key: value / count if value is not None else None for key, value in totals.items()}


def amount_text(key, value):
    if value is None:
        return '—'
    places = Decimal('0.1') if NUTRIENTS[key][2] == 'g' or key == 'iron' else Decimal('1')
    rounded = value.quantize(places, rounding=ROUND_HALF_UP)
    return format(rounded, 'f').rstrip('0').rstrip('.') if places == Decimal('0.1') else str(rounded)


def display_amount(key, value):
    text = amount_text(key, value)
    return text if value is None or key == 'calories' else f'{text} {NUTRIENTS[key][2]}'


def percent(key, values):
    if key == 'saturated_fat':
        if values['saturated_fat'] is None or values['trans_fat'] is None:
            return '—'
        value, reference = values['saturated_fat'] + values['trans_fat'], 20
    elif key in DAILY_VALUES:
        value, reference = values[key], DAILY_VALUES[key]
        if value is None:
            return '—'
    else:
        return ''
    return f"{(value * 100 / reference).quantize(Decimal('1'), rounding=ROUND_HALF_UP)}%"


def nutrition_schema(portion, values):
    result = {'@type': 'NutritionInformation', 'servingSize': portion['label']}
    for key, (_, _, unit, schema_key) in NUTRIENTS.items():
        if schema_key and values[key] is not None:
            result[schema_key] = f'{amount_text(key, values[key])} {unit}'
    return result


def render_panel(portion, values, default):
    hidden = '' if portion['id'] == default else ' hidden'
    rows = []
    for key, (_, name, _, _) in NUTRIENTS.items():
        if key == 'calories':
            continue
        classes = []
        if key in {'saturated_fat', 'trans_fat', 'fiber', 'sugar'}:
            classes.append('nutrition-sub')
        if key in {'carbohydrate', 'potassium'}:
            classes.append('nutrition-rule')
        if key == 'protein':
            classes.append('nutrition-protein')
        rows.append(f'<tr class="{" ".join(classes)}"><th scope="row">{name} <span data-portion="{escape(portion["id"])}" data-nutrient-value="{key}">{display_amount(key, values[key])}</span></th><td data-portion="{escape(portion["id"])}" data-nutrient-dv="{key}">{percent(key, values)}</td></tr>')
    return f'''<div class="nutrition-panel" data-portion="{escape(portion['id'])}" data-serving-count="{portion['count']}"{hidden}>
      <div class="nutrition-label">
        <h3>Nutrition Facts</h3>
        <p class="nutrition-estimate">Estimated per serving</p>
        <p class="nutrition-serving">{escape(portion['label'])}</p>
        <p class="nutrition-batch">{portion['count']} servings per batch · {escape(portion.get('fraction', '1/' + str(portion['count']) + ' of recipe'))}</p>
        <div class="nutrition-calories"><span>Calories</span><strong data-portion="{escape(portion['id'])}" data-nutrient-value="calories">{amount_text('calories', values['calories'])}</strong></div>
        <table class="nutrition-table"><caption class="visually-hidden">Estimated nutrients per {escape(portion['label'])}</caption>
        <thead><tr><th scope="col"><span class="visually-hidden">Nutrient and amount</span></th><th scope="col">% Daily Value*</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
        <p class="nutrition-daily-note">* Canadian Daily Values for ages 4 and older. Saturated fat % includes trans fat when available. — means source data are unavailable, not zero.</p>
      </div></div>'''


def render_section(config, foods, totals):
    options = ''.join(f'<option value="{escape(p["id"])}"{" selected" if p["id"] == config["default_portion"] else ""}>{escape(p["label"])}</option>' for p in config['portions'])
    panels = ''.join(render_panel(p, per_serving(totals, p['count']), config['default_portion']) for p in config['portions'])
    rows = []
    for item in config['ingredients']:
        if item.get('excluded'):
            description = f'Not included: {item["reason"]}'
            source = '—'
        else:
            food = foods[item['food']]
            description = f'{item["grams"]} g · {item.get("basis", food["description"])}'
            source = f'<a href="{escape(item["weight_source"])}">Weight</a> · <a href="{escape(food["source_url"])}">Nutrients</a>'
        rows.append(f'<tr><th scope="row">{escape(item["recipe_text"])}</th><td>{escape(description)}</td><td>{source}</td></tr>')
    notes = ''.join(f'<p>{escape(note)}</p>' for note in config['notes'])
    return f'''<section id="nutrition" class="nutrition-section" aria-labelledby="nutrition-title">
      <h2 id="nutrition-title" class="visually-hidden">Estimated nutrition</h2>
      <div class="nutrition-controls" hidden><label for="nutrition-serving">Serving size</label><select id="nutrition-serving" data-nutrition-select hidden disabled>{options}</select></div>
      <div class="nutrition-panels">{panels}</div>
      <div class="nutrition-notes"><p><strong>About this estimate</strong></p>{notes}
      <p>Calculated from ingredient weights and <a href="{FDC_URL}">USDA FoodData Central</a> records. Brands, substitutions and preparation can change the result. These are home-recipe estimates, not laboratory-tested package labels.</p>
      <details><summary>Ingredients and calculation sources</summary><div class="nutrition-table-scroll"><table class="nutrition-ingredients"><caption>Amounts used for this batch estimate</caption><thead><tr><th scope="col">Recipe ingredient</th><th scope="col">Modelled amount</th><th scope="col">Sources</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></details>
      <p class="nutrition-source-note"><a href="{DV_URL}">Daily Value reference</a>. Values are rounded for display; missing source values remain unknown.</p></div>
      <p class="visually-hidden" data-nutrition-status aria-live="polite"></p></section>'''


def apply_nutrition(root: Path, output: Path):
    directory = root / 'data' / 'nutrition'
    if not directory.exists():
        return
    foods = json.loads((directory / 'foods.json').read_text())['foods']
    for config_path in sorted((directory / 'recipes').glob('*.json')):
        config = json.loads(config_path.read_text())
        page = output / config['page']
        source = page.read_text()
        recipe_objects = [recipe for match in JSON_LD.finditer(source) for recipe in recipes_in(json.loads(match[2]))]
        if len(recipe_objects) != 1 or source.count('<!-- nutrition -->') != 1:
            raise ValueError(f'{page.name}: expected one recipe and one nutrition insertion point')
        validate_inputs(config, foods, recipe_objects[0]['recipeIngredient'])
        totals = batch_nutrients(config, foods)
        if totals['calories'] is None:
            raise ValueError(f'{page.name}: calories are unavailable')
        portion = next(p for p in config['portions'] if p['id'] == config['default_portion'])
        def enrich(match):
            data = json.loads(match[2])
            for recipe in recipes_in(data):
                recipe['nutrition'] = nutrition_schema(portion, per_serving(totals, portion['count']))
                recipe['recipeYield'] = [str(portion['count']), portion['batch_label']]
            return match[1] + '\n' + json.dumps(data, indent=2, ensure_ascii=False) + '\n    ' + match[3]
        source = JSON_LD.sub(enrich, source).replace('<!-- nutrition -->', render_section(config, foods, totals))
        page.write_text(source)


def validate_built_nutrition(page, root):
    """Check the visible cards and Google markup against the same saved calculation."""
    config_path = root / 'data' / 'nutrition' / 'recipes' / (Path(page.name).stem + '.json')
    if not config_path.exists():
        return []
    foods = json.loads((root / 'data' / 'nutrition' / 'foods.json').read_text())['foods']
    config = json.loads(config_path.read_text())
    totals = batch_nutrients(config, foods)
    default = next(p for p in config['portions'] if p['id'] == config['default_portion'])
    problems = []
    recipes = [r for attrs, text in page.scripts if attrs.get('type') == 'application/ld+json' for r in recipes_in(json.loads(text))]
    expected = nutrition_schema(default, per_serving(totals, default['count']))
    if len(recipes) != 1 or recipes[0].get('nutrition') != expected:
        problems.append('nutrition structured data must match the default visible serving')
    if len(recipes) != 1 or recipes[0].get('recipeYield') != [str(default['count']), default['batch_label']]:
        problems.append('nutrition requires matching numeric recipeYield')
    if 'nutrition' not in page.ids:
        problems.append('missing visible nutrition section')
    for portion in config['portions']:
        values = per_serving(totals, portion['count'])
        panels = [attrs for _, attrs in page.tags if 'nutrition-panel' in attrs.get('class', '').split() and attrs.get('data-portion') == portion['id']]
        if len(panels) != 1 or panels[0].get('data-serving-count') != str(portion['count']) or ('hidden' in panels[0]) != (portion['id'] != default['id']):
            problems.append(f'{portion["id"]}: serving panel or default visibility is incorrect')
        for key in NUTRIENTS:
            elements = [attrs for _, attrs in page.tags if attrs.get('data-nutrient-value') == key and attrs.get('data-portion') == portion['id']]
            wanted = display_amount(key, values[key]).replace('—', '-')
            if len(elements) != 1 or page.text_for(elements[0]) != wanted:
                problems.append(f'{portion["id"]}: visible {key} differs from calculation')
    return [f'{page.name}: {message}' for message in problems]
