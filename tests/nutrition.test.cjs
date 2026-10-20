'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { initNutrition } = require('../assets/nutrition.js');

function fixture(ids = ['medium', 'large']) {
  const panels = ids.map((id, i) => ({ dataset: { portion: id }, hidden: i !== 0 }));
  const handlers = {};
  const select = {
    options: ids.map(id => ({ value: id, textContent: `1 ${id} cookie` })),
    value: ids[0], hidden: true, disabled: true,
    addEventListener(event, callback) { handlers[event] = callback; }
  };
  const controls = { hidden: true }, status = { textContent: '' };
  const section = {
    querySelector(selector) { return { '[data-nutrition-select]': select, '.nutrition-controls': controls, '[data-nutrition-status]': status }[selector]; },
    querySelectorAll() { return panels; }
  };
  return { root: { querySelectorAll: () => [section] }, panels, select, controls, status, handlers };
}

test('portion selection shows exactly one matching card and announces it', () => {
  const f = fixture(); initNutrition(f.root);
  assert.equal(f.controls.hidden, false);
  assert.equal(f.select.disabled, false);
  f.select.value = 'large'; f.handlers.change();
  assert.deepEqual(f.panels.map(p => p.hidden), [true, false]);
  assert.match(f.status.textContent, /1 large cookie/);
  f.select.value = 'invalid'; f.handlers.change();
  assert.equal(f.select.value, 'large');
  assert.deepEqual(f.panels.map(p => p.hidden), [true, false]);
});

test('one-serving-size recipes retain their static card without a redundant selector', () => {
  const f = fixture(['bowl']); initNutrition(f.root);
  assert.equal(f.controls.hidden, true);
  assert.equal(f.select.disabled, true);
  assert.equal(f.panels[0].hidden, false);
});

test('initialization is idempotent and preserves a selected portion', () => {
  const f = fixture(); initNutrition(f.root);
  const handler = f.handlers.change;
  f.select.value = 'large'; handler(); initNutrition(f.root);
  assert.equal(f.handlers.change, handler);
  assert.deepEqual(f.panels.map(p => p.hidden), [true, false]);
});
