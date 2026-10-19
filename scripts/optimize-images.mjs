#!/usr/bin/env node
/** Build-only image optimization and cache-busted asset links; source files stay intact. */
import { createHash } from 'node:crypto';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SITE = path.join(ROOT, '_site');
const CACHE = path.join(ROOT, '.cache', 'images');
const WIDTHS = [320, 640, 960, 1280];
const IMAGE_EXTENSION = /\.(?:jpe?g|png|webp|avif)$/i;
const ORIGIN = 'https://tradingkitchen.org/';
const QUALITY = 82;
const PIPELINE_VERSION = 'webp-v1';
const ATTRIBUTE = /([^\s=<>/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;

const hash = (content) => createHash('sha256').update(content).digest('hex');
const publicURL = (relative) => `/${relative.split(path.sep).join('/')}`;
const encodeAttribute = (value) => String(value).replace(/&(?!(?:#\d+|#x[\da-f]+|[a-z][\w]+);)/gi, '&amp;').replaceAll('"', '&quot;');

/** Only resolve site-local URLs and refuse traversal outside the staged output. */
export function localPath(value, base = 'index.html') {
  if (!value || value.startsWith('#') || value.startsWith('//')) return null;
  let url;
  try {
    url = new URL(value.replaceAll('&amp;', '&'), new URL(base, ORIGIN));
  } catch { return null; }
  if (url.origin !== new URL(ORIGIN).origin) return null;
  let relative;
  try { relative = decodeURIComponent(url.pathname).replace(/^\/+/, ''); } catch { return null; }
  const resolved = path.resolve(SITE, relative);
  if (resolved !== SITE && !resolved.startsWith(SITE + path.sep)) return null;
  return path.relative(SITE, resolved).split(path.sep).join('/');
}

function attributes(tag) {
  const result = new Map();
  const body = tag.replace(/^<\s*[a-z][\w:-]*\b/i, '').replace(/\/?\s*>$/, '');
  for (const match of body.matchAll(ATTRIBUTE)) {
    result.set(match[1].toLowerCase(), match[2] ?? match[3] ?? match[4] ?? null);
  }
  return result;
}

function serializeTag(name, attrs) {
  return `<${name}${Array.from(attrs, ([key, value]) => value === null ? ` ${key}` : ` ${key}="${encodeAttribute(value)}"`).join('')}>`;
}

export function imageSizes(page, classes = '') {
  if (/(?:^|\s)(?:print:block|recipe-print-image)(?:\s|$)/.test(classes)) return '120px';
  if (page === 'index.html') return '(min-width: 1600px) 227px, (min-width: 1536px) calc((100vw - 240px) / 6), (min-width: 1280px) calc((100vw - 184px) / 4), (min-width: 1024px) calc((100vw - 156px) / 3), (min-width: 768px) calc((100vw - 128px) / 2), calc(100vw - 52px)';
  return '(min-width: 1024px) 828px, (min-width: 768px) calc(100vw - 196px), calc(100vw - 76px)';
}

/** Rewrite image tags only. Script contents and structured data are intentionally untouched. */
export function rewriteHTMLImages(html, page, images) {
  return html.replace(/<script\b[^>]*>[\s\S]*?<\/script\s*>|<img\b[^>]*>/gi, (tag) => {
    if (!/^<img\b/i.test(tag)) return tag;
    const attrs = attributes(tag);
    const image = images[localPath(attrs.get('src'), page)];
    if (!image) return tag;
    const classes = attrs.get('class') || '';
    const printImage = /(?:^|\s)(?:print:block|recipe-print-image)(?:\s|$)/.test(classes);
    const preferredWidth = printImage || page === 'index.html' ? 640 : 960;
    const fallback = image.variants.find((variant) => variant.width >= preferredWidth) ?? image.variants.at(-1);
    attrs.set('src', publicURL(fallback.path));
    attrs.set('srcset', image.variants.map((variant) => `${publicURL(variant.path)} ${variant.width}w`).join(', '));
    attrs.set('sizes', imageSizes(page, classes));
    attrs.set('width', image.width);
    attrs.set('height', image.height);
    if (!attrs.has('decoding')) attrs.set('decoding', 'async');
    return serializeTag('img', attrs);
  });
}

export function rewriteCSSImages(css, base, images) {
  return css.replace(/url\(\s*(["']?)([^"')]+)\1\s*\)/gi, (original, quote, value) => {
    const image = images[localPath(value.trim(), base)];
    return image ? `url("${publicURL(image.variants.at(-1).path)}")` : original;
  });
}

function rewriteAssetLinks(html, page, assets) {
  return html.replace(/<(?:link|script)\b[^>]*>/gi, (tag) => {
    const name = /^<([a-z]+)/i.exec(tag)[1].toLowerCase();
    const attrs = attributes(tag);
    const attribute = name === 'link' ? 'href' : 'src';
    if (name === 'link' && attrs.get('rel') !== 'stylesheet') return tag;
    const asset = assets[localPath(attrs.get(attribute), page)];
    if (!asset) return tag;
    attrs.set(attribute, publicURL(asset.path));
    return serializeTag(name, attrs);
  });
}

async function filesUnder(directory) {
  const files = [];
  for (const entry of await fs.readdir(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`Refusing to process symlink: ${filename}`);
    if (entry.isDirectory()) files.push(...await filesUnder(filename));
    else if (entry.isFile()) files.push(filename);
  }
  return files.sort();
}

async function optimizeImage(relative) {
  const input = await fs.readFile(path.join(SITE, relative));
  const metadata = await sharp(input).metadata();
  const swapsAxes = metadata.orientation >= 5 && metadata.orientation <= 8;
  const width = swapsAxes ? metadata.height : metadata.width;
  const height = swapsAxes ? metadata.width : metadata.height;
  if (!width || !height) throw new Error(`Image has no dimensions: ${relative}`);
  // A smaller original contributes its native width once, never an enlarged variant.
  const widths = [...new Set(WIDTHS.map((target) => Math.min(target, width)))];
  const slug = path.basename(relative, path.extname(relative)).replace(/[^a-z0-9_-]/gi, '-');
  const variants = [];
  for (const target of widths) {
    const cacheKey = hash(Buffer.concat([input, Buffer.from(JSON.stringify({ target, quality: QUALITY, pipeline: PIPELINE_VERSION, versions: sharp.versions }))]));
    const cacheFile = path.join(CACHE, `${cacheKey}.webp`);
    let output;
    try { output = await fs.readFile(cacheFile); }
    catch (error) {
      if (error.code !== 'ENOENT') throw error;
      output = await sharp(input).rotate().resize({ width: target, withoutEnlargement: true }).webp({ quality: QUALITY, effort: 6 }).toBuffer();
      await fs.writeFile(cacheFile, output);
    }
    const outputMetadata = await sharp(output).metadata();
    const digest = hash(output).slice(0, 12);
    const destination = `assets/images/${slug}-${outputMetadata.width}.${digest}.webp`;
    await fs.writeFile(path.join(SITE, destination), output);
    variants.push({ path: destination, width: outputMetadata.width, height: outputMetadata.height, bytes: output.length });
  }
  return { width, height, bytes: input.length, variants };
}

export async function optimizeSite() {
  const initialFiles = await filesUnder(SITE);
  const pages = initialFiles.filter((filename) => filename.endsWith('.html'));
  const styles = initialFiles.filter((filename) => filename.endsWith('.css'));
  const scripts = initialFiles.filter((filename) => filename.endsWith('.js'));
  const referenced = new Set();
  const pageSources = new Map();
  const styleSources = new Map();
  function collect(value, base) {
    const relative = localPath(value, base);
    if (relative && IMAGE_EXTENSION.test(relative) && path.basename(relative) !== 'T.png') referenced.add(relative);
  }
  for (const filename of pages) {
    const relative = path.relative(SITE, filename).split(path.sep).join('/');
    const html = await fs.readFile(filename, 'utf8');
    pageSources.set(relative, html);
    for (const tag of html.matchAll(/<img\b[^>]*>/gi)) collect(attributes(tag[0]).get('src'), relative);
    for (const match of html.matchAll(/url\(\s*["']?([^"')]+)["']?\s*\)/gi)) collect(match[1], relative);
  }
  for (const filename of styles) {
    const relative = path.relative(SITE, filename).split(path.sep).join('/');
    const css = await fs.readFile(filename, 'utf8');
    styleSources.set(relative, css);
    for (const match of css.matchAll(/url\(\s*["']?([^"')]+)["']?\s*\)/gi)) collect(match[1], relative);
  }
  await fs.mkdir(path.join(SITE, 'assets', 'images'), { recursive: true });
  await fs.mkdir(CACHE, { recursive: true });
  const images = {};
  // Keep memory and CPU bounded on smaller CI runners.
  for (const relative of [...referenced].sort()) images[relative] = await optimizeImage(relative);
  const assets = {};
  for (const filename of [...styles, ...scripts].sort()) {
    const relative = path.relative(SITE, filename).split(path.sep).join('/');
    const content = styleSources.has(relative)
      ? Buffer.from(rewriteCSSImages(styleSources.get(relative), relative, images))
      : await fs.readFile(filename);
    const extension = path.extname(relative);
    const digest = hash(content).slice(0, 12);
    const destination = `${relative.slice(0, -extension.length)}.${digest}${extension}`;
    // Stable copies remain available to direct links; HTML uses immutable names.
    await fs.writeFile(filename, content);
    await fs.writeFile(path.join(SITE, destination), content);
    assets[relative] = { path: destination, bytes: content.length, hash: digest };
  }
  for (const [relative, html] of pageSources) {
    let output = rewriteHTMLImages(html, relative, images);
    output = output.replace(/<style\b[^>]*>[\s\S]*?<\/style\s*>/gi, (style) => rewriteCSSImages(style, relative, images));
    output = rewriteAssetLinks(output, relative, assets);
    await fs.writeFile(path.join(SITE, relative), output);
  }
  const manifest = { version: 1, widths: WIDTHS, format: 'webp', quality: QUALITY, images, assets };
  await fs.writeFile(path.join(SITE, 'assets', 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
  const originals = Object.values(images).reduce((sum, image) => sum + image.bytes, 0);
  const largest = Object.values(images).reduce((sum, image) => sum + image.variants.at(-1).bytes, 0);
  const count = Object.values(images).reduce((sum, image) => sum + image.variants.length, 0);
  console.log(`Optimized ${referenced.size} images into ${count} responsive WebP files (${Math.round(100 * (1 - largest / originals))}% smaller at largest size); hashed ${Object.keys(assets).length} CSS/JS assets.`);
  return manifest;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  optimizeSite().catch((error) => { console.error(error); process.exitCode = 1; });
}
