# Recipe nutrition estimates

The build generates each nutrition card and its Google Recipe `nutrition` fields from the same calculation. Ingredient contributions are their grams multiplied by nutrient values per 100 g; the batch total is divided by the chosen serving count. Google metadata describes the default visible serving, with a numeric `recipeYield`. Other portion sizes are available where the recipe supports them.

## Data and editing

- `data/nutrition/foods.json` contains the pinned nutrient records and their provenance.
- `data/nutrition/recipes/*.json` maps every recipe ingredient, in order, to a food and gram weight, or explicitly excludes an optional ingredient. Each weight has a source and assumptions are shown beside the card.
- `scripts/nutrition.py` calculates, renders and checks the results. It rejects stale ingredient mappings, invalid weights and serving counts. Unknown nutrient data stay unknown; they are never assumed to be zero.
- `assets/nutrition.css` and `assets/nutrition.js` provide the shared display and portion selector. Nutrition is omitted from the compact recipe printout.

Edit the recipe and its mapping together. Run `npm test`, then check the default serving, any alternate serving, mobile layout and ingredient-source disclosure. The build checks that visible nutrients match the structured data and saved calculation.

## Sources and limitations

The baseline is the USDA FoodData Central **SR Legacy April 2018** release, downloaded from the [official datasets page](https://fdc.nal.usda.gov/download-datasets/). It is public-domain data. `scripts/import_nutrition_foods.py` imports selected foods from the official CSV archive into the small checked-in catalog; builds need neither an API key nor a network request. Food records retain their USDA IDs and household portions. Raw peeled potato uses Health Canada’s Canadian Nutrient File because the chosen USDA record includes skin. That record retains its CNF code, source and nutrient-endpoint URLs. Where a different primary source is needed, its provenance is stored with the record.

Household baking weights use [King Arthur Baking’s ingredient weight chart](https://www.kingarthurbaking.com/learn/ingredient-weight-chart), with food-specific USDA portions where appropriate. These conversions are estimates; cups, brands and packing methods differ. Raw, drained or cooked ingredient weights must match the selected nutrient record. Finished weights or bowl volumes must not be represented as measured unless they have actually been measured.

Daily Value percentages use [Health Canada’s reference for ages 4 and older](https://www.canada.ca/en/health-canada/services/technical-documents-labelling-requirements/table-daily-values/nutrition-labelling.html). Saturated-fat percentages include trans fat and remain unknown if either value is missing. Display rounds calories and most milligrams to whole numbers and grams/iron to one decimal; these are home-recipe estimates, **not certified package labels**. Optional garnishes, ingredient choices, substitutions and salt assumptions are disclosed per recipe.

[Google’s Recipe guidance](https://developers.google.com/search/docs/appearance/structured-data/recipe) recommends calories per serving and requires a numeric serving count when calories are included. Correct markup supports eligibility; it does not guarantee a rich result or ranking.

## Suggested portions

These are editorial serving suggestions, not regulated reference amounts. Use the stated fraction of the finished batch; no finished bowl volume or weight has been measured.

| Recipe | Batch divided into |
| --- | --- |
| Chocolate chip cookies | 16 medium or 9 large cookies |
| Good Friday scones | 12 small or 8 large scones |
| Banana bread | 8 slices |
| Ash cakes | 4 cakes |
| Hard Time Pudding | 8 portions, including sauce |
| Rice pudding | 4 small bowls |
| Baked beans | 8 side portions, dried-bean version |
| Beef and noodles | 6 dinner bowls |
| Chipped beef on toast | 4 plates, each 2 toast slices plus a quarter of the sauce |
| Hoover stew | 8 bowls |
| Potato soup | 8 bowls |
| Tuna stew | 8 bowls, bread excluded |
| Zaprezna soup | 6 bowls |
| Milk potatoes | 6 side portions |

Recipe-specific options are selected explicitly: salt-to-taste in the soup group is modelled as half a teaspoon per batch, while other recipes exclude discretionary salt. Read each card’s assumptions; these estimates are not interchangeable with a different ingredient option.
