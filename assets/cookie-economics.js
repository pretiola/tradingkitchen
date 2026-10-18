(function () {
  'use strict';

  const fieldRules = {
    ingredientCost: { label: 'Ingredient cost', minimum: 0 },
    overheadCost: { label: 'Energy and other cash costs', minimum: 0 },
    bakedGrams: { label: 'Cooled batch weight', minimum: 0, positive: true },
    count: { label: 'Batch yield', choices: [9, 16] },
    packagedPrice: { label: 'Packaged cookie price', minimum: 0 },
    packagedGrams: { label: 'Packaged cookie weight', minimum: 0, positive: true },
    bakeryPrice: { label: 'Bakery cookie price', minimum: 0 },
    bakeryGrams: { label: 'Bakery cookie weight', minimum: 0, positive: true },
    activeMinutes: { label: 'Active work time', minimum: 0 },
    hourlyValue: { label: 'Optional time tradeoff', minimum: 0 }
  };

  function validate(values) {
    const errors = {};
    for (const [name, rule] of Object.entries(fieldRules)) {
      const value = values && values[name];
      if (typeof value !== 'number' || !Number.isFinite(value)) {
        errors[name] = `${rule.label}: enter a number.`;
      } else if (rule.choices && !rule.choices.includes(value)) {
        errors[name] = 'Batch yield: choose 9 large or 16 medium cookies.';
      } else if (rule.positive && value <= 0) {
        errors[name] = `${rule.label}: enter a weight greater than zero.`;
      } else if (value < rule.minimum) {
        errors[name] = `${rule.label}: enter zero or a positive number.`;
      }
    }
    return errors;
  }

  function calculate(values) {
    const errors = validate(values);
    if (Object.keys(errors).length) {
      throw new RangeError(Object.values(errors).join(' '));
    }
    const cash = values.ingredientCost + values.overheadCost;
    const hours = values.activeMinutes / 60;
    const timeAllowance = hours * values.hourlyValue;
    const packagedEquivalent = values.packagedPrice / values.packagedGrams * values.bakedGrams;
    const bakeryEquivalent = values.bakeryPrice / values.bakeryGrams * values.bakedGrams;
    const result = {
      cash,
      homePerCookie: cash / values.count,
      homePer100g: cash / values.bakedGrams * 100,
      packagedEquivalent,
      bakeryEquivalent,
      timeAllowance,
      economicCost: cash + timeAllowance,
      packagedSavings: packagedEquivalent - cash,
      bakerySavings: bakeryEquivalent - cash,
      packagedBreakEvenHourly: values.activeMinutes === 0 ? null : (packagedEquivalent - cash) / hours,
      bakeryBreakEvenHourly: values.activeMinutes === 0 ? null : (bakeryEquivalent - cash) / hours
    };
    if (Object.values(result).some(value => value !== null && !Number.isFinite(value))) {
      throw new RangeError('These values are too large or too small to compare. Please use ordinary batch costs and weights.');
    }
    return result;
  }

  const currencyFormatter = new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD' });

  function formatCurrency(value) {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      throw new RangeError('Currency formatting requires a finite number.');
    }
    const absoluteCents = Math.abs(value) * 100;
    // Correct tiny binary arithmetic errors at a half-cent boundary only when
    // displaying money. Keep calculate() and all user inputs at full precision.
    // The cap prevents the tolerance growing into material sums at large values.
    if (absoluteCents <= Number.MAX_SAFE_INTEGER) {
      const wholeCents = Math.floor(absoluteCents);
      const fraction = absoluteCents - wholeCents;
      const tolerance = Math.min(Number.EPSILON * Math.max(1, absoluteCents), 1e-7);
      const roundedCents = wholeCents + (fraction >= 0.5 - tolerance ? 1 : 0);
      const rounded = roundedCents === 0 ? 0 : Math.sign(value) * roundedCents / 100;
      return currencyFormatter.format(rounded);
    }
    // At this magnitude a Number cannot represent individual cents reliably.
    // Intl can still format the finite value without overflowing value * 100.
    return currencyFormatter.format(value);
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { calculate, validate, formatCurrency };
  }
  if (typeof document === 'undefined') return;

  const calculator = document.querySelector('[data-cookie-economics]');
  if (!calculator) return;
  const form = calculator.querySelector('form');
  const results = calculator.querySelector('[data-calculator-results]');
  const status = calculator.querySelector('[data-calculator-status]');
  const errorMessage = calculator.querySelector('[data-calculator-error]');
  const weight = new Intl.NumberFormat('en-CA', { maximumFractionDigits: 2 });
  const formatMoney = formatCurrency;

  function setText(name, text) {
    calculator.querySelector(`[data-result="${name}"]`).textContent = text;
  }

  function savingsText(value) {
    if (Math.abs(value) < 0.005) return 'Same cash cost at this precision';
    return value > 0 ? `${formatMoney(value)} less cash spent` : `${formatMoney(-value)} extra cash cost at home`;
  }

  function breakEvenText(value, minutes) {
    if (minutes === 0) return 'No active-time comparison: active work time is zero.';
    if (value < 0) return 'No nonnegative break-even rate: the home cash cost already exceeds this comparison.';
    return `${formatMoney(value)} per active hour`;
  }

  function update() {
    const values = {};
    for (const name of Object.keys(fieldRules)) {
      const input = form.elements.namedItem(name);
      values[name] = input.value.trim() === '' ? NaN : Number(input.value);
    }
    const errors = validate(values);
    for (const name of Object.keys(fieldRules)) {
      const input = form.elements.namedItem(name);
      if (errors[name]) input.setAttribute('aria-invalid', 'true');
      else input.removeAttribute('aria-invalid');
    }
    try {
      const result = calculate(values);
      const batchWeight = `${weight.format(values.bakedGrams)} g`;
      setText('cash', formatMoney(result.cash));
      setText('economicCost', formatMoney(result.economicCost));
      setText('packagedEquivalent', formatMoney(result.packagedEquivalent));
      setText('bakeryEquivalent', formatMoney(result.bakeryEquivalent));
      setText('homePerCookie', `${formatMoney(result.homePerCookie)} per ${values.count === 9 ? 'large' : 'medium'} cookie`);
      setText('homePer100g', `${formatMoney(result.homePer100g)} per 100 g`);
      setText('packagedSavings', savingsText(result.packagedSavings));
      setText('bakerySavings', savingsText(result.bakerySavings));
      setText('packagedBreakEvenHourly', breakEvenText(result.packagedBreakEvenHourly, values.activeMinutes));
      setText('bakeryBreakEvenHourly', breakEvenText(result.bakeryBreakEvenHourly, values.activeMinutes));
      const includeTimeAllowance = result.timeAllowance > 0;
      calculator.querySelector('[data-time-allowance-row]').hidden = !includeTimeAllowance;
      calculator.querySelector('[data-time-break-even]').hidden = !includeTimeAllowance;
      setText('comparisonWeight', `All ${includeTimeAllowance ? 'four' : 'three'} bars compare ${batchWeight} of cookies, on the same cost scale.`);
      const barValues = ['cash', 'economicCost', 'packagedEquivalent', 'bakeryEquivalent'];
      const scale = Math.max(...barValues.map(name => result[name]));
      for (const name of barValues) {
        const percentage = scale === 0 ? 0 : result[name] / scale * 100;
        calculator.querySelector(`[data-bar="${name}"]`).style.width = `${percentage}%`;
      }
      errorMessage.hidden = true;
      errorMessage.textContent = '';
      results.hidden = false;
      const timeSummary = includeTimeAllowance ? ` Optional time allowance ${formatMoney(result.timeAllowance)}; home total with that allowance ${formatMoney(result.economicCost)}.` : '';
      status.textContent = `Updated: ${batchWeight}, ${values.count === 9 ? '9 large' : '16 medium'} cookies. Home cash cost ${formatMoney(result.cash)}. Compared with packaged: ${savingsText(result.packagedSavings)}; bakery: ${savingsText(result.bakerySavings)}.${timeSummary}`;
    } catch (error) {
      results.hidden = true;
      errorMessage.hidden = false;
      errorMessage.textContent = `Please check the inputs. ${error.message}`;
      status.textContent = 'Results hidden until the inputs are valid.';
    }
  }

  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('input', update);
  form.addEventListener('change', update);
  form.addEventListener('reset', () => setTimeout(update, 0));
  form.querySelectorAll('fieldset').forEach(fieldset => { fieldset.disabled = false; });
  form.querySelector('button[type="reset"]').disabled = false;
  update();
}());
