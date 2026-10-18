import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

// Run the actual browser script with deterministic network and timer doubles.
// These tests never submit an address to Formspree or send analytics events.
const source = readFileSync(new URL('../assets/newsletter.js', import.meta.url), 'utf8');

function setup({ valid = true, analytics = true, fetchResult = async () => ({ ok: true }) } = {}) {
  const requests = [];
  const events = [];
  const destinations = [];
  const timers = new Map();
  const attributes = new Map();
  const classes = new Set(['hidden']);
  const button = { textContent: 'Request an invite', disabled: false };
  const status = {
    textContent: '',
    classList: { add: value => classes.add(value), remove: value => classes.delete(value) },
  };
  let handler;
  let nextTimer = 0;
  let prevented = 0;
  const form = {
    action: 'https://formspree.io/f/test-only',
    fields: [['email', 'test@example.invalid']],
    querySelector: selector => selector === 'button[type="submit"]' ? button : null,
    reportValidity: () => valid,
    addEventListener: (name, callback) => { if (name === 'submit') handler = callback; },
    setAttribute: (name, value) => attributes.set(name, value),
    removeAttribute: name => attributes.delete(name),
  };
  const window = { location: { assign: value => destinations.push(value) } };
  if (analytics) window.gtag = (...args) => events.push(JSON.parse(JSON.stringify(args)));
  vm.runInNewContext(source, {
    document: { getElementById: id => ({ 'invite-form': form, 'form-status': status })[id] },
    window,
    AbortController,
    FormData: class {
      constructor(target) { this.fields = [...target.fields]; }
    },
    fetch: (url, options) => {
      requests.push({ url, options });
      return fetchResult(url, options);
    },
    setTimeout: (callback, delay) => {
      const id = ++nextTimer;
      timers.set(id, { callback, delay });
      return id;
    },
    clearTimeout: id => timers.delete(id),
  }, { filename: 'assets/newsletter.js' });
  return {
    requests, events, destinations, timers, attributes, classes, button, status,
    submit: () => handler({ preventDefault: () => { prevented++; } }),
    get prevented() { return prevented; },
  };
}

function assertReady(context) {
  assert.equal(context.button.disabled, false);
  assert.equal(context.button.textContent, 'Request an invite');
  assert.equal(context.attributes.has('aria-busy'), false);
  assert.equal(context.timers.size, 0);
}

function assertNoSuccess(context) {
  assert.deepEqual(context.events, []);
  assert.deepEqual(context.destinations, []);
}

test('invalid input is stopped before a request is made', async () => {
  const context = setup({ valid: false });
  await context.submit();
  assert.equal(context.prevented, 1);
  assert.equal(context.requests.length, 0);
  assertReady(context);
  assertNoSuccess(context);
});

test('successful response sends the form once, records a lead without PII, and navigates', async () => {
  const context = setup();
  await context.submit();
  assert.equal(context.requests.length, 1);
  const { url, options } = context.requests[0];
  assert.equal(url, 'https://formspree.io/f/test-only');
  assert.equal(options.method, 'POST');
  assert.equal(options.headers.Accept, 'application/json');
  assert.deepEqual(Array.from(options.body.fields, field => Array.from(field)), [['email', 'test@example.invalid']]);
  assert.deepEqual(context.events, [['event', 'generate_lead', { form_name: 'trading_post_invite' }]]);
  assert.deepEqual(context.destinations, ['thanks.html']);
  assertReady(context);
});

test('pending submissions block duplicate requests and do not report premature success', async () => {
  let resolveResponse;
  const context = setup({ fetchResult: () => new Promise(resolve => { resolveResponse = resolve; }) });
  const first = context.submit();
  assert.equal(context.button.disabled, true);
  assert.equal(context.attributes.get('aria-busy'), 'true');
  assert.equal(context.button.textContent, 'Sending…');
  await context.submit();
  assert.equal(context.requests.length, 1);
  assertNoSuccess(context);
  resolveResponse({ ok: true });
  await first;
  assert.equal(context.events.length, 1);
  assertReady(context);
});

test('HTTP errors stay on the form, show the service error, and allow a retry', async () => {
  let attempts = 0;
  const context = setup({ fetchResult: async () => ++attempts === 1
    ? { ok: false, json: async () => ({ errors: [{ message: 'Please use a valid email address.' }] }) }
    : { ok: true } });
  await context.submit();
  assert.equal(context.status.textContent, 'Please use a valid email address.');
  assert.equal(context.classes.has('hidden'), false);
  assertNoSuccess(context);
  assertReady(context);
  await context.submit();
  assert.equal(context.requests.length, 2);
  assert.equal(context.events.length, 1);
  assert.deepEqual(context.destinations, ['thanks.html']);
  assertReady(context);
});

test('non-JSON error responses use a useful fallback without recording a lead', async () => {
  const context = setup({ fetchResult: async () => ({
    ok: false,
    json: async () => { throw new SyntaxError('Unexpected token <'); },
  }) });
  await context.submit();
  assert.equal(context.status.textContent, 'Your request could not be sent. Please try again later.');
  assert.equal(context.classes.has('hidden'), false);
  assertNoSuccess(context);
  assertReady(context);
});

test('network failure shows a connection message without recording a lead', async () => {
  const context = setup({ fetchResult: async () => { throw new TypeError('Failed to fetch'); } });
  await context.submit();
  assert.match(context.status.textContent, /We could not connect/);
  assert.equal(context.classes.has('hidden'), false);
  assertNoSuccess(context);
  assertReady(context);
});

test('the 15-second timeout aborts the request and restores the form', async () => {
  const context = setup({ fetchResult: (_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(Object.assign(new Error('Aborted'), { name: 'AbortError' })), { once: true });
  }) });
  const pending = context.submit();
  const timer = [...context.timers.values()][0];
  assert.equal(timer.delay, 15000);
  timer.callback();
  await pending;
  assert.equal(context.requests[0].options.signal.aborted, true);
  assert.match(context.status.textContent, /request timed out/);
  assert.equal(context.classes.has('hidden'), false);
  assertNoSuccess(context);
  assertReady(context);
});

test('signup still succeeds when analytics is unavailable', async () => {
  const context = setup({ analytics: false });
  await context.submit();
  assert.deepEqual(context.events, []);
  assert.deepEqual(context.destinations, ['thanks.html']);
  assertReady(context);
});
