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
npm run build
npm run preview
```

Open <http://localhost:8000>. Press Ctrl+C to stop the preview server. After editing the source, run `npm run build` again and refresh the browser.

`npm run build` compiles the stylesheet, prepares the publishable site in `_site/`, and validates the result. `npm run validate` checks an existing build. `_site/` is generated output; edit the source files instead.

## Edit the site

The current site uses static HTML. Recipe pages and their images live at the repository root; shared assets and build tools are under `assets/` and `scripts/`. Keep existing recipe filenames so saved links continue to work.

When adding a recipe, use an existing recipe as a starting point. Update its title, description, canonical URL, and Recipe structured data to match the visible content; add its homepage card, image, and `sitemap.xml` entry. Run the build, then review the recipe on desktop and mobile before publishing. The next requested recipe is **chocolate chip cookies**; its content and any photo are awaiting the owner.

## Publish and operate

The GitHub Pages workflow builds and deploys changes pushed to `main`. See [the deployment guide](docs/DEPLOYMENT.md) for DNS, HTTPS, analytics, Search Console, and release checks.

The new domain's DNS and certificate setup are pending completion. Google Analytics retains the existing property and measurement ID. Mailing-list delivery is still being investigated; no successful subscription delivery is assumed.

See [the roadmap](docs/ROADMAP.md) for the mission and longer-term plans for a CMS, ingredient and equipment search, meal pricing, APIs, and community contributions.
