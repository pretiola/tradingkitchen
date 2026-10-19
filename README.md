# Trading Kitchen

Trading Kitchen shares practical, affordable recipes and the knowledge to make more of the resources you have.

- Website: [tradingkitchen.org](https://tradingkitchen.org)
- Repository: [pretiola/tradingkitchen](https://github.com/pretiola/tradingkitchen)
- Previous domain: `trading.kitchen`
- Hosting: GitHub Pages, with Dynadot DNS for the new domain

## Run locally

Install Node.js 22 or later and Python 3, then run:

```sh
npm ci
npm test
npm run preview
```

Open <http://localhost:8000>. Press Ctrl+C to stop the preview server. After editing the source, run `npm run build` again and refresh the browser.

`npm test` runs the automated tests, then the full build and static validation. `npm run build` compiles Tailwind, stages public files, generates responsive WebP images and content-hashed CSS/JavaScript, and validates `_site/`. `npm run validate` checks an existing build. Edit source files rather than `_site/`; generated output and the local image cache are ignored by Git. Static checks cover markup and signup configuration; live subscriber storage and email delivery require separate verification.

## Edit the site

The current site uses static HTML. Recipe pages and their images live at the repository root; shared assets and build tools are under `assets/` and `scripts/`. Keep existing recipe filenames so saved links continue to work.

All recipes use the same `recipe-page-container`, `recipe-card`, and `recipe-title` classes. Their width, spacing, typography, and single-column print layout live in `assets/site.css`. Printed recipes omit the screen card, story, and economic lesson, and keep the ingredients, instructions, recipe notes, and a small photo. Do not add page-local width or print overrides; the build rejects recipe-local styles. Homepage and cookie lesson details have separate stylesheets, `assets/pantry.css` and `assets/cookie-lesson.css`.

Put a replacement photo at its existing source path and rebuild. Sharp generates appropriately sized WebP variants without upscaling, adds intrinsic dimensions and responsive `srcset`/`sizes`, and fingerprints filenames so changed photos and styles do not reuse stale cached versions. Original image URLs remain available for shared links, social previews, and structured data. See `_site/assets/manifest.json` for generated assets. The builder follows the shared-assets and responsive-image approach in [pretiola-website-template](https://github.com/pretiola/pretiola-website-template), while keeping this site on static GitHub Pages.

When adding a recipe, use an existing recipe as a starting point. Update its title, description, canonical URL, and Recipe structured data to match the visible content; add its homepage card, image, and `sitemap.xml` entry. Run the build, then review the recipe on desktop and mobile before publishing. The owner’s **chocolate chip cookies** recipe is in `chocolate_chip_cookies.html`, with the supplied photo edited with steam, a warm autumn kitchen setting, baking ingredients, and a Magic Baking Powder tin. The recipe began with the supplied document; the owner later reduced the chocolate chips to ⅓ cup. The owner later corrected the yield to 9 large or 16 medium cookies and the bake time to 9–14 minutes, depending on size; portioning appears before the optional 20-minute chill so the dough balls are ready to chill.

## Publish and operate

The GitHub Pages workflow builds and deploys changes pushed to `main`. See [the deployment guide](docs/DEPLOYMENT.md) for DNS, HTTPS, analytics, Search Console, and release checks.

The site is deployed at [tradingkitchen.org](https://tradingkitchen.org), including the Buttondown signup integration in release [`a000c09`](https://github.com/pretiola/tradingkitchen/commit/a000c09). Public DNS resolves to GitHub Pages, the certificate covers the apex and `www`, and HTTPS enforcement is enabled. The live homepage has been checked in a browser; all 14 sitemap pages and the initial launch's 11 assets returned successfully and matched that build. The site has 17 HTML pages, 14 illustrated recipes, and 15 sitemap URLs; builds also include responsive image variants and versioned styles/scripts. All 14 recipes have local food images; the eight remaining placeholder cards have been replaced with illustrations, and their recipe pages now include images and Recipe structured data. The Search Console counts below record the initial launch check. HTTP and `www` redirect to the HTTPS apex while preserving paths and query strings.

Google Analytics retains the existing property and measurement ID, with the property and stream updated for the new domain; live event receipt is confirmed. The Search Console Domain property is verified and linked to the Analytics web stream, its sitemap reports success with 14 discovered pages, and the homepage indexing request was accepted. The Chipped Beef page passed its live indexing test with valid Recipe and Breadcrumb structured data. Search Console reported no manual actions or security issues. Actual indexing is still pending.

The signup form now posts directly to [Trading Kitchen on Buttondown](https://buttondown.com/tradingkitchen), replacing Formspree. The owner account is verified and uses the free plan for up to 100 subscribers, with no credit card. An owner-approved test confirmed live signup, subscriber storage, and delivery of confirmation and welcome emails to Gmail's inbox; one confirmed subscriber remains. The subscriber portal has an Unsubscribe control, which was inspected but not exercised. Before the first newsletter broadcast, the owner needs to supply the intended public postal contact address; that field is currently blank. No email campaigns have been sent.

See [the roadmap](docs/ROADMAP.md) for the mission and longer-term plans for a CMS, ingredient and equipment search, meal pricing, APIs, and community contributions.

The chocolate chip cookie page includes a sourced Economic Lesson on pantry unit pricing, household production, portions, and family learning. Its calculator uses explicitly illustrative CAD costs and equal finished weights, with family time kept outside cash costs by default. Readers can explore an optional time tradeoff. `npm test` includes arithmetic and input-validation tests for this tool before building the site.
