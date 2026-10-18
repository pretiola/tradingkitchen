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

`npm test` runs the full build and static validation. It checks the site's markup and signup configuration, not live subscriber storage or email delivery. `npm run build` performs the same build: it compiles the stylesheet, prepares the publishable site in `_site/`, and validates the result. `npm run validate` checks an existing build. `_site/` is generated output; edit the source files instead.

## Edit the site

The current site uses static HTML. Recipe pages and their images live at the repository root; shared assets and build tools are under `assets/` and `scripts/`. Keep existing recipe filenames so saved links continue to work.

When adding a recipe, use an existing recipe as a starting point. Update its title, description, canonical URL, and Recipe structured data to match the visible content; add its homepage card, image, and `sitemap.xml` entry. Run the build, then review the recipe on desktop and mobile before publishing. The next requested recipe is **chocolate chip cookies**; its content and any photo are awaiting the owner.

## Publish and operate

The GitHub Pages workflow builds and deploys changes pushed to `main`. See [the deployment guide](docs/DEPLOYMENT.md) for DNS, HTTPS, analytics, Search Console, and release checks.

The site is deployed at [tradingkitchen.org](https://tradingkitchen.org), including the Buttondown signup integration in release [`a000c09`](https://github.com/pretiola/tradingkitchen/commit/a000c09). Public DNS resolves to GitHub Pages, the certificate covers the apex and `www`, and HTTPS enforcement is enabled. The live homepage has been checked in a browser; all 14 sitemap pages and the initial launch's 11 assets returned successfully and matched that build. The current build has 31 public files, including 10 assets after removal of the old signup script. HTTP and `www` redirect to the HTTPS apex while preserving paths and query strings.

Google Analytics retains the existing property and measurement ID, with the property and stream updated for the new domain; live event receipt is confirmed. The Search Console Domain property is verified and linked to the Analytics web stream, its sitemap reports success with 14 discovered pages, and the homepage indexing request was accepted. The Chipped Beef page passed its live indexing test with valid Recipe and Breadcrumb structured data. Search Console reported no manual actions or security issues. Actual indexing is still pending.

The signup form now posts directly to [Trading Kitchen on Buttondown](https://buttondown.com/tradingkitchen), replacing Formspree. The owner account is verified and uses the free plan for up to 100 subscribers, with no credit card. An owner-approved test confirmed live signup, subscriber storage, and delivery of confirmation and welcome emails to Gmail's inbox; one confirmed subscriber remains. The subscriber portal has an Unsubscribe control, which was inspected but not exercised. Before the first newsletter broadcast, the owner needs to supply the intended public postal contact address; that field is currently blank. No email campaigns have been sent.

See [the roadmap](docs/ROADMAP.md) for the mission and longer-term plans for a CMS, ingredient and equipment search, meal pricing, APIs, and community contributions.
