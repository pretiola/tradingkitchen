const { test } = require('node:test');
const assert = require('node:assert/strict');

const pipeline = import('../scripts/optimize-images.mjs');
const image = {
  width: 1000, height: 750, bytes: 250000,
  variants: [320, 640, 960, 1000].map((width) => ({ path: `assets/images/cookies-${width}.abcdef012345.webp`, width, height: Math.round(width * .75), bytes: width * 20 })),
};

test('recipe image transforms preserve alt, classes and structured data while adding dimensions and responsive sources', async () => {
  const { rewriteHTMLImages } = await pipeline;
  const schema = '<script type="application/ld+json">{"image":"https://tradingkitchen.org/cookies.jpg"}</script>';
  const original = `${schema}<img src="cookies.jpg?v=old" alt="Cookies &amp; milk" class="recipe-hero" loading="lazy"><img src="cookies.jpg" alt="Cookies" class="recipe-print-image">`;
  const result = rewriteHTMLImages(original, 'cookies.html', { 'cookies.jpg': image });
  assert.ok(result.startsWith(schema), 'SEO image URL must remain stable');
  assert.match(result, /alt="Cookies &amp; milk" class="recipe-hero" loading="lazy"/);
  assert.doesNotMatch(result, /&amp;amp;/);
  assert.match(result, /src="\/assets\/images\/cookies-960\.abcdef012345\.webp"/);
  assert.match(result, /width="1000" height="750"/);
  assert.match(result, /srcset="[^"]*1000w"/);
  assert.match(result, /class="recipe-print-image"[^>]*sizes="120px"/);
});

test('local URLs resolve from their page or stylesheet and remote assets remain unchanged', async () => {
  const { localPath, rewriteHTMLImages, rewriteCSSImages } = await pipeline;
  assert.equal(localPath('../cookies.jpg?v=old', 'assets/pantry.css'), 'cookies.jpg');
  assert.equal(localPath('https://tradingkitchen.org/cookies.jpg'), 'cookies.jpg');
  assert.equal(localPath('https://example.org/cookies.jpg'), null);
  assert.equal(localPath('data:image/png;base64,AA=='), null);
  const external = '<img src="https://example.org/cookies.jpg" alt="External">';
  assert.equal(rewriteHTMLImages(external, 'cookies.html', { 'cookies.jpg': image }), external);
  assert.equal(rewriteCSSImages(".hero { background: url('../cookies.jpg'); }", 'assets/pantry.css', { 'cookies.jpg': image }), '.hero { background: url("/assets/images/cookies-1000.abcdef012345.webp"); }');
});

test('marked homepage images defer responsive requests and retain an optimized no-script fallback', async () => {
  const { rewriteHTMLImages, imageSizes } = await pipeline;
  const schema = '<script type="application/ld+json">{"image":"https://tradingkitchen.org/cookies.jpg"}</script>';
  const original = `${schema}<img src="cookies.jpg" alt="Cookies &amp; milk" class="recipe-card" loading="lazy" data-defer-image>`;
  const result = rewriteHTMLImages(original, 'index.html', { 'cookies.jpg': image });
  assert.ok(result.startsWith(schema), 'structured data keeps its public image URL');
  const [deferred, fallback] = result.match(/<img\b[^>]*>/g);
  assert.match(deferred, /\ssrc="data:image\/svg\+xml,/);
  assert.doesNotMatch(deferred, /\ssrcset=/, 'the browser must not discover a responsive request before scrolling');
  assert.match(deferred, /\sdata-src="\/assets\/images\/cookies-640\.abcdef012345\.webp"/);
  assert.match(deferred, /\sdata-srcset="[^\"]*320w[^\"]*1000w"/);
  assert.match(deferred, /\sdata-defer-image(?:\s|>)/);
  assert.match(deferred, /\sloading="eager"/);
  assert.match(deferred, /\swidth="1000" height="750"/);
  assert.ok(deferred.includes(`sizes="${imageSizes('index.html', 'recipe-card')}"`));
  assert.match(deferred, /alt="Cookies &amp; milk" class="recipe-card"/);
  assert.ok(result.includes(`<noscript>${fallback}</noscript>`));
  assert.match(fallback, /\ssrc="\/assets\/images\/cookies-640\.abcdef012345\.webp"/);
  assert.match(fallback, /\ssrcset="[^\"]*320w[^\"]*1000w"/);
  assert.match(fallback, /\sloading="lazy"/);
  assert.match(fallback, /\swidth="1000" height="750"/);
  assert.match(fallback, /alt="Cookies &amp; milk" class="recipe-card"/);
  assert.doesNotMatch(fallback, /\sdata-/, 'no observer attributes belong to the no-script fallback');
  assert.ok(fallback.includes(`sizes="${imageSizes('index.html', 'recipe-card')}"`));
  assert.equal(rewriteHTMLImages(result, 'index.html', { 'cookies.jpg': image }), result, 'a second pass must not nest or duplicate the fallback');
});

test('unmarked homepage images and images on recipe pages retain normal responsive loading', async () => {
  const { rewriteHTMLImages } = await pipeline;
  for (const [page, marker] of [['index.html', ''], ['cookies.html', ' data-defer-image']]) {
    const result = rewriteHTMLImages(`<img src="cookies.jpg" alt="Cookies" loading="lazy"${marker}>`, page, { 'cookies.jpg': image });
    assert.match(result, /\ssrc="\/assets\/images\/cookies-/);
    assert.match(result, /\ssrcset="[^\"]*1000w"/);
    assert.match(result, /\sloading="lazy"/);
    assert.doesNotMatch(result, /<noscript>|\sdata-src=/);
  }
});
