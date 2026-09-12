import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from export_hiershrink import export


class ExportTest(unittest.TestCase):
    def test_roundtrip_and_rejection(self):
        fixture = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "src/semantic-router/pkg/selection/testdata/hiershrink.json"
            ).read_text()
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "profile.npz"
            destination = Path(directory) / "profile.json"
            arrays = {
                name: fixture[name]
                for name in ["models", "costs", "profile", "offset", "table", "centers"]
            }
            for index, layer in enumerate(fixture["layers"]):
                arrays[f"w{index}"] = layer["weights"]
                arrays[f"b{index}"] = layer["bias"]
            np.savez(source, **arrays)
            mapping = {name: name for name in fixture["models"]}
            export(source, destination, "fixture", mapping)
            self.assertEqual(json.loads(destination.read_text()), fixture)
            with self.assertRaises(FileExistsError):
                export(source, destination, "fixture", mapping)
            with self.assertRaises(KeyError):
                export(source, destination, "fixture", {})
            with self.assertRaises(ValueError):
                export(
                    source, destination, "fixture", dict.fromkeys(mapping, "same")
                )


if __name__ == "__main__":
    unittest.main()
