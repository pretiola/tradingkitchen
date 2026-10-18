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
| Signup endpoint under investigation | `https://formspree.io/f/mjglgbao` |

## Current migration status

- Source is being prepared for the repository and GitHub Pages deployment.
- Dynadot changes are pending the owner's signed-in session. Public DNS initially returned the parking address `185.53.179.128` for both the apex and `www`.
- GitHub domain ownership verification and HTTPS depend on the DNS changes below. A valid certificate for the new domain has not yet been confirmed.
- The GA4 property and web stream have been renamed, and stream `10012221772` now uses `https://tradingkitchen.org`. Retain the measurement ID above. Live event receipt still requires verification after DNS is connected.
- Search Console DNS verification is pending publication of its TXT record.
- Formspree delivery and subscriber storage have not been verified. Do not treat a form submission or success page alone as proof that a subscriber was saved.
- The chocolate chip cookie recipe is awaiting content from the owner.

Update these statuses with observed results when the migration is completed.

## Build and deployment

Requirements: Node.js 22 or later and Python 3. CI uses Node.js 24.

```sh
npm ci
npm run build
npm run preview
```

Run `npm test` for signup success, failure, timeout, and duplicate-submission checks. Preview at <http://localhost:8000>. To validate an existing build, run `npm run validate`. The publish directory is `_site/`; source files, build scripts, and operator documentation should not be deployed as page content. The generated `assets/tailwind.css` is ignored by Git and rebuilt when publishing.

In repository **Settings → Pages**, select **GitHub Actions** as the build source. The workflow builds the site and deploys on pushes to `main`; it can also be started manually from the Actions tab. Pull requests run the build without deploying. Confirm the Pages deployment job succeeds before testing the public site.

Set the repository custom domain to **`tradingkitchen.org`**. GitHub Actions deployments use the Pages setting for the custom domain; a `CNAME` file alone does not configure an Actions deployment.

The compatible Tailwind 3.4.19 build dependency currently has upstream npm audit findings for denial-of-service risks in pattern/selector parsing. It runs during the build; the published site includes compiled CSS and no npm runtime packages. A broader Tailwind upgrade remains maintenance work.

## Dynadot DNS

First claim the domain under **pretiola organization Settings → Pages**, and configure the repository custom domain before pointing web traffic at GitHub. The GitHub ownership TXT record below was generated for this organization.

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

Use a 300-second TTL while migrating if available. Replace the parking address and remove conflicting web records or wildcard parking. Preserve any unrelated mail or verification records discovered in the account. The public baseline had no MX or CAA records.

The `www` CNAME target is the organization hostname, with no protocol or repository path. GitHub Pages redirects `www` to the apex when both are correctly configured. Leave both TXT records in place after verification.

Optional IPv6 support can be added with all four apex AAAA records: `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, and `2606:50c0:8003::153`. Retain the A records when adding IPv6.

After public DNS resolves to the new values, complete **Verify** in the organization's Pages domain settings and in Google Search Console.

References: [GitHub custom-domain DNS](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site), [GitHub ownership verification](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages), [Dynadot DNS settings](https://www.dynadot.com/help/question/set-up-DNS).

## HTTPS and release checks

GitHub requests and installs a Let's Encrypt certificate automatically after its DNS check succeeds. In repository **Settings → Pages**, wait for certificate provisioning, then enable **Enforce HTTPS**. No certificate purchase or private-key upload is required.

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

In **Admin → Data collection and modification → Data streams**, edit the website stream name and URL to Trading Kitchen and `https://tradingkitchen.org`. Review any old-domain settings, then visit the deployed site and confirm a visit in the Realtime report. Stream configuration and receiving a live event are separate checks.

Reference: [Google's instructions for editing a web stream](https://support.google.com/analytics/answer/9304776?hl=en).

## Google Search Console

Create or select the **Domain property** `tradingkitchen.org` in [Search Console](https://search.google.com/search-console), publish the TXT record above, and complete verification. The Domain property includes HTTP, HTTPS, the apex, and subdomains.

After the site is live, submit `https://tradingkitchen.org/sitemap.xml`. Inspect the homepage and a representative recipe URL, and check for manual actions or indexing exclusions. Verification and a submitted sitemap do not guarantee immediate indexing.

The previous domain currently uses GoDaddy nameservers and returned a GitHub Pages 404 during the initial inspection. If the owner still controls it, configure permanent, path-preserving redirects from `trading.kitchen` to `tradingkitchen.org`, with working HTTPS on the old host. This requires separate old-domain handling because one GitHub Pages site cannot use two unrelated apex domains. Once redirects work and both properties are verified, use the old property's **Change of Address** tool.

References: [Domain properties](https://support.google.com/webmasters/answer/34592?hl=en), [ownership verification](https://support.google.com/webmasters/answer/9008080?hl=en), [Google's migration guidance](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes).

## Mailing-list verification

The signup handler now restores the submit button on errors (including non-JSON responses), times out stalled requests, prevents duplicate submissions, and reports a `generate_lead` event only after a successful response. Email addresses are never added to that event. Production Analytics runs only on `tradingkitchen.org` and `www.tradingkitchen.org`, not local previews.

Inspect the existing Formspree form in the owner's account before deciding whether to keep it or replace it. Confirm the form is active, its destination is verified, submissions are stored, and the intended recipient can access them. Check spam handling and the confirmation flow.

A working Formspree submission endpoint is not by itself a newsletter service. If a replacement is needed, choose a service with subscriber storage, email confirmation, and unsubscribe handling, then connect its real signup form. Verify delivery with an owner-approved test address before claiming the mailing list is operational.
