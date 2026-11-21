"""Safety checks for publishing externally built static release archives."""

import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from ops import got_site_sync


def make_archive(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class GotSiteSyncTests(unittest.TestCase):
    def test_host_installer_prepares_the_libexec_directory(self) -> None:
        installer = Path(__file__).resolve().parents[1] / "tools/install_host_sync.sh"
        content = installer.read_text(encoding="utf-8")

        self.assertIn("install -d -o root -g root -m 0755 /usr/local/libexec", content)

    def test_publish_workflow_resolves_draft_release_from_releases_list(self) -> None:
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/build-and-deploy.yml"
        content = workflow.read_text(encoding="utf-8")

        self.assertIn('releases?per_page=100', content)
        self.assertIn('select(.tag_name ==', content)
        self.assertNotIn('releases/tags/$tag', content)

    def test_manifest_requires_exact_public_repo_sha_and_release_tag(self) -> None:
        sha = "a" * 40
        tag = f"got-preview-{sha}"
        manifest = {
            "schema_version": 1,
            "repository": got_site_sync.REPOSITORY,
            "source_sha": sha,
            "release_tag": tag,
            "artifact": "site.tar.gz",
            "artifact_sha256": "b" * 64,
        }

        self.assertEqual(got_site_sync.validate_manifest(json.dumps(manifest).encode(), sha, tag), "b" * 64)
        manifest["source_sha"] = "c" * 40
        with self.assertRaisesRegex(RuntimeError, "identity is invalid"):
            got_site_sync.validate_manifest(json.dumps(manifest).encode(), sha, tag)

    def test_archive_rejects_path_traversal_and_symlinks(self) -> None:
        unsafe = make_archive({"../outside.txt": b"bad"})
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "unsafe archive entry"):
                got_site_sync.extract_archive(unsafe, Path(directory))

        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            member = tarfile.TarInfo("index.html")
            member.type = tarfile.SYMTYPE
            member.linkname = "/etc/passwd"
            archive.addfile(member)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "unsafe archive entry"):
                got_site_sync.extract_archive(buffer.getvalue(), Path(directory))

    def test_workflow_style_archive_root_marker_is_accepted(self) -> None:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            root = tarfile.TarInfo("./")
            root.type = tarfile.DIRTYPE
            archive.addfile(root)
            for name, data in {
                "./index.html": b"<a href='ui_kits/storefront/index.html'>preview</a>",
                "./ui_kits/storefront/index.html": b"<main>GOT</main>",
            }.items():
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))

        with tempfile.TemporaryDirectory() as directory:
            got_site_sync.extract_archive(buffer.getvalue(), Path(directory))
            self.assertTrue((Path(directory) / "ui_kits/storefront/index.html").is_file())

    def test_release_pointer_changes_only_after_valid_archive(self) -> None:
        sha = "d" * 40
        archive = make_archive({
            "index.html": b"<a href='ui_kits/storefront/index.html'>preview</a>",
            "ui_kits/storefront/index.html": b"<main>GOT</main>",
        })
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "site"
            self.assertTrue(got_site_sync.install_release(root, sha, archive))
            self.assertEqual(got_site_sync.current_release(root), sha)
            self.assertEqual((root / "current/index.html").read_bytes(), b"<a href='ui_kits/storefront/index.html'>preview</a>")
            with self.assertRaisesRegex(RuntimeError, "overwrite"):
                got_site_sync.install_release(root, sha, archive)

    def test_archive_rejects_a_manifest_digest_mismatch(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "checksum does not match"):
            got_site_sync.verify_archive_digest(b"tampered archive", "0" * 64)


if __name__ == "__main__":
    unittest.main()
