"""Assemble the public static storefront preview into dist/."""

import hashlib
import html
from pathlib import Path
import re
import shutil
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (ROOT / "dist").resolve()
ASSET_SUFFIXES = {
    ".css", ".js", ".jsx", ".json", ".svg", ".ico", ".png", ".jpg",
    ".jpeg", ".webp", ".avif", ".woff", ".woff2",
}
HTML_REFERENCE = re.compile(
    r"(?P<prefix>\b(?:href|src|poster)\s*=\s*)(?P<quote>[\"'])"
    r"(?P<url>.*?)(?P=quote)",
    re.IGNORECASE,
)
CSS_IMPORT = re.compile(
    r"(?P<prefix>@import\s+(?:url\(\s*)?)(?P<quote>[\"'])"
    r"(?P<url>.*?)(?P=quote)(?P<suffix>\s*\)?[^;]*;)",
    re.IGNORECASE,
)
CSS_URL = re.compile(
    r"(?P<prefix>\burl\(\s*)(?P<quote>[\"']?)"
    r"(?P<url>[^\"')]+?)(?P=quote)(?P<suffix>\s*\))",
    re.IGNORECASE,
)


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def build_version() -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in OUTPUT.rglob("*") if item.is_file()):
        digest.update(path.relative_to(OUTPUT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    digest.update(Path(__file__).read_bytes())
    return digest.hexdigest()[:20]


def versioned_reference(reference: str, containing_file: Path, version: str) -> str:
    parsed = urlsplit(html.unescape(reference))
    if parsed.scheme or parsed.netloc or not parsed.path:
        return reference
    if Path(parsed.path).suffix.lower() not in ASSET_SUFFIXES:
        return reference

    target = (
        OUTPUT / unquote(parsed.path).lstrip("/")
        if parsed.path.startswith("/")
        else containing_file.parent / unquote(parsed.path)
    ).resolve()
    if not target.is_relative_to(OUTPUT) or not target.is_file():
        return reference

    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key != "v"
    ]
    query.append(("v", version))
    updated = urlunsplit(("", "", parsed.path, urlencode(query), parsed.fragment))
    return html.escape(updated, quote=True)


def stamp_html_assets(page: Path, version: str) -> None:
    content = page.read_text(encoding="utf-8")
    content = HTML_REFERENCE.sub(
        lambda match: (
            match.group("prefix")
            + match.group("quote")
            + versioned_reference(match.group("url"), page, version)
            + match.group("quote")
        ),
        content,
    )
    page.write_text(content, encoding="utf-8")


def stamp_css_assets(stylesheet: Path, version: str) -> None:
    content = stylesheet.read_text(encoding="utf-8")

    def replace_reference(match: re.Match[str]) -> str:
        return (
            match.group("prefix")
            + match.group("quote")
            + versioned_reference(match.group("url"), stylesheet, version)
            + match.group("quote")
            + match.group("suffix")
        )

    content = CSS_IMPORT.sub(replace_reference, content)
    content = CSS_URL.sub(replace_reference, content)
    stylesheet.write_text(content, encoding="utf-8")


def stamp_sidecar_fetch(version: str) -> None:
    script = OUTPUT / "ui_kits" / "storefront" / "image-slot.js"
    marker = "const STATE_URL = STATE_FILE;"
    replacement = f"const STATE_URL = STATE_FILE + '?v={version}';"
    content = script.read_text(encoding="utf-8")
    if marker not in content:
        raise RuntimeError("Could not find image-slot state URL to version")
    script.write_text(content.replace(marker, replacement, 1), encoding="utf-8")


def stamp_static_asset_urls() -> None:
    version = build_version()
    for page in OUTPUT.rglob("*.html"):
        stamp_html_assets(page, version)
    for stylesheet in OUTPUT.rglob("*.css"):
        stamp_css_assets(stylesheet, version)
    stamp_sidecar_fetch(version)


def main() -> None:
    if OUTPUT.parent != ROOT.resolve() or OUTPUT.name != "dist":
        raise RuntimeError(f"Refusing unexpected output path: {OUTPUT}")

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    for name in (
        "index.html",
        "styles.css",
        "_ds_bundle.js",
        "favicon.svg",
        ".image-slots.state.json",
    ):
        copy_file(ROOT / name, OUTPUT / name)

    for folder in ("tokens", "assets/icons"):
        for source in (ROOT / folder).rglob("*"):
            if source.is_file() and source.suffix.lower() in {".css", ".svg"}:
                copy_file(source, OUTPUT / source.relative_to(ROOT))

    for source in (ROOT / "components").rglob("*.css"):
        copy_file(source, OUTPUT / source.relative_to(ROOT))

    storefront = ROOT / "ui_kits" / "storefront"
    for source in storefront.rglob("*"):
        if source.is_file() and source.suffix.lower() in {".html", ".css", ".js", ".jsx", ".json"}:
            copy_file(source, OUTPUT / source.relative_to(ROOT))

    # Serve the interactive storefront at the domain root while keeping the
    # original /ui_kits/storefront/index.html URL available as well.
    copy_file(storefront / "index.html", OUTPUT / "index.html")
    stamp_static_asset_urls()

    print(f"Prepared static preview at {OUTPUT}")


if __name__ == "__main__":
    main()
