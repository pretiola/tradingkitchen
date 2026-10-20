from copy import deepcopy
from decimal import Decimal
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from nutrition import batch_nutrients, per_serving, validate_inputs, nutrition_schema, amount_text, percent


class NutritionTests(unittest.TestCase):
    def setUp(self):
        self.foods = {'sample': {'per_100g': {'calories': 200, 'fat': 10, 'saturated_fat': 3, 'trans_fat': 0, 'sodium': 100}}}
        self.config = {'page': 'sample.html', 'default_portion': 'small', 'portions': [
            {'id': 'small', 'count': 4, 'label': '1 small portion', 'batch_label': '4 small portions'},
            {'id': 'large', 'count': 2, 'label': '1 large portion', 'batch_label': '2 large portions'}],
            'ingredients': [{'recipe_text': '250 g sample', 'food': 'sample', 'grams': 250, 'weight_source': 'https://example.com/weight'}]}

    def test_weighted_batch_and_portion_arithmetic(self):
        totals = batch_nutrients(self.config, self.foods)
        self.assertEqual(totals['calories'], Decimal(500))
        self.assertEqual(totals['fat'], Decimal(25))
        self.assertEqual(per_serving(totals, 4)['calories'], Decimal(125))
        self.assertEqual(per_serving(totals, 2)['calories'], Decimal(250))

    def test_missing_is_unknown_and_excluded_ingredients_add_nothing(self):
        config = deepcopy(self.config)
        config['ingredients'].append({'recipe_text': 'Optional extra', 'excluded': True, 'reason': 'optional topping'})
        totals = batch_nutrients(config, self.foods)
        self.assertEqual(totals['calories'], Decimal(500))
        self.assertIsNone(totals['fiber'])
        self.assertEqual(amount_text('fiber', None), '—')
        self.assertNotIn('fiberContent', nutrition_schema(config['portions'][0], per_serving(totals, 4)))

    def test_stale_mapping_and_invalid_weights_fail(self):
        with self.assertRaises(ValueError):
            validate_inputs(self.config, self.foods, ['Changed quantity'])
        for value in ['NaN', 'Infinity', -1, 0]:
            config = deepcopy(self.config)
            config['ingredients'][0]['grams'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_inputs(config, self.foods, ['250 g sample'])

    def test_portions_need_a_positive_count_and_valid_default(self):
        for count in [0, -1, 2.5, True]:
            config = deepcopy(self.config)
            config['portions'][0]['count'] = count
            with self.subTest(count=count), self.assertRaises(ValueError):
                validate_inputs(config, self.foods, ['250 g sample'])

    def test_display_rounds_half_up_and_canadian_saturated_dv_needs_trans(self):
        self.assertEqual(amount_text('calories', Decimal('124.5')), '125')
        self.assertEqual(amount_text('fat', Decimal('1.25')), '1.3')
        self.assertEqual(percent('saturated_fat', {'saturated_fat': Decimal(3), 'trans_fat': Decimal(1)}), '20%')
        self.assertEqual(percent('saturated_fat', {'saturated_fat': Decimal(3), 'trans_fat': None}), '—')


if __name__ == '__main__':
    unittest.main()
