# Deployment and operations

Migration notes updated **October 18, 2026**. This document records public configuration identifiers only. Passwords, API secrets, recovery codes, and account credentials must stay out of the repository.

## Service map

| Service | Configuration |
| --- | --- |
| Source | [pretiola/tradingkitchen](https://github.com/pretiola/tradingkitchen) |
| Hosting | GitHub Pages, deployed by `.github/workflows/pages.yml` |
| Canonical URL | `https://tradingkitchen.org` |
| Alternate host | `www.tradingkitchen.org`, redirected to the canonical host |
| New-domain DNS | Dynadot |
| Previous domain | `trading.kitchen` |
| Analytics account | `135348446` |
| GA4 property | `469214836` — `Trading Kitchen — tradingkitchen.org` |
| GA4 measurement ID | `G-NMY1V4BQVB` |
| Mailing-list service | Buttondown, free plan for up to 100 subscribers; no credit card |
| Newsletter | [Trading Kitchen](https://buttondown.com/tradingkitchen), username `tradingkitchen` |
| Signup endpoint | `https://buttondown.com/api/emails/embed-subscribe/tradingkitchen` |

## Current migration status

- GitHub Pages has deployed the Buttondown integration in `main` commit [`a000c09`](https://github.com/pretiola/tradingkitchen/commit/a000c09). [Workflow run `39168500481`](https://github.com/pretiola/tradingkitchen/actions/runs/39168500481) succeeded.
- Dynadot DNS was saved with the records below and a 300-second TTL. Public DNS checks now resolve to GitHub Pages, and GitHub organization domain ownership is verified. The original parking address was `185.53.179.128` for both the apex and `www`.
- GitHub approved a certificate covering `tradingkitchen.org` and `www.tradingkitchen.org`, expiring **January 16, 2027**, and **Enforce HTTPS** is enabled. Checks with normal TLS certificate validation returned HTTPS apex `200`, HTTPS `www` `301` to the HTTPS apex, and `301` redirects for both HTTP hosts. Redirects preserve paths and query strings. The live homepage loaded in a browser; at initial launch, all 14 sitemap pages and 11 assets returned `200` and matched that build byte for byte. The illustrated recipe collection now has 17 HTML pages and 42 public files, including 20 assets. All 14 recipes have local food images.
- The GA4 property and web stream have been renamed, and stream `10012221772` now uses `https://tradingkitchen.org`. Retain the measurement ID above. Realtime confirmed live event receipt for the new homepage and Chipped Beef page. Its observed 22 page-view events and eight users include migration testing and must not be reported as organic traffic.
- The Search Console Domain property is DNS-verified and linked to Analytics web stream `10012221772`. `https://tradingkitchen.org/sitemap.xml` reports **Success** with **14 discovered pages**. The homepage indexing request was accepted. The Chipped Beef page's live test passed as eligible for indexing with valid Recipe and Breadcrumb structured data; optional metadata warnings remain. Manual Actions and Security Issues both report **No issues detected**. Actual indexing is not yet confirmed.
- The Buttondown account is configured with verified owner email and Google sign-in. The deployed form uses Buttondown's native POST endpoint; Formspree and its JavaScript handler and tests have been removed. `npm test` passed the build and static validation of 16 pages and 31 public files. A live owner-approved Gmail test verified signup storage, confirmation email delivery, activation, and welcome email delivery. One confirmed subscriber remains. The subscriber portal's Unsubscribe control was inspected but not exercised.
- The newsletter's public postal contact address is blank. The owner needs to supply the intended address before the first broadcast. No email campaigns have been sent.
- The owner’s chocolate chip cookie recipe is implemented in `chocolate_chip_cookies.html`, with the supplied photo edited with steam, a warm autumn kitchen setting, baking ingredients, and a Magic Baking Powder tin. The new page is first in the homepage recipe list and included in the sitemap, which now contains 15 URLs. Search Console’s 14-page count above is the observed initial launch result; discovery of the new page has not yet been confirmed.

- The eight remaining placeholder recipe images have been replaced with local illustrations for Zaprezna Soup, Potato Soup, Tuna Fish Stew, Baked Beans, Milk Potatoes, Ash Cakes, Rice Pudding, and Hard Time Pudding. Each page includes a hero image, a print image, social image metadata, and Recipe structured data matching its visible ingredients and instructions. Existing recipe text is preserved; malformed Rice Pudding list/image tags were repaired. No timing, yield, nutrition, ratings, or product claims were added.

- The Hoover Stew image was remade in a cottage kitchen scene with an enameled pot and serving bowl on a wooden table. Chipped Beef on Toast, Beef and Noodles, and Banana Bread were also remade in natural color. Their original image URLs are retained. The remaining grayscale/sepia image rules were removed from the homepage and those three recipe pages, along with the homepage’s redundant per-image overrides; all recipe images now display their natural colors while the parchment background and vignette remain. Image descriptions were updated for the new scenes, with no changes to recipe text, structured recipe content, or file counts.

Update these statuses with observed results as indexing and the remaining pre-broadcast setup are completed.

## Build and deployment

Requirements: Node.js 22 or later and Python 3. CI uses Node.js 24.

```sh
npm ci
npm test
npm run preview
```

`npm test` runs the cookie calculator’s arithmetic and validation tests, then `npm run build`, including CSS compilation, staging, and full static validation. The current source includes 17 HTML pages and stages 42 public files, including 20 assets and the Buttondown signup configuration. Automated checks do not submit a real address or verify subscriber storage, confirmation email delivery, or unsubscribe handling; the separate live signup verification is recorded below. The previous Formspree handler and its mocked tests were removed when the form switched to native Buttondown submission. Preview at <http://localhost:8000>. To validate an existing build, run `npm run validate`. The publish directory is `_site/`; source files, build scripts, and operator documentation should not be deployed as page content. The generated `assets/tailwind.css` is ignored by Git and rebuilt when publishing.

In repository **Settings → Pages**, use **GitHub Actions** as the build source. The workflow builds and validates the site, then deploys on pushes to `main`; it can also be started manually from the Actions tab. Pull requests run the build and validation without deploying. Confirm the Pages deployment job succeeds before testing each release on the public site.

Set the repository custom domain to **`tradingkitchen.org`**. GitHub Actions deployments use the Pages setting for the custom domain; a `CNAME` file alone does not configure an Actions deployment.

The compatible Tailwind 3.4.19 build dependency currently has upstream npm audit findings for denial-of-service risks in pattern/selector parsing. It runs during the build; the published site includes compiled CSS and no npm runtime packages. A broader Tailwind upgrade remains maintenance work.

## Dynadot DNS

The domain is verified under **pretiola organization Settings → Pages**, and the repository custom domain is configured. For a future migration, claim the domain and configure the repository custom domain before pointing web traffic at GitHub. The GitHub ownership TXT record below was generated for this organization.

In Dynadot, open **My Domains → Manage Domains → tradingkitchen.org → DNS Settings**, then choose **Dynadot DNS**. The apex (`@`) records belong in **Domain Record**; do not enter `@` as a subdomain name.

| Section / name | Type | Value |
| --- | --- | --- |
| Domain Record (`@`) | A | `185.199.108.153` |
| Domain Record (`@`) | A | `185.199.109.153` |
| Domain Record (`@`) | A | `185.199.110.153` |
| Domain Record (`@`) | A | `185.199.111.153` |
| Subdomain `www` | CNAME | `pretiola.github.io` |
| Subdomain `_github-pages-challenge-pretiola` | TXT | `cbc49ad5a06646d5732cb59b4fb16d` |
| Domain Record (`@`) | TXT | `google-site-verification=toN04mS7MGzwgGSHhWT2ceFRJTqCHMJpmLS1qmBpbps` |

These records were saved with a 300-second TTL. When making future changes, remove conflicting web records or wildcard parking and preserve unrelated mail or verification records. The public baseline had no MX or CAA records.

The `www` CNAME target is the organization hostname, with no protocol or repository path. GitHub Pages redirects `www` to the apex when both are correctly configured. Leave both TXT records in place after verification.

Optional IPv6 support can be added with all four apex AAAA records: `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, and `2606:50c0:8003::153`. Retain the A records when adding IPv6.

Both the organization's Pages domain verification and Google Search Console Domain property verification are complete. Keep their TXT records in place so ownership can continue to be checked.

References: [GitHub custom-domain DNS](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site), [GitHub ownership verification](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages), [Dynadot DNS settings](https://www.dynadot.com/help/question/set-up-DNS).

## HTTPS and release checks

GitHub requests and installs a Let's Encrypt certificate automatically after its DNS check succeeds. In repository **Settings → Pages**, wait for certificate provisioning, then enable **Enforce HTTPS**. No certificate purchase or private-key upload is required.

The initial certificate is approved for both hosts and expires January 16, 2027; HTTPS enforcement is enabled. GitHub manages certificate renewal. The initial status above records the completed connection, page, asset, and redirect checks; use the following list for future releases.

Confirm these results using normal certificate validation:

- `https://tradingkitchen.org/` serves the homepage successfully.
- `https://www.tradingkitchen.org/` redirects to the apex and has a valid certificate.
- Both HTTP hosts redirect to HTTPS.
- A recipe URL loads directly, including its image and stylesheet.
- `robots.txt`, `sitemap.xml`, and recipe canonical URLs reference `https://tradingkitchen.org`.
- The deployed site has no mixed HTTP assets or browser console errors.

DNS and certificate provisioning can take time. If provisioning stalls after DNS is correct, review conflicting A/AAAA/CNAME records and the Pages DNS check. If a CAA policy is introduced, it must allow `letsencrypt.org`.

References: [GitHub HTTPS](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https), [custom-domain troubleshooting](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages).

## Google Analytics

Keep the existing [GA4 property](https://analytics.google.com/analytics/web/#/a135348446p469214836/reports/intelligenthome) and tag `G-NMY1V4BQVB` to retain historical continuity. A domain change does not require a new property.

The property and web stream have been renamed, and stream `10012221772` now uses `https://tradingkitchen.org`. Realtime confirmed receipt of events for the new homepage and Chipped Beef page. The observed snapshot showed 22 page-view events and eight users during migration testing; this verifies collection, not organic audience growth.

Review the configuration under **Admin → Data collection and modification → Data streams** and check for remaining old-domain settings. For future releases, visit the deployed site and confirm a visit in the Realtime report. Stream configuration and receiving a live event are separate checks.

The Search Console Domain property `tradingkitchen.org` is linked to the Trading Kitchen Analytics web stream `10012221772`; the configuration screen confirmed **Link created**. The former Formspree `generate_lead` event was removed with its JavaScript handler; the native Buttondown form does not currently report a confirmed-subscription event to Analytics. Production Analytics runs only on `tradingkitchen.org` and `www.tradingkitchen.org`, not local previews.

Reference: [Google's instructions for editing a web stream](https://support.google.com/analytics/answer/9304776?hl=en).

## Google Search Console

The **Domain property** `tradingkitchen.org` in [Search Console](https://search.google.com/search-console) is verified using the TXT record above. The Domain property includes HTTP, HTTPS, the apex, and subdomains.

`https://tradingkitchen.org/sitemap.xml` reports **Success** with **14 discovered pages**, and the homepage indexing request was accepted. The live test for `https://tradingkitchen.org/chipped_beef.html` passed as eligible for indexing and found valid Recipe and Breadcrumb structured data. Noncritical warnings concern optional recipe metadata; missing values have not been invented to suppress those warnings. Manual Actions and Security Issues both report **No issues detected**. Actual indexing is not yet confirmed. Check indexing status and exclusions as Google processes the site. Verification, a successful sitemap submission, and an accepted indexing request do not guarantee immediate indexing.

The previous domain currently uses GoDaddy nameservers and returned a GitHub Pages 404 during the initial inspection. If the owner still controls it, configure permanent, path-preserving redirects from `trading.kitchen` to `tradingkitchen.org`, with working HTTPS on the old host. This requires separate old-domain handling because one GitHub Pages site cannot use two unrelated apex domains. Once redirects work and both properties are verified, use the old property's **Change of Address** tool.

References: [Domain properties](https://support.google.com/webmasters/answer/34592?hl=en), [ownership verification](https://support.google.com/webmasters/answer/9008080?hl=en), [Google's migration guidance](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes).

## Mailing-list configuration and verification

Buttondown replaces Formspree. The account username is `tradingkitchen`, the public newsletter is <https://buttondown.com/tradingkitchen>, and the website form submits directly to `https://buttondown.com/api/emails/embed-subscribe/tradingkitchen` using native HTML POST. No AJAX handler is involved. The previous `assets/newsletter.js`, its mocked tests, and its `generate_lead` event were removed.

The owner approved the account, signed in with Google, and verified the owner email. The newsletter name and author are **Trading Kitchen**; its description reflects the brand and links to `https://tradingkitchen.org`, and the brand tint is `#1f2937`. The selected plan is free for up to 100 subscribers, with no credit card.

The owner-approved live Gmail signup test passed against the deployed form in release `a000c09`:

- Empty email submission was blocked by the form's validation.
- The submitted address appeared in Buttondown as **Unactivated**, with the embedded form as its source and `https://tradingkitchen.org` as its referrer.
- The confirmation email from `tradingkitchen@buttondown.email` arrived in Gmail's inbox.
- Following the approved confirmation link changed the subscriber to **Regular**. Subscriber activity recorded receipt of the confirmation email and activation, and the welcome email also arrived in Gmail's inbox.
- One confirmed subscriber remains. No private subscriber address or identifier is stored in this repository.
- The subscriber portal has an **Unsubscribe** control. Its presence was inspected without using it, so the unsubscribe action itself is not verified.

This verifies the signup and confirmation flow with one approved address. Static build checks alone do not establish these outcomes.

The public postal contact address is currently blank. Before sending the first newsletter broadcast, the owner needs to provide the intended public postal contact address. No email campaigns have been sent.

The four color-remake image URLs include a content-hash query parameter in page, social, and structured-data references. This avoids showing cached copies of the former photos immediately after deployment; the original image filenames remain available.

The cookie recipe now makes 9 large or 16 medium cookies and bakes for 9–14 minutes depending on size, as corrected by the owner after the original document was supplied. Its Economic Lesson includes a sourced pantry ledger, fair weight-based price comparison, optional time-tradeoff calculator, family-learning activities, portion graphics, and careful nutrition context. Default calculator time allowance is zero: bonding and practical learning remain benefits outside the cash comparison. Prices and 550 g baked batch weight are explicitly illustrative; nutrition superiority over packaged cookies is not claimed.

The cookie recipe uses ⅓ cup chocolate chips. The lesson has one title, matching unnumbered navigation and section headings, and shorter copy. Cost examples and calculator defaults reflect approximately 57 g chips, C$4.05 ingredients, C$4.40 cash cost, and an assumed 550 g cooled batch.
