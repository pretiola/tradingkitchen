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
