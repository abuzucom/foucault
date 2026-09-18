#!/usr/bin/env python3
"""Upstream manifest freshness tests.

`scripts/check_upstream_drift.py --check-local` runs in one CI job. A
changelog entry changes the recorded `CHANGELOG.md` hash, and a stale entry
reaches the default branch when no test run reports the mismatch. These
tests recompute every recorded hash on each platform the suite covers.
"""
import hashlib
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "upstream-files.json"


def normalized_sha256(path: Path) -> str:
    """Return the line-ending-normalized SHA-256 the drift checker records."""
    text = path.read_bytes().decode("utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class ManifestHashTest(unittest.TestCase):
    """Every recorded hash matches the file it names."""

    def setUp(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        # A locally adapted file also appears under "files" at its upstream
        # hash. check_local resolves that overlap toward the adapted value.
        self.tracked = dict(manifest["files"])
        self.tracked.update(manifest["local_adapted_files"])

    def test_tracked_files_exist(self):
        self.assertTrue(self.tracked)
        for rel_path in sorted(self.tracked):
            with self.subTest(path=rel_path):
                self.assertTrue((REPO_ROOT / rel_path).is_file())

    def test_tracked_files_match_recorded_hashes(self):
        for rel_path, recorded_hash in sorted(self.tracked.items()):
            local_path = REPO_ROOT / rel_path
            if not local_path.is_file():
                continue
            with self.subTest(path=rel_path):
                self.assertEqual(normalized_sha256(local_path), recorded_hash)
