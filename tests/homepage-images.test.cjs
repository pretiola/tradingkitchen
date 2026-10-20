const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../assets/homepage-images.js'), 'utf8');

function browser({ observer = true, readyState = 'complete' } = {}) {
  const listeners = {};
  const writes = [];
  const frames = [];
  let callback;
  let options;
  const observed = new Set();
  const images = [100, 1200].map((top, index) => {
    const attrs = new Map([
      ['src', 'data:image/svg+xml,placeholder'], ['data-defer-image', ''],
      ['data-src', `/image-${index}.webp`], ['data-srcset', `/image-${index}-320.webp 320w, /image-${index}.webp 640w`]
    ]);
    return {
      top, attrs,
      getAttribute(name) { return attrs.get(name); },
      setAttribute(name, value) { attrs.set(name, value); writes.push({ index, name, value }); },
      removeAttribute(name) { attrs.delete(name); },
      getBoundingClientRect() { return { top: this.top, bottom: this.top + 192, left: 0, right: 300 }; }
    };
  });
  const document = {
    readyState,
    querySelectorAll() { return images; },
    addEventListener(name, handler) { listeners[name] = handler; }
  };
  const window = {
    innerHeight: 800, innerWidth: 1200,
    addEventListener(name, handler) { listeners[name] = handler; },
    removeEventListener(name) { delete listeners[name]; },
    requestAnimationFrame(handler) { frames.push(handler); return frames.length; }
  };
  if (observer) window.IntersectionObserver = class {
    constructor(handler, config) { callback = handler; options = config; }
    observe(image) { observed.add(image); }
    unobserve(image) { observed.delete(image); }
    disconnect() { observed.clear(); }
  };
  vm.runInNewContext(source, { window, document, Set });
  return {
    images, writes, listeners, observed,
    get options() { return options; },
    enter(index, ratio = 0.5) { callback([{ target: images[index], isIntersecting: ratio > 0, intersectionRatio: ratio }]); },
    flush() { const pending = frames.splice(0); pending.forEach(handler => handler()); }
  };
}

test('offscreen images keep inert sources until intersecting and load only once', () => {
  const state = browser();
  assert.equal(state.writes.length, 0, 'observing alone must not assign a network source');
  assert.equal(state.options.rootMargin, '0px', 'do not prefetch beyond the viewport');
  state.enter(1, 0);
  assert.equal(state.writes.length, 0);
  state.enter(0);
  assert.equal(state.images[0].attrs.get('src'), '/image-0.webp');
  assert.equal(state.images[1].attrs.get('src'), 'data:image/svg+xml,placeholder');
  assert.deepEqual(state.writes.map(write => write.name), ['srcset', 'src'], 'select responsive source before fallback to avoid a duplicate request');
  assert.equal(state.observed.has(state.images[0]), false);
  assert.equal(state.images[0].attrs.has('data-src'), false);
  state.enter(0);
  assert.equal(state.writes.length, 2);
});

test('browsers without IntersectionObserver still wait for the viewport', () => {
  const state = browser({ observer: false });
  state.flush();
  assert.equal(state.images[0].attrs.get('src'), '/image-0.webp');
  assert.equal(state.images[1].attrs.get('src'), 'data:image/svg+xml,placeholder');
  state.listeners.scroll();
  state.flush();
  assert.equal(state.images[1].attrs.get('src'), 'data:image/svg+xml,placeholder');
  state.images[1].top = 700;
  state.listeners.resize();
  state.flush();
  assert.equal(state.images[1].attrs.get('src'), '/image-1.webp');
  assert.equal(state.listeners.scroll, undefined);
});

test('printing requests remaining images so printed cards are complete', () => {
  const state = browser();
  state.listeners.beforeprint();
  assert.deepEqual(state.images.map(image => image.attrs.get('src')), ['/image-0.webp', '/image-1.webp']);
  assert.equal(state.observed.size, 0);
});

test('a script loaded in the head waits until images exist', () => {
  const state = browser({ readyState: 'loading' });
  assert.equal(state.observed.size, 0);
  state.listeners.DOMContentLoaded();
  assert.equal(state.observed.size, 2);
});
