#!/usr/bin/env python3
"""Stage only public website files for GitHub Pages."""
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "_site"
PUBLIC_EXTENSIONS = {".html", ".css", ".js", ".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif", ".svg", ".ico", ".woff", ".woff2"}
PUBLIC_ROOT_FILES = {"CNAME", "robots.txt", "sitemap.xml"}
PUBLIC_DIRECTORIES = {"assets", "images", "fonts"}


def copy_public_file(source: Path) -> None:
    if source.is_symlink():
        raise SystemExit(f"Refusing to publish symlink: {source.relative_to(ROOT)}")
    destination = OUTPUT / source.relative_to(ROOT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def render_shared_partials() -> None:
    """Expand a small allowlist of shared HTML, without publishing template sources."""
    names = {"privacy-links", "privacy-dialog"}
    def render(match):
        name = match.group(1)
        if name not in names:
            raise SystemExit(f"Unknown shared partial: {name}")
        return (ROOT / "partials" / f"{name}.html").read_text(encoding="utf-8").strip()
    for page in OUTPUT.glob("*.html"):
        html = page.read_text(encoding="utf-8")
        html = re.sub(r"<!-- include: ([a-z-]+) -->", render, html)
        page.write_text(html, encoding="utf-8")


def main() -> None:
    if OUTPUT.is_symlink():
        raise SystemExit("Refusing to replace a symlink at _site")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir()
    for source in sorted(ROOT.iterdir()):
        if source.is_file() and (source.suffix.lower() in PUBLIC_EXTENSIONS or source.name in PUBLIC_ROOT_FILES):
            copy_public_file(source)
        elif source.name in PUBLIC_DIRECTORIES and source.is_dir():
            if source.is_symlink():
                raise SystemExit(f"Refusing to publish symlink: {source.name}")
            for asset in sorted(source.rglob("*")):
                if asset.is_file() and (asset.suffix.lower() in PUBLIC_EXTENSIONS or source.name == "fonts" and asset.name == "LICENSE.txt"):
                    copy_public_file(asset)
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    render_shared_partials()
    subprocess.run(["node", "scripts/optimize-images.mjs"], cwd=ROOT, check=True)
    print(f"Staged {sum(path.is_file() for path in OUTPUT.rglob('*'))} public files in _site/")


if __name__ == "__main__":
    main()
