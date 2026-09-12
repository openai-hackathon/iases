from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from swebench.benchmarks.tsmc.validate import checked_images


@pytest.mark.parametrize("label", [None, "old-baseline", "expected-baseline"])
def test_stale_image_cannot_enter_validation_or_composition(label):
    client = MagicMock()
    client.images.get.return_value = SimpleNamespace(
        id="sha256:immutable", labels={"org.tsmc-bench.base-commit": label}
    )
    instance = dict(
        instance_id="tsmc__f01-v0.2",
        image="fixture:latest",
        base_commit="expected-baseline",
    )
    if label == instance["base_commit"]:
        assert checked_images(client, [instance]) == {
            instance["instance_id"]: "sha256:immutable"
        }
    else:
        with pytest.raises(ValueError, match="force-rebuild"):
            checked_images(client, [instance])
