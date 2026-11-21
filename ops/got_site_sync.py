"""Pull and atomically publish the current successful static preview release."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.request


REPOSITORY = "Yousef-Abdallah-1711/got-design-system-preview"
ROOT = Path("/var/lib/servio-deployer/public/got")
MAX_ARCHIVE_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_BYTES = 50 * 1024 * 1024
MAX_FILES = 2_000
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def remote_ref(reference: str) -> str | None:
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", f"https://github.com/{REPOSITORY}.git", reference],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError("Could not read the public GØT deployment ref")
    for line in result.stdout.splitlines():
        commit, ref = line.split("\t", 1)
        if ref == reference:
            return commit
    return None


def current_main_sha() -> str:
    sha = remote_ref("refs/heads/main")
    if not sha or not SHA_PATTERN.fullmatch(sha):
        raise RuntimeError("Could not resolve the public main commit")
    return sha


def release_tag_commit(tag: str) -> str | None:
    command = [
        "git",
        "ls-remote",
        "--tags",
        f"https://github.com/{REPOSITORY}.git",
        f"refs/tags/{tag}",
        f"refs/tags/{tag}^{{}}",
    ]
    result = subprocess.run(command, capture_output=True, check=False, text=True, timeout=30)
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError("Could not verify the public GØT release tag")
    refs = dict(line.split("\t", 1)[::-1] for line in result.stdout.splitlines())
    return refs.get(f"refs/tags/{tag}^{{}}") or refs.get(f"refs/tags/{tag}")


def download(url: str, limit: int) -> bytes | None:
    request = urllib.request.Request(url, headers={"User-Agent": "got-site-sync/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read(limit + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise RuntimeError(f"Could not download GØT release asset: HTTP {error.code}") from error
    if len(data) > limit:
        raise RuntimeError("GØT release asset exceeds the configured size limit")
    return data


def validate_manifest(data: bytes, sha: str, tag: str) -> str:
    try:
        manifest = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("GØT deployment manifest is not valid JSON") from error
    if not isinstance(manifest, dict):
        raise RuntimeError("GØT deployment manifest is not an object")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("repository") != REPOSITORY
        or manifest.get("source_sha") != sha
        or manifest.get("release_tag") != tag
        or manifest.get("artifact") != "site.tar.gz"
        or not re.fullmatch(r"[0-9a-f]{64}", str(manifest.get("artifact_sha256", "")))
    ):
        raise RuntimeError("GØT deployment manifest identity is invalid")
    return manifest["artifact_sha256"]


def verify_archive_digest(archive: bytes, expected_digest: str) -> None:
    if hashlib.sha256(archive).hexdigest() != expected_digest:
        raise RuntimeError("GØT release archive checksum does not match its manifest")


def extract_archive(archive: bytes, destination: Path) -> None:
    try:
        source = tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz")
    except (tarfile.TarError, OSError) as error:
        raise RuntimeError("GØT release archive is invalid") from error

    extracted = 0
    count = 0
    seen: set[PurePosixPath] = set()
    with source:
        members = source.getmembers()
        if len(members) > MAX_FILES:
            raise RuntimeError("GØT release contains too many files")
        for member in members:
            relative = PurePosixPath(member.name)
            if member.isdir() and member.name in {".", "./"}:
                continue
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or "\\" in member.name
                or not relative.parts
                or not (member.isfile() or member.isdir())
            ):
                raise RuntimeError("GØT release contains an unsafe archive entry")
            target = destination.joinpath(*relative.parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise RuntimeError("GØT release archive escapes the staging directory")
            if relative in seen:
                raise RuntimeError("GØT release archive contains duplicate paths")
            seen.add(relative)
            count += 1
            if member.isfile():
                extracted += member.size
                if extracted > MAX_EXTRACTED_BYTES:
                    raise RuntimeError("GØT release expands beyond the configured size limit")
                target.parent.mkdir(parents=True, exist_ok=True)
                file_object = source.extractfile(member)
                if file_object is None:
                    raise RuntimeError("GØT release archive contains an unreadable file")
                with file_object, target.open("wb") as output:
                    shutil.copyfileobj(file_object, output)
                target.chmod(0o644)
            else:
                target.mkdir(parents=True, exist_ok=True)
                target.chmod(0o755)

    required = ("index.html", "ui_kits/storefront/index.html")
    if not all((destination / name).is_file() for name in required) or count == 0:
        raise RuntimeError("GØT release is missing its storefront entry points")


def current_release(root: Path) -> str | None:
    pointer = root / "current"
    if not pointer.is_symlink():
        return None
    resolved = pointer.resolve()
    if resolved.parent != (root / "releases").resolve():
        raise RuntimeError("GØT current pointer escapes the release directory")
    if not resolved.is_dir():
        return None
    return resolved.name


def install_release(root: Path, sha: str, archive: bytes) -> bool:
    releases = root / "releases"
    root.mkdir(parents=True, exist_ok=True, mode=0o755)
    releases.mkdir(parents=True, exist_ok=True, mode=0o755)
    target = releases / sha
    if target.exists():
        raise RuntimeError("Refusing to overwrite an existing immutable GØT release")

    stage = Path(tempfile.mkdtemp(prefix=".incoming-", dir=releases))
    try:
        extract_archive(archive, stage)
        stage.chmod(0o755)
        os.replace(stage, target)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise

    next_pointer = root / f".current-{sha}"
    next_pointer.unlink(missing_ok=True)
    next_pointer.symlink_to(Path("releases") / sha)
    os.replace(next_pointer, root / "current")
    prune_releases(releases, sha)
    return True


def prune_releases(releases: Path, current_sha: str) -> None:
    candidates = sorted(
        (path for path in releases.iterdir() if path.is_dir() and SHA_PATTERN.fullmatch(path.name)),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    keep = {path.name for path in candidates[:5]} | {current_sha}
    for path in candidates:
        if path.name not in keep:
            shutil.rmtree(path)


def sync(root: Path = ROOT) -> bool:
    sha = current_main_sha()
    if current_release(root) == sha:
        print(f"GØT preview already serves main {sha}")
        return False

    tag = f"got-preview-{sha}"
    if release_tag_commit(tag) != sha:
        print(f"No published GØT release is ready for main {sha}")
        return False

    asset_base = f"https://github.com/{REPOSITORY}/releases/download/{tag}"
    manifest_data = download(f"{asset_base}/deployment.json", 16 * 1024)
    if manifest_data is None:
        print(f"GØT release assets are not ready for main {sha}")
        return False
    expected_digest = validate_manifest(manifest_data, sha, tag)
    archive = download(f"{asset_base}/site.tar.gz", MAX_ARCHIVE_BYTES)
    if archive is None:
        print(f"GØT release archive is not ready for main {sha}")
        return False
    verify_archive_digest(archive, expected_digest)

    install_release(root, sha, archive)
    print(f"Deployed GØT static preview from main {sha}")
    return True


if __name__ == "__main__":
    sync()
