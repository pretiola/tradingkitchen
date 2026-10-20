"""Check recipe metadata against the visible recipe, without external services."""

from dataclasses import dataclass, field
from html.parser import HTMLParser
import re
from urllib.parse import unquote, urlsplit


ORIGIN = "https://tradingkitchen.org/"
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def normalized_text(value):
    """Ignore presentation whitespace and equivalent typographic punctuation."""
    return " ".join(value.translate(str.maketrans({
        "\u2010": "-", "\u2011": "-", "\u2013": "-", "\u2014": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    })).split())


@dataclass
class Element:
    tag: str
    attrs: dict
    in_recipe: bool
    parts: list = field(default_factory=list)

    @property
    def text(self):
        return normalized_text("".join(self.parts))


class RecipeDocument(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.stack = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        in_recipe = attrs.get("id") == "recipe-section" or any(element.in_recipe for element in self.stack)
        element = Element(tag, attrs, in_recipe)
        self.elements.append(element)
        if tag not in VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(self, tag, attributes):
        self.handle_starttag(tag, attributes)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        for element in self.stack:
            element.parts.append(data)

    def with_class(self, name):
        return [element for element in self.elements if name in element.attrs.get("class", "").split()]


def duration_seconds(value):
    """Accept ISO 8601 day/hour/minute/second durations used for recipes."""
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", value)
    if not match or not any(match.groups()) or value.endswith("T"):
        return None
    return sum(int(number or 0) * multiplier for number, multiplier in zip(match.groups(), (86400, 3600, 60, 1)))


def visible_duration_seconds(value):
    """Read the upper bound of the site's displayed timing ranges.

    This is our editorial convention, not a schema.org requirement. Parse the
    actual text as well as data-duration so a stale annotation cannot hide drift.
    """
    upper = re.split(r"\s*(?:[\u2010\u2011\u2013\u2014-]|\bto\b)\s*", value.lower())[-1]
    units = re.findall(r"(\d+)\s*(hours?|hrs?|minutes?|mins?|seconds?|secs?)\b", upper)
    if not units:
        return None
    return sum(int(number) * (3600 if unit.startswith("h") else 60 if unit.startswith("m") else 1) for number, unit in units)


def validate_recipe_metadata(recipe, document, page_url):
    """Return actionable errors; optional ratings/nutrition/step media stay optional."""
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    for name in ("name", "recipeCategory", "recipeCuisine", "keywords"):
        check(isinstance(recipe.get(name), str) and bool(recipe[name].strip()), f"Recipe missing {name}")
    for name in ("image", "recipeIngredient", "recipeInstructions"):
        check(isinstance(recipe.get(name), list) and bool(recipe[name]), f"Recipe missing {name}")

    author = recipe.get("author")
    check(isinstance(author, dict) and author.get("@type") == "Organization" and author.get("name") == "Trading Kitchen" and author.get("url") == ORIGIN,
          "Recipe author must identify Trading Kitchen and its canonical URL")
    bylines = document.with_class("recipe-byline")
    check(len(bylines) == 1 and bylines[0].text == "By Trading Kitchen", "Recipe needs the visible Trading Kitchen byline")

    categories = document.with_class("recipe-meta")
    for name in ("recipeCategory", "recipeCuisine"):
        value = recipe.get(name)
        if isinstance(value, str) and value.strip():
            check(any(normalized_text(value) in element.text for element in categories), f"Recipe {name} must match visible recipe metadata")

    for name in ("prepTime", "cookTime"):
        seconds = duration_seconds(recipe.get(name))
        check(seconds is not None and seconds > 0, f"Recipe {name} must be a positive ISO 8601 duration")
        visible = [element for element in document.elements if element.attrs.get("data-time-field") == name]
        check(len(visible) == 1 and visible[0].tag == "dd" and visible[0].in_recipe, f"Recipe needs one visible {name} in its recipe facts")
        if len(visible) == 1:
            check(visible[0].attrs.get("data-duration") == recipe.get(name), f"Recipe {name} differs from its visible duration annotation")
            check(seconds is not None and visible_duration_seconds(visible[0].text) == seconds, f"Recipe {name} differs from the visible timing or range upper bound")

    elements_by_id = {element.attrs["id"]: element for element in document.elements if "id" in element.attrs}
    steps = recipe.get("recipeInstructions")
    if not isinstance(steps, list):
        return errors
    linked_steps = []
    for number, step in enumerate(steps, 1):
        prefix = f"Recipe step {number}"
        if not isinstance(step, dict):
            errors.append(f"{prefix} must be a HowToStep")
            continue
        check(step.get("@type") == "HowToStep", f"{prefix} must be a HowToStep")
        check(isinstance(step.get("name"), str) and bool(step["name"].strip()), f"{prefix} needs a short name")
        text = step.get("text")
        check(isinstance(text, str) and bool(text.strip()), f"{prefix} needs instruction text")
        url = step.get("url")
        if not isinstance(url, str) or not url:
            errors.append(f"{prefix} needs a direct URL to its visible instruction")
            continue
        try:
            target = urlsplit(url)
            current = urlsplit(page_url)
            local = target.scheme == current.scheme and target.netloc == current.netloc and target.path == current.path and not target.query
            fragment = unquote(target.fragment)
            element = elements_by_id.get(fragment)
        except ValueError:
            local, element, fragment = False, None, ""
        check(local and bool(fragment) and element is not None and element.tag == "li" and element.in_recipe,
              f"{prefix} URL must identify an instruction on this recipe page")
        if local and element is not None and element.tag == "li" and element.in_recipe:
            linked_steps.append(fragment)
            check(isinstance(text, str) and normalized_text(text) == element.text, f"{prefix} text differs from its visible instruction")
    visible_steps = [element.attrs["id"] for element in document.elements if element.tag == "li" and element.in_recipe and element.attrs.get("id", "").startswith("step-")]
    check(linked_steps == visible_steps and len(set(linked_steps)) == len(linked_steps), "Recipe steps must link to every visible instruction once, in order")
    return errors
