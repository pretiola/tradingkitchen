#!/usr/bin/env python3
"""Validate the built site without making network requests or running browser scripts."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from recipe_metadata import RecipeDocument, VOID_TAGS, validate_recipe_metadata
from nutrition import validate_built_nutrition

DOMAIN = "tradingkitchen.org"
ORIGIN = f"https://{DOMAIN}"
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
errors = []


def check(condition, message):
    if not condition:
        errors.append(message)


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.name = path.relative_to(SITE).as_posix()
        self.url = urljoin(ORIGIN + "/", self.name if self.name != "index.html" else "")
        self.tags = []
        self.context_tags = []
        self.element_stack = []
        self.comments = []
        self.ids = set()
        self.scripts = []
        self.styles = []
        self.forms = []
        self.current_form = None
        self.active = None
        self.buffer = []
        source = path.read_text(encoding="utf-8")
        self.recipe_document = RecipeDocument(source)
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.tags.append((tag, attrs))
        self.context_tags.append((tag, attrs, tuple(self.element_stack)))
        if tag not in VOID_TAGS:
            self.element_stack.append((tag, attrs))
        if tag == "form":
            self.current_form = {"attrs": attrs, "fields": []}
            self.forms.append(self.current_form)
        elif self.current_form is not None and tag in {"input", "button", "select", "textarea"}:
            self.current_form["fields"].append(attrs)
        if attrs.get("id"):
            check(attrs["id"] not in self.ids, f"{self.name}: duplicate id {attrs['id']}")
            self.ids.add(attrs["id"])
        if tag in {"script", "style"}:
            self.active = (tag, attrs)
            self.buffer = []
        if attrs.get("style"):
            self.styles.append(attrs["style"])

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self.active:
            self.buffer.append(data)

    def handle_comment(self, data):
        self.comments.append(data)

    def handle_endtag(self, tag):
        for index in range(len(self.element_stack) - 1, -1, -1):
            if self.element_stack[index][0] == tag:
                del self.element_stack[index:]
                break
        if tag == "form":
            self.current_form = None
        if self.active and self.active[0] == tag:
            if tag == "script":
                self.scripts.append((self.active[1], "".join(self.buffer)))
            else:
                self.styles.append("".join(self.buffer))
            self.active = None
            self.buffer = []

    def attributes(self, tag):
        return [attrs for element, attrs in self.tags if element == tag]

    def meta(self, name):
        return [attrs.get("content", "") for attrs in self.attributes("meta") if attrs.get("name", "").lower() == name]

    def text_for(self, attributes):
        return next((element.text for element in self.recipe_document.elements if element.attrs == attributes), "")

    @property
    def noindex(self):
        return any("noindex" in value.lower() for value in self.meta("robots"))


def local_target(value, base_url, label):
    try:
        url = urlsplit(urljoin(base_url, value))
    except ValueError as error:
        errors.append(f"{label}: invalid URL {value!r}: {error}")
        return None
    if url.scheme not in {"http", "https"} or url.hostname not in {DOMAIN, f"www.{DOMAIN}"}:
        return None
    check(url.scheme == "https", f"{label}: insecure internal URL {value}")
    path = unquote(url.path)
    target = (SITE / path.lstrip("/")).resolve()
    if not target.is_relative_to(SITE):
        errors.append(f"{label}: path escapes public site: {value}")
        return None
    if path.endswith("/"):
        target = target / "index.html"
    check(target.is_file(), f"{label}: missing local target {value}")
    return (target, unquote(url.fragment))


def check_javascript(source, label, module=False):
    result = subprocess.run(
        ["node", "--check", "--input-type=module" if module else "--input-type=commonjs"],
        input=source, capture_output=True, text=True, check=False,
    )
    check(result.returncode == 0, f"{label}: JavaScript syntax error\n{result.stderr.strip()}")


def schema_objects(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from schema_objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from schema_objects(item)


def privacy_errors(page):
    """Catch missing consent controls and accidental pre-consent dependencies."""
    problems = []

    def require(condition, message):
        if not condition:
            problems.append(f"{page.name}: {message}")

    def local_asset(value, pattern):
        try:
            target = urlsplit(urljoin(page.url, value))
            return target.scheme == "https" and target.netloc == DOMAIN and bool(re.fullmatch(pattern, target.path))
        except ValueError:
            return False

    def inside(ancestors, tag, element_id=None):
        return any(name == tag and (element_id is None or attrs.get("id") == element_id) for name, attrs in ancestors)

    def labelled(attrs):
        return bool(attrs.get("aria-label", "").strip() or page.text_for(attrs).strip())

    analytics = [attrs for attrs in page.attributes("script") if local_asset(attrs.get("src", ""), r"/assets/analytics(?:\.[0-9a-f]+)?\.js")]
    require(len(analytics) == 1 and "defer" in analytics[0], "expected one deferred first-party analytics consent script")
    dialogs = [attrs for attrs in page.attributes("dialog") if attrs.get("id") == "privacy-dialog"]
    require(len(dialogs) == 1, "expected one privacy dialog")
    if len(dialogs) == 1:
        for attribute in ("aria-labelledby", "aria-describedby"):
            referenced_ids = dialogs[0].get(attribute, "").split()
            require(bool(referenced_ids) and all(value in page.ids for value in referenced_ids), f"privacy dialog needs valid {attribute}")
    choices = [(tag, attrs) for tag, attrs, ancestors in page.context_tags if "data-consent-choice" in attrs and inside(ancestors, "dialog", "privacy-dialog")]
    all_choices = [attrs for _, attrs in page.tags if "data-consent-choice" in attrs]
    require(len(all_choices) == 3 and sorted(attrs["data-consent-choice"] for _, attrs in choices) == ["advertising", "analytics", "rejected"], "privacy dialog needs exactly one reject, analytics-only and advertising choice")
    require(all(tag == "button" and attrs.get("type") == "button" and "disabled" not in attrs and labelled(attrs) for tag, attrs in choices), "privacy choices must be labelled, enabled buttons")
    openers = [(tag, attrs) for tag, attrs, ancestors in page.context_tags if "data-privacy-open" in attrs and inside(ancestors, "footer")]
    require(len(openers) == 1, "footer needs one privacy choices button")
    if len(openers) == 1:
        tag, attrs = openers[0]
        require(tag == "button" and attrs.get("type") == "button" and attrs.get("aria-controls") == "privacy-dialog" and attrs.get("aria-haspopup") == "dialog" and "disabled" not in attrs and labelled(attrs), "footer privacy choices button must be accessible and target the dialog")
    require(any(tag == "a" and local_asset(attrs.get("href", ""), r"/privacy\.html") and labelled(attrs) and inside(ancestors, "footer") for tag, attrs, ancestors in page.context_tags), "footer needs a link to our privacy policy")
    require(not any(re.search(r"\binclude\s*:", comment, re.IGNORECASE) for comment in page.comments), "unexpanded shared include in built HTML")
    fonts = [attrs for attrs in page.attributes("link") if attrs.get("rel") == "stylesheet" and local_asset(attrs.get("href", ""), r"/assets/fonts(?:\.[0-9a-f]+)?\.css")]
    require(len(fonts) == 1, "expected one first-party font stylesheet")
    for tag, attrs in page.tags:
        for attribute in ("href", "src"):
            try:
                host = urlsplit(urljoin(page.url, attrs.get(attribute, ""))).hostname or ""
            except ValueError:
                continue
            require(host not in {"fonts.googleapis.com", "fonts.gstatic.com"}, "external Google Fonts request bypasses privacy choices")
            if tag == "script" and attribute == "src":
                require(not re.search(r"(?:^|\.)(?:googletagmanager\.com|google-analytics\.com|doubleclick\.net|googleadservices\.com)$", host), "third-party Google tracking must load through the consent script")
    for attrs, source in page.scripts:
        if not attrs.get("src") and attrs.get("type") != "application/ld+json":
            require(not re.search(r"googletagmanager\.com|google-analytics\.com|\b(?:gtag|ga)\s*\(", source), "inline Google tracking bypasses the shared consent script")
    return problems


def check_newsletter(page):
    forms = [form for form in page.forms if form["attrs"].get("id") == "newsletter-form"]
    check(len(forms) == 1, "index.html: expected one mailing-list signup form")
    if len(forms) != 1:
        return
    form = forms[0]
    attrs = form["attrs"]
    check(attrs.get("action") == "https://buttondown.com/api/emails/embed-subscribe/tradingkitchen", "index.html: mailing-list form must use the verified Buttondown endpoint")
    check(attrs.get("method", "").lower() == "post", "index.html: mailing-list signup must POST to Buttondown")
    check("novalidate" not in attrs and "onsubmit" not in attrs, "index.html: preserve native signup validation and submission")
    emails = [field for field in form["fields"] if field.get("name") == "email"]
    check(len(emails) == 1, "index.html: expected one subscriber email input")
    if len(emails) == 1:
        email = emails[0]
        check(email.get("type") == "email" and "required" in email, "index.html: signup requires a valid email address")
        check(bool(email.get("id")) and any(label.get("for") == email.get("id") for label in page.attributes("label")), "index.html: signup email needs an associated label")
        description_ids = email.get("aria-describedby", "").split()
        check(bool(description_ids) and all(value in page.ids for value in description_ids), "index.html: signup email needs accessible confirmation instructions")
    check(any(field.get("type") == "hidden" and field.get("name") == "embed" and field.get("value") == "1" for field in form["fields"]), "index.html: missing Buttondown embed field")
    check(not any(field.get("formaction") or "formnovalidate" in field for field in form["fields"]), "index.html: signup fields must preserve the provider endpoint and validation")
    submit_buttons = [field for field in form["fields"] if field.get("type") == "submit"]
    check(len(submit_buttons) == 1 and page.text_for(submit_buttons[0]) == "Join the email list", "index.html: signup action must clearly say Join the email list")
    check(any(element.tag == "p" and "Email list powered by" in element.text and "Buttondown" in element.text for element in page.recipe_document.elements), "index.html: identify Buttondown as the email provider")
    check(any(attrs.get("href") == "/privacy.html" and page.text_for(attrs) == "Our privacy policy" for attrs in page.attributes("a")), "index.html: newsletter needs our own privacy policy link")
    check(not any(attrs.get("href", "").startswith("https://buttondown.com/legal/privacy") for attrs in page.attributes("a")), "index.html: link to our policy; provider details belong in privacy.html")


def check_recipe_layout(page):
    """Keep recipes on the shared layout and require complete responsive images."""
    if "recipe-section" not in page.ids:
        return
    def with_class(tag, name):
        return [attrs for attrs in page.attributes(tag) if name in attrs.get("class", "").split()]

    check(len(with_class("body", "recipe-page")) == 1, f"{page.name}: missing shared recipe body")
    containers = with_class("main", "recipe-page-container")
    check(len(containers) == 1 and containers[0].get("class") == "recipe-page-container", f"{page.name}: recipe width must use the shared container")
    cards = with_class("article", "recipe-card")
    check(len(cards) == 1 and cards[0].get("class") == "recipe-card", f"{page.name}: recipe card must use shared screen/print styles")
    check(len(with_class("h1", "recipe-title")) == 1, f"{page.name}: missing shared recipe title")
    check(len(with_class("img", "recipe-hero")) == 1, f"{page.name}: expected one recipe hero")
    check(len(with_class("img", "recipe-print-image")) == 1, f"{page.name}: expected one print thumbnail")
    check(len(with_class("footer", "recipe-print-footer")) == 1, f"{page.name}: expected one shared print footer")
    check(not any(element == "style" for element, _ in page.tags), f"{page.name}: use shared stylesheets instead of page-local layout/print rules")
    check(any(re.search(r"/site(?:\.[0-9a-f]+)?\.css$", urlsplit(attrs.get("href", "")).path) for attrs in page.attributes("link")), f"{page.name}: missing shared site stylesheet")


def check_srcset(value, page, require_local=False):
    for candidate in value.split(","):
        fields = candidate.strip().split()
        check(len(fields) == 2 and bool(re.fullmatch(r"[1-9][0-9]*w", fields[-1])), f"{page.name}: invalid width-based srcset candidate {candidate}")
        if fields:
            target = local_target(fields[0], page.url, page.name)
            if require_local:
                check(target is not None, f"{page.name}: deferred image candidates must be local assets")


def check_images(page):
    """Validate responsive images and the homepage's scroll-triggered contract."""
    visible = []
    deferred = []
    fallbacks = []
    for tag, attrs, ancestors in page.context_tags:
        if tag != "img":
            continue
        in_noscript = any(name == "noscript" for name, _ in ancestors)
        is_deferred = "data-defer-image" in attrs
        check(bool(attrs.get("alt")), f"{page.name}: image needs descriptive alt text")
        check(all(attrs.get(size, "").isdigit() and int(attrs[size]) > 0 for size in ("width", "height")), f"{page.name}: image needs intrinsic width and height")
        responsive = attrs.get("data-srcset", "") if is_deferred else attrs.get("srcset", "")
        check(bool(responsive) and bool(attrs.get("sizes")), f"{page.name}: image needs responsive {'data-srcset' if is_deferred else 'srcset'} and sizes")
        if responsive:
            check_srcset(responsive, page, require_local=is_deferred)
        if in_noscript:
            fallbacks.append(attrs)
        else:
            visible.append(attrs)
        if is_deferred:
            deferred.append(attrs)
            check(page.name == "index.html" and not in_noscript, f"{page.name}: only visible homepage images may use data-defer-image")
            check(attrs.get("src", "").startswith("data:image/"), f"{page.name}: deferred image src must be an inline image placeholder")
            check("srcset" not in attrs, f"{page.name}: deferred image must not expose a preloaded srcset")
            check(attrs.get("loading") == "eager", f"{page.name}: observer-triggered images must use loading=eager")
            source = attrs.get("data-src", "")
            check(bool(source), f"{page.name}: deferred image needs data-src")
            if source:
                check(local_target(source, page.url, page.name) is not None, f"{page.name}: deferred image data-src must be a local asset")
        else:
            check(bool(attrs.get("src")), f"{page.name}: image needs a source")
            if attrs.get("src"):
                check(not attrs["src"].startswith("http://"), f"{page.name}: insecure src: {attrs['src']}")
                local_target(attrs["src"], page.url, page.name)
            check("data-src" not in attrs and "data-srcset" not in attrs, f"{page.name}: deferred image sources require data-defer-image")

    loaders = []
    for attrs in page.attributes("script"):
        try:
            target = urlsplit(urljoin(page.url, attrs.get("src", "")))
        except ValueError:
            continue  # The general URL check reports malformed script sources.
        if re.fullmatch(r"/assets/homepage-images(?:\.[0-9a-f]+)?\.js", target.path):
            loaders.append((attrs, target))
    if page.name == "index.html":
        check(all("data-defer-image" in attrs for attrs in visible), "index.html: all visible homepage images must defer their requests")
        check(len(loaders) == 1 and "defer" in loaders[0][0] and loaders[0][1].scheme == "https" and loaders[0][1].netloc == DOMAIN,
              "index.html: expected one deferred first-party homepage image loader")
        if len(loaders) == 1:
            local_target(loaders[0][0]["src"], page.url, page.name)
        check(len(fallbacks) == len(deferred), "index.html: every deferred image needs one noscript fallback")
        if len(fallbacks) == len(deferred):
            for image, fallback in zip(deferred, fallbacks):
                check(image.get("data-src") == fallback.get("src") and image.get("data-srcset") == fallback.get("srcset") and
                      all(image.get(attribute) == fallback.get(attribute) for attribute in ("alt", "width", "height", "sizes")),
                      "index.html: noscript image must preserve its deferred image sources, dimensions and description")
    else:
        check(not loaders, f"{page.name}: homepage image loader belongs only on index.html")


def main():
    check(SITE.is_dir(), f"Missing build output: {SITE}; run npm run build first")
    if not SITE.is_dir():
        return
    pages = [Page(path) for path in sorted(SITE.rglob("*.html"))]
    check(bool(pages), "No HTML pages were built")
    page_by_path = {page.path: page for page in pages}
    for page in pages:
        errors.extend(privacy_errors(page))
        errors.extend(validate_built_nutrition(page, Path(__file__).resolve().parent.parent))
        if page.name == "index.html":
            check_newsletter(page)
        check_recipe_layout(page)
        check_images(page)
        html = page.attributes("html")
        check(len(html) == 1 and bool(html[0].get("lang")), f"{page.name}: missing document language")
        check(bool(page.attributes("title")), f"{page.name}: missing title")
        if not page.noindex:
            canonical = [attrs.get("href") for attrs in page.attributes("link") if attrs.get("rel") == "canonical"]
            check(canonical == [page.url], f"{page.name}: expected one canonical URL: {page.url}")
            check(any(page.meta("description")), f"{page.name}: missing description")
            check(any(attrs.get("type") == "application/ld+json" for attrs, _ in page.scripts), f"{page.name}: missing structured data")
        check(not any("cdn.tailwindcss.com" in attrs.get("src", "") for attrs in page.attributes("script")), f"{page.name}: development Tailwind CDN is still enabled")
        for tag, attrs in page.tags:
            if tag != "img" and attrs.get("srcset"):
                check_srcset(attrs["srcset"], page)
            for attribute in ("href", "src", "poster", "action"):
                if not attrs.get(attribute):
                    continue
                if tag == "img" and attribute == "src":
                    continue  # Includes noscript and deferred sources checked above.
                value = attrs[attribute]
                if attribute in {"src", "poster", "action"}:
                    check(not value.startswith("http://"), f"{page.name}: insecure {attribute}: {value}")
                target = local_target(value, page.url, page.name)
                if target and target[1] and target[0] in page_by_path:
                    check(target[1] in page_by_path[target[0]].ids, f"{page.name}: missing fragment target {value}")
            for attribute, value in attrs.items():
                if attribute.startswith("on") and value:
                    check_javascript(f"function handler(event) {{\n{value}\n}}", f"{page.name}: {attribute}")
        recipe_count = 0
        for attrs, source in page.scripts:
            if attrs.get("type") == "application/ld+json":
                try:
                    data = json.loads(source)
                    for item in schema_objects(data):
                        types = item.get("@type", [])
                        if types == "Recipe" or isinstance(types, list) and "Recipe" in types:
                            recipe_count += 1
                            errors.extend(f"{page.name}: {error}" for error in validate_recipe_metadata(item, page.recipe_document, page.url))
                except (ValueError, TypeError) as error:
                    errors.append(f"{page.name}: invalid JSON-LD: {error}")
            elif not attrs.get("src") and attrs.get("type", "") in {"", "text/javascript", "module"}:
                check_javascript(source, page.name, attrs.get("type") == "module")
        if "recipe-section" in page.ids:
            check(recipe_count == 1, f"{page.name}: expected one Recipe structured-data object")
        for stylesheet in page.styles:
            for value in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", stylesheet):
                local_target(value.strip(), page.url, page.name)
    for path in SITE.rglob("*.js"):
        check_javascript(path.read_text(encoding="utf-8"), path.relative_to(SITE).as_posix())
    for path in SITE.rglob("*.css"):
        source = path.read_text(encoding="utf-8")
        check(not re.search(r"(?:fonts\.googleapis\.com|fonts\.gstatic\.com)", source), f"{path.name}: font requests must stay first-party")
        for value in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", source):
            base_url = urljoin(ORIGIN + "/", path.relative_to(SITE).as_posix())
            if re.fullmatch(r"fonts(?:\.[0-9a-f]+)?\.css", path.name):
                font_url = urlsplit(urljoin(base_url, value.strip()))
                check(font_url.scheme == "https" and font_url.netloc == DOMAIN, f"{path.name}: font files must stay first-party")
            local_target(value.strip(), base_url, path.name)
    try:
        sitemap = ET.parse(SITE / "sitemap.xml")
        urls = [element.text for element in sitemap.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        expected = {page.url for page in pages if not page.noindex}
        check(len(urls) == len(set(urls)), "sitemap.xml: duplicate URLs")
        check(set(urls) == expected, f"sitemap.xml: URLs differ from indexable pages (missing={sorted(expected - set(urls))}, extra={sorted(set(urls) - expected)})")
    except (OSError, ET.ParseError) as error:
        errors.append(f"sitemap.xml: {error}")
    try:
        robots = (SITE / "robots.txt").read_text(encoding="utf-8")
        check(f"Sitemap: {ORIGIN}/sitemap.xml" in robots, "robots.txt: missing current HTTPS sitemap")
        check(not re.search(r"^Disallow:\s*/\s*$", robots, re.MULTILINE | re.IGNORECASE), "robots.txt: blocks the entire site")
        check((SITE / "CNAME").read_text(encoding="utf-8").strip() == DOMAIN, f"CNAME must contain {DOMAIN}")
    except OSError as error:
        errors.append(str(error))
    print(f"Checked {len(pages)} pages, privacy controls, signup form, local links/assets, JavaScript syntax, JSON-LD, sitemap, robots.txt and CNAME.")


if __name__ == "__main__":
    main()
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        raise SystemExit(1)
    print("Website validation passed.")
