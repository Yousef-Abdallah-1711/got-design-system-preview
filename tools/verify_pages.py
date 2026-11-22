"""Check that the prepared static preview contains its entry points and local assets."""

from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
REQUIRED_FILES = (
    "index.html",
    "styles.css",
    "_ds_bundle.js",
    "favicon.svg",
    "components/components.css",
    "ui_kits/storefront/index.html",
    "ui_kits/storefront/coming-soon.html",
    "ui_kits/storefront/product.html",
    "ui_kits/storefront/.image-slots.state.json",
)
CSS_IMPORT = re.compile(r"@import\s+(?:url\(\s*)?([\"'])(.*?)\1\s*\)?[^;]*;", re.IGNORECASE)


class LocalAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src", "poster"} and value:
                self.references.append(value)


def verify_required_files() -> None:
    missing = [name for name in REQUIRED_FILES if not (DIST / name).is_file()]
    if missing:
        raise RuntimeError("Missing preview files: " + ", ".join(missing))


def verify_css_imports(stylesheet: Path, visited: set[Path] | None = None) -> None:
    if visited is None:
        visited = set()
    stylesheet = stylesheet.resolve()
    if stylesheet in visited:
        return
    visited.add(stylesheet)

    for match in CSS_IMPORT.finditer(stylesheet.read_text(encoding="utf-8")):
        reference = match.group(2)
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (
            DIST / parsed.path.lstrip("/")
            if parsed.path.startswith("/")
            else stylesheet.parent / parsed.path
        ).resolve()
        if not target.is_relative_to(DIST.resolve()) or not target.is_file():
            relative_sheet = stylesheet.relative_to(DIST.resolve())
            raise RuntimeError(f"Broken CSS import in {relative_sheet}: {reference}")
        if target.suffix.lower() == ".css":
            verify_css_imports(target, visited)


def verify_local_references(page: Path) -> None:
    parser = LocalAssetParser()
    parser.feed(page.read_text(encoding="utf-8"))

    for reference in parser.references:
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (
            DIST / parsed.path.lstrip("/")
            if parsed.path.startswith("/")
            else page.parent / parsed.path
        ).resolve()
        if not target.is_relative_to(DIST.resolve()) or not target.is_file():
            relative_page = page.relative_to(DIST)
            raise RuntimeError(f"Broken local reference in {relative_page}: {reference}")
        if target.suffix.lower() == ".css":
            verify_css_imports(target)


def main() -> None:
    verify_required_files()
    for page in DIST.rglob("*.html"):
        verify_local_references(page)
    print(f"Verified static preview at {DIST}")


if __name__ == "__main__":
    main()
