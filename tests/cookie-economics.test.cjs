const test = require('node:test');
const assert = require('node:assert/strict');
const { calculate, formatCurrency } = require('../assets/cookie-economics.js');

const example = {
  ingredientCost: 6.13,
  overheadCost: 0.35,
  bakedGrams: 700,
  count: 16,
  packagedPrice: 4,
  packagedGrams: 300,
  bakeryPrice: 12,
  bakeryGrams: 400,
  activeMinutes: 25,
  hourlyValue: 0
};
const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-9, `${actual} should be ${expected}`);

test('the explicit CAD $20/hour sensitivity example has independently checked totals', () => {
  const result = calculate({ ...example, hourlyValue: 20 });
  near(result.cash, 6.48);
  near(result.homePerCookie, 0.405);
  near(result.homePer100g, 0.9257142857142857);
  near(result.packagedEquivalent, 9.333333333333334);
  near(result.bakeryEquivalent, 21);
  near(result.economicCost, 14.813333333333333);
  near(result.timeAllowance, 8.333333333333334);
  near(result.packagedSavings, 2.853333333333334);
  near(result.bakerySavings, 14.52);
  near(result.packagedBreakEvenHourly, 6.848);
  near(result.bakeryBreakEvenHourly, 34.848);
});

test('the default keeps family time outside the cash comparison', () => {
  const result = calculate(example);
  near(result.cash, 6.48);
  near(result.timeAllowance, 0);
  near(result.economicCost, 6.48);
  near(result.packagedSavings, 2.853333333333334);
  near(result.bakerySavings, 14.52);
});

test('a $12 batch costs $1.33 per large cookie or $0.75 per medium cookie without changing equal-weight costs', () => {
  const medium = calculate({ ...example, ingredientCost: 12, overheadCost: 0 });
  const large = calculate({ ...example, ingredientCost: 12, overheadCost: 0, count: 9 });
  near(medium.homePerCookie, 0.75);
  near(large.homePerCookie, 1.3333333333333333);
  near(large.homePer100g, medium.homePer100g);
  near(large.packagedEquivalent, medium.packagedEquivalent);
  near(large.economicCost, medium.economicCost);
});

test('retail comparisons scale to the weighed batch, not the number of cookies', () => {
  const result = calculate({ ...example, bakedGrams: 350 });
  near(result.packagedEquivalent, 4.666666666666667);
  near(result.bakeryEquivalent, 10.5);
  near(result.homePer100g, 1.8514285714285714);
  near(result.cash, 6.48);
  near(result.economicCost, 6.48);
});

test('zero active time has no hourly break-even result and adds no time cost', () => {
  const result = calculate({ ...example, activeMinutes: 0, hourlyValue: 20 });
  near(result.economicCost, 6.48);
  near(result.timeAllowance, 0);
  assert.equal(result.packagedBreakEvenHourly, null);
  assert.equal(result.bakeryBreakEvenHourly, null);
});

test('free retail comparisons retain negative savings rather than claiming a benefit', () => {
  const result = calculate({ ...example, packagedPrice: 0, bakeryPrice: 0 });
  near(result.packagedEquivalent, 0);
  near(result.bakeryEquivalent, 0);
  near(result.packagedSavings, -6.48);
  near(result.bakerySavings, -6.48);
  near(result.packagedBreakEvenHourly, -15.552);
});

test('zero cash prices and zero time value are valid and keep calculations finite', () => {
  const result = calculate({ ...example, ingredientCost: 0, overheadCost: 0, packagedPrice: 0, bakeryPrice: 0, hourlyValue: 0 });
  for (const value of Object.values(result)) assert.equal(value, 0);
});

test('every input rejects missing, blank, negative, and nonfinite values', () => {
  for (const name of Object.keys(example)) {
    for (const invalid of [undefined, null, '', '4', NaN, Infinity, -Infinity, -1]) {
      assert.throws(() => calculate({ ...example, [name]: invalid }), RangeError, `${name}: ${invalid}`);
    }
  }
});

test('weights must be positive and cookie yield must be one of the recipe options', () => {
  for (const name of ['bakedGrams', 'packagedGrams', 'bakeryGrams']) {
    assert.throws(() => calculate({ ...example, [name]: 0 }), RangeError);
  }
  for (const count of [0, 1, 9.5, 18]) assert.throws(() => calculate({ ...example, count }), RangeError);
});

test('extreme finite inputs cannot overflow into infinite displayed results', () => {
  assert.throws(() => calculate({ ...example, ingredientCost: Number.MAX_VALUE, overheadCost: Number.MAX_VALUE }), RangeError);
  assert.throws(() => calculate({ ...example, packagedGrams: Number.MIN_VALUE }), RangeError);
  assert.throws(() => calculate({ ...example, activeMinutes: Number.MIN_VALUE }), RangeError);
});

test('the default per-cookie display rounds the computed half-cent up without rounding calculations', () => {
  const result = calculate(example);
  assert.equal(formatCurrency(result.homePerCookie), '$0.41');
  assert.equal(formatCurrency(result.cash), '$6.48');
  assert.notEqual(result.homePerCookie, 0.41);
  near(result.homePerCookie, 0.405);
});

test('currency formatting handles sub-cent inputs and signed half-cent ties', () => {
  for (const [value, expected] of [
    [0.004, '$0.00'], [0.005, '$0.01'],
    [-0.004, '$0.00'], [-0.005, '-$0.01'],
    [1.005, '$1.01'], [-1.005, '-$1.01'],
    [10.075, '$10.08'], [-10.075, '-$10.08'],
    [0, '$0.00'], [-0, '$0.00']
  ]) {
    assert.equal(formatCurrency(value), expected, String(value));
  }
});

test('arbitrary decimal inputs below a half-cent stay below it', () => {
  assert.equal(formatCurrency(0.404999999), '$0.40');
  assert.equal(formatCurrency(-0.404999999), '-$0.40');
  assert.equal(formatCurrency(1.004999999), '$1.00');
  const result = calculate({ ...example, ingredientCost: 6.123456789, overheadCost: 0.333333333 });
  near(result.cash, 6.456790122);
  near(result.homePerCookie, 0.403549382625);
  assert.equal(formatCurrency(result.homePerCookie), '$0.40');
});

test('currency formatting rejects nonfinite values and handles very large finite values without overflow', () => {
  for (const invalid of [NaN, Infinity, -Infinity, null, '0.005']) {
    assert.throws(() => formatCurrency(invalid), RangeError);
  }
  assert.equal(formatCurrency(Number.MAX_VALUE), new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD' }).format(Number.MAX_VALUE));
});
