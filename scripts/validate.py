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
from recipe_metadata import RecipeDocument, validate_recipe_metadata

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

    def handle_endtag(self, tag):
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


def main():
    check(SITE.is_dir(), f"Missing build output: {SITE}; run npm run build first")
    if not SITE.is_dir():
        return
    pages = [Page(path) for path in sorted(SITE.rglob("*.html"))]
    check(bool(pages), "No HTML pages were built")
    page_by_path = {page.path: page for page in pages}
    for page in pages:
        if page.name == "index.html":
            check_newsletter(page)
        check_recipe_layout(page)
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
            if tag == "img":
                check(bool(attrs.get("alt")), f"{page.name}: image needs descriptive alt text")
                check(all(attrs.get(size, "").isdigit() and int(attrs[size]) > 0 for size in ("width", "height")), f"{page.name}: image needs intrinsic width and height")
                check(bool(attrs.get("srcset")) and bool(attrs.get("sizes")), f"{page.name}: image needs responsive srcset and sizes")
            if attrs.get("srcset"):
                for candidate in attrs["srcset"].split(","):
                    fields = candidate.strip().split()
                    check(len(fields) == 2 and bool(re.fullmatch(r"[1-9][0-9]*w", fields[-1])), f"{page.name}: invalid width-based srcset candidate {candidate}")
                    if fields:
                        local_target(fields[0], page.url, page.name)
            for attribute in ("href", "src", "poster", "action"):
                if not attrs.get(attribute):
                    continue
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
        for value in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", path.read_text(encoding="utf-8")):
            local_target(value.strip(), urljoin(ORIGIN + "/", path.relative_to(SITE).as_posix()), path.name)
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
    print(f"Checked {len(pages)} pages, signup form, local links/assets, JavaScript syntax, JSON-LD, sitemap, robots.txt and CNAME.")


if __name__ == "__main__":
    main()
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        raise SystemExit(1)
    print("Website validation passed.")
