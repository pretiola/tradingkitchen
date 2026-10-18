# Trading Kitchen roadmap

## Mission

Provide the knowledge and tools to maximize individual freedom and improve quality of life for everyone. The current site shares static recipe pages; the longer-term vision connects recipes, available ingredients, equipment, and cost so people can make better use of their resources.

## Current refresh

- Publish the site from `pretiola/tradingkitchen` using GitHub Pages.
- Complete the rebrand from `trading.kitchen` to `tradingkitchen.org`, including Dynadot DNS, the `www` redirect, and HTTPS.
- Provide a simple local build and preview workflow through npm and Python's web server.
- Update analytics and establish the new Search Console property and sitemap.
- Verify the existing mailing-list form or connect a replacement that reliably stores subscribers and delivers confirmations.
- Add the owner’s chocolate chip cookie recipe and supplied photo (implemented in `chocolate_chip_cookies.html`).

See [deployment notes](DEPLOYMENT.md) for the current operational status and remaining account-dependent steps.

## Recipe publishing and discovery

- Move to a CMS that makes maintenance and recipe publishing easier.
- Replace repetitive headers, footers, and navigation with shared templates.
- Support homepage cards with images and categories.
- Store structured ingredient lists so visitors can browse recipes by ingredients such as beef.
- Record the equipment needed for each recipe, including pots, whisks, knives, and other tools.

## Meal planning and prices

- Connect each recipe ingredient to product and price data feeds.
- Calculate the cost of a meal per adult or child portion using current ingredient prices.
- Help visitors choose meals based on their available ingredients, equipment, and budget.

## APIs and assisted publishing

- Provide an API for bulk recipe additions and retrieving price feeds.
- Document the API and build a user interface for its workflows.
- Explore an integration with OpenAI or similar tools to help people work with the recipe and pricing interfaces.

## Community

- Let visitors submit comments and photos, with moderator approval before publication.
- Allow visitors to submit their own Depression-era recipes and related cooking knowledge for review.

## Context and reference pages

Explore dynamic reference pages based on Grokipedia content, with clear attribution and a direct link to the source article. For example, the **United Fruit Company** reference in the banana bread recipe could link to a Trading Kitchen page based on the corresponding [Grokipedia API entry](https://grokipedia-api.com/page/United_Fruit_Company).

This preserves the original roadmap idea; the API integration and reference-page system are future work.
