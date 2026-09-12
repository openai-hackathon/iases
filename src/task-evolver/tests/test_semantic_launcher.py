import argparse
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "semantic_launcher",
    Path(__file__).resolve().parents[2] / "semantic-router" / "run.py",
)
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class SemanticLauncherTest(unittest.TestCase):
    def test_revision_sources(self):
        for marker in (None, launcher.ROUTER_REVISION, "wrong-revision"):
            with (
                self.subTest(marker=marker),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                if marker is not None:
                    (root / "UPSTREAM_REVISION").write_text(marker)
                args = argparse.Namespace(router_root=root, runtime=root / "runtime")
                with (
                    patch.object(
                        launcher.subprocess,
                        "check_output",
                        return_value=launcher.ROUTER_REVISION,
                    ) as revision,
                    patch.object(launcher, "config_value", return_value=None),
                ):
                    expected = (
                        "Use Semantic Router commit"
                        if marker == "wrong-revision"
                        else "Set OPENAI_API_KEY"
                    )
                    with self.assertRaisesRegex(ValueError, expected):
                        launcher.run(args)
                    self.assertEqual(revision.call_count, int(marker is None))
