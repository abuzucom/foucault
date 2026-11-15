#!/usr/bin/env python3
"""Behavioral tests for the shared-file map inside shared-files.json.

check_shared reads the "shared" key as a map from file name to digest. A
list or string under that key previously reached an index lookup and raised
TypeError.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts import sync


class SharedMapShapeTest(unittest.TestCase):
    """check_shared reports a "shared" value that is not a JSON object."""

    def _check(self, shared_value) -> tuple:
        """Return the exit code and stderr for one manifest shape."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in sync.SHARED_FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("content\n", encoding="utf-8")
            (root / sync.SHARED_MANIFEST).write_text(
                json.dumps({"shared": shared_value}), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = sync.check_shared(root)
        return code, stderr.getvalue()

    def test_list_shared_value_is_reported(self):
        code, stderr = self._check(list(sync.SHARED_FILES))
        self.assertEqual(code, 1)
        self.assertIn('"shared" in shared-files.json is not a JSON object',
                      stderr)

    def test_string_shared_value_is_reported(self):
        code, stderr = self._check(" ".join(sync.SHARED_FILES))
        self.assertEqual(code, 1)
        self.assertIn('"shared" in shared-files.json is not a JSON object',
                      stderr)

    def test_object_shared_value_still_compares_digests(self):
        code, stderr = self._check({name: "0" for name in sync.SHARED_FILES})
        self.assertEqual(code, 1)
        self.assertIn("differs from the recorded copy", stderr)
        self.assertNotIn("is not a JSON object", stderr)


if __name__ == "__main__":
    unittest.main()
