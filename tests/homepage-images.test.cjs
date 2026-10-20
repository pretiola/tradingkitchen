const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../assets/homepage-images.js'), 'utf8');

function browser({ observer = true, readyState = 'complete', tops = [100, 1200, 1600, 2000] } = {}) {
  const listeners = {};
  const writes = [];
  const frames = [];
  let callback;
  let options;
  const observed = new Set();
  const images = tops.map((top, index) => {
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
    notify() { callback(); },
    flush() { const pending = frames.splice(0); pending.forEach(handler => handler()); }
  };
}

test('visible images load with exactly one next image, without cascading requests', () => {
  const state = browser();
  assert.equal(state.writes.length, 0, 'wait for the initial animation frame');
  assert.equal(state.options.rootMargin, '0px');
  state.flush();
  assert.equal(state.images[0].attrs.get('src'), '/image-0.webp');
  assert.equal(state.images[1].attrs.get('src'), '/image-1.webp');
  assert.equal(state.images[2].attrs.get('src'), 'data:image/svg+xml,placeholder');
  assert.deepEqual(state.writes.map(write => write.name), ['srcset', 'src', 'srcset', 'src'], 'select responsive candidates before fallback sources');
  assert.equal(state.observed.has(state.images[1]), true, 'keep observing the speculative image');
  state.notify();
  state.flush();
  assert.equal(state.writes.length, 4, 'another scan must not walk through the remaining images');
});

test('entering an already-preloaded image advances lookahead by one', () => {
  const state = browser();
  state.flush();
  state.images[1].top = 700;
  state.notify();
  state.flush();
  assert.equal(state.images[2].attrs.get('src'), '/image-2.webp');
  assert.equal(state.images[3].attrs.get('src'), 'data:image/svg+xml,placeholder');
  assert.equal(state.writes.filter(write => write.index === 1).length, 2, 'do not request a loaded image twice');
});

test('a multi-column visible row gets only one extra image', () => {
  const state = browser({ tops: [100, 100, 100, 100, 1200, 1200, 1600] });
  state.flush();
  assert.equal(state.images.filter(image => !image.attrs.has('data-src')).length, 5);
  assert.equal(state.images[5].attrs.get('src'), 'data:image/svg+xml,placeholder');
});

test('lookahead follows viewport position when no card is visible or the page starts scrolled', () => {
  const aboveGrid = browser({ tops: [1000, 1200, 1600] });
  aboveGrid.flush();
  assert.equal(aboveGrid.images.filter(image => !image.attrs.has('data-src')).length, 1);
  const scrolled = browser({ tops: [-1200, -800, 100, 1200, 1600] });
  scrolled.flush();
  assert.deepEqual(scrolled.writes.filter(write => write.name === 'src').map(write => write.index), [2, 3]);
});

test('browsers without IntersectionObserver also keep one-image lookahead', () => {
  const state = browser({ observer: false });
  state.flush();
  assert.equal(state.images[1].attrs.get('src'), '/image-1.webp');
  assert.equal(state.images[2].attrs.get('src'), 'data:image/svg+xml,placeholder');
  state.listeners.scroll();
  state.flush();
  assert.equal(state.images[2].attrs.get('src'), 'data:image/svg+xml,placeholder');
  state.images[1].top = 700;
  state.listeners.resize();
  state.flush();
  assert.equal(state.images[2].attrs.get('src'), '/image-2.webp');
  assert.equal(state.images[3].attrs.get('src'), 'data:image/svg+xml,placeholder');
  state.images[2].top = 700;
  state.listeners.scroll();
  state.flush();
  assert.equal(state.images[3].attrs.get('src'), '/image-3.webp');
  assert.equal(state.listeners.scroll, undefined);
});

test('printing requests remaining images so printed cards are complete', () => {
  const state = browser();
  state.listeners.beforeprint();
  assert.deepEqual(state.images.map(image => image.attrs.get('src')), ['/image-0.webp', '/image-1.webp', '/image-2.webp', '/image-3.webp']);
  assert.equal(state.observed.size, 0);
});

test('a script loaded in the head waits until images exist', () => {
  const state = browser({ readyState: 'loading' });
  assert.equal(state.observed.size, 0);
  state.listeners.DOMContentLoaded();
  assert.equal(state.observed.size, 4);
});
