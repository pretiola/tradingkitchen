# Recipe nutrition estimates

The build generates each nutrition card and its Google Recipe `nutrition` fields from the same calculation. Ingredient contributions are their grams multiplied by nutrient values per 100 g; the batch total is divided by the chosen serving count. Google metadata describes the default visible serving, with a numeric `recipeYield`. Other portion sizes are available where the recipe supports them.

## Data and editing

- `data/nutrition/foods.json` contains the pinned nutrient records and their provenance.
- `data/nutrition/recipes/*.json` maps every recipe ingredient, in order, to a food and gram weight, or explicitly excludes an optional ingredient. Each weight has a source and assumptions are shown beside the card.
- `scripts/nutrition.py` calculates, renders and checks the results. It rejects stale ingredient mappings, invalid weights and serving counts. Unknown nutrient data stay unknown; they are never assumed to be zero.
- `assets/nutrition.css` and `assets/nutrition.js` provide the shared display and portion selector. Nutrition is omitted from the compact recipe printout.

Edit the recipe and its mapping together. Run `npm test`, then check the default serving, any alternate serving, mobile layout and ingredient-source disclosure. The build checks that visible nutrients match the structured data and saved calculation.

## Sources and limitations

The baseline is the USDA FoodData Central **SR Legacy April 2018** release, downloaded from the [official datasets page](https://fdc.nal.usda.gov/download-datasets/). It is public-domain data. `scripts/import_nutrition_foods.py` imports selected foods from the official CSV archive into the small checked-in catalog; builds need neither an API key nor a network request. Food records retain their USDA IDs and household portions. Where a different primary source is needed, its provenance is stored with the record.

Household baking weights use [King Arthur Baking’s ingredient weight chart](https://www.kingarthurbaking.com/learn/ingredient-weight-chart), with food-specific USDA portions where appropriate. These conversions are estimates; cups, brands and packing methods differ. Raw, drained or cooked ingredient weights must match the selected nutrient record. Finished weights or bowl volumes must not be represented as measured unless they have actually been measured.

Daily Value percentages use [Health Canada’s reference for ages 4 and older](https://www.canada.ca/en/health-canada/services/technical-documents-labelling-requirements/table-daily-values/nutrition-labelling.html). Saturated-fat percentages include trans fat and remain unknown if either value is missing. Display rounds calories and most milligrams to whole numbers and grams/iron to one decimal; these are home-recipe estimates, **not certified package labels**. Optional garnishes, ingredient choices, substitutions and salt assumptions are disclosed per recipe.

[Google’s Recipe guidance](https://developers.google.com/search/docs/appearance/structured-data/recipe) recommends calories per serving and requires a numeric serving count when calories are included. Correct markup supports eligibility; it does not guarantee a rich result or ranking.
