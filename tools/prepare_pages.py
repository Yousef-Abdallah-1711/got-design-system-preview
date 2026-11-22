"""Assemble the public static storefront preview into dist/."""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (ROOT / "dist").resolve()


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> None:
    if OUTPUT.parent != ROOT.resolve() or OUTPUT.name != "dist":
        raise RuntimeError(f"Refusing unexpected output path: {OUTPUT}")

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    for name in ("index.html", "styles.css", "_ds_bundle.js", "favicon.svg"):
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

    print(f"Prepared static preview at {OUTPUT}")


if __name__ == "__main__":
    main()
