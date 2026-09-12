import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from prepare import prepare


class PrepareTest(unittest.TestCase):
    def test_reconstructs_pinned_source_with_patch_and_overlay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            upstream = root / "upstream"
            subprocess.run(["git", "init", "-q", str(upstream)], check=True)
            (upstream / "base.txt").write_text("before\n")
            subprocess.run(["git", "add", "."], cwd=upstream, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-qm",
                    "Initial",
                ],
                cwd=upstream,
                check=True,
            )
            revision = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=upstream, text=True
            ).strip()
            (upstream / "base.txt").write_text("after\n")
            patch = subprocess.check_output(["git", "diff"], cwd=upstream)
            integration = root / "integrations/example"
            integration.mkdir(parents=True)
            (integration / "changes.patch").write_bytes(patch)
            (root / "integrations/sources.json").write_text(
                json.dumps(
                    {
                        "example": {
                            "url": str(upstream),
                            "revision": revision,
                            "copies": {"overlay": "."},
                        }
                    }
                )
            )
            (root / "overlay").mkdir()
            (root / "overlay/feature.txt").write_text("feature\n")
            research = root / "src/model-router/research"
            research.mkdir(parents=True)
            (research / "reference.py").write_text("value = 1\n")
            destination = root / "workspace"
            prepare(root, destination)
            self.assertEqual(
                [
                    (destination / path).read_text()
                    for path in (
                        "example/base.txt",
                        "example/feature.txt",
                        "icr-router/experiments/reference.py",
                    )
                ],
                ["after\n", "feature\n", "value = 1\n"],
            )
            self.assertEqual(
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=destination / "example", text=True
                ).strip(),
                revision,
            )
            with self.assertRaises(FileExistsError):
                prepare(root, destination)
