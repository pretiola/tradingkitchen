"""Regression checks for metadata bugs that produced Search Console warnings."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from recipe_metadata import RecipeDocument, validate_recipe_metadata


URL = "https://tradingkitchen.org/example.html"
HTML = """
<article><p class="recipe-byline">By <a href="/">Trading Kitchen</a></p>
<section id="recipe-section">
<p class="recipe-meta">Dessert · Home cooking</p>
<dl><dt>Prep time</dt><dd data-time-field="prepTime" data-duration="PT15M">About 15 minutes</dd>
<dt>Cook time</dt><dd data-time-field="cookTime" data-duration="PT1H10M">50 minutes–1 hr 10 min</dd></dl>
<ol><li id="step-1"><strong>Mix:</strong> Whisk the dry ingredients—gently.</li>
<li id="step-2">Bake for 50–70 minutes.</li></ol>
</section></article>
"""
RECIPE = {
    "name": "Example recipe", "image": ["https://tradingkitchen.org/example.jpg"],
    "recipeIngredient": ["1 cup flour"],
    "author": {"@type": "Organization", "name": "Trading Kitchen", "url": "https://tradingkitchen.org/"},
    "recipeCategory": "Dessert", "recipeCuisine": "Home cooking", "keywords": "flour, pantry baking",
    "prepTime": "PT15M", "cookTime": "PT1H10M",
    "recipeInstructions": [
        {"@type": "HowToStep", "name": "Mix ingredients", "text": "Mix: Whisk the dry ingredients—gently.", "url": URL + "#step-1"},
        {"@type": "HowToStep", "name": "Bake", "text": "Bake for 50-70 minutes.", "url": URL + "#step-2"},
    ],
}


class RecipeMetadataTests(unittest.TestCase):
    def validate(self, recipe=None, html=HTML):
        return validate_recipe_metadata(recipe if recipe is not None else RECIPE, RecipeDocument(html), URL)

    def test_valid_recipe_without_optional_step_media_or_reviews(self):
        self.assertEqual(self.validate(), [])

    def test_missing_step_name_is_rejected(self):
        recipe = deepcopy(RECIPE)
        del recipe["recipeInstructions"][0]["name"]
        self.assertIn("Recipe step 1 needs a short name", self.validate(recipe))

    def test_malformed_or_missing_times_are_rejected(self):
        for value in (None, "9–14 minutes", "PT9M-PT14M", "PT", "P", "PT0M"):
            with self.subTest(value=value):
                recipe = dict(RECIPE, cookTime=value)
                self.assertIn("Recipe cookTime must be a positive ISO 8601 duration", self.validate(recipe))

    def test_metadata_and_visible_timing_must_agree(self):
        self.assertIn("Recipe prepTime differs from its visible duration annotation", self.validate(dict(RECIPE, prepTime="PT20M")))
        html = HTML.replace("About 15 minutes", "About 20 minutes")
        self.assertIn("Recipe prepTime differs from the visible timing or range upper bound", self.validate(html=html))

    def test_step_urls_must_target_the_same_page_and_real_instruction(self):
        for url in (None, URL, URL + "#missing", URL + "#recipe-section", "https://tradingkitchen.org/other.html#step-1", "https://other.example/example.html#step-1"):
            with self.subTest(url=url):
                recipe = deepcopy(RECIPE)
                recipe["recipeInstructions"][0]["url"] = url
                self.assertTrue(any(error.startswith("Recipe step 1") and "URL" in error for error in self.validate(recipe)))

    def test_instructions_cannot_drift_or_link_to_the_same_step_twice(self):
        recipe = deepcopy(RECIPE)
        recipe["recipeInstructions"][0]["text"] = "Use two cups of flour."
        self.assertIn("Recipe step 1 text differs from its visible instruction", self.validate(recipe))
        recipe = deepcopy(RECIPE)
        recipe["recipeInstructions"][1]["url"] = URL + "#step-1"
        self.assertIn("Recipe steps must link to every visible instruction once, in order", self.validate(recipe))

    def test_author_and_category_must_match_visible_content(self):
        recipe = deepcopy(RECIPE)
        recipe["author"]["name"] = "Someone else"
        self.assertIn("Recipe author must identify Trading Kitchen and its canonical URL", self.validate(recipe))
        self.assertIn("Recipe needs the visible Trading Kitchen byline", self.validate(html=HTML.replace("By <a href=\"/\">Trading Kitchen</a>", "By someone else")))
        self.assertIn("Recipe recipeCategory must match visible recipe metadata", self.validate(dict(RECIPE, recipeCategory="Soup")))


if __name__ == "__main__":
    unittest.main()
