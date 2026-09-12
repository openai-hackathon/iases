from unittest.mock import MagicMock

import docker
import pytest

from swebench.harness.container_profiles import container_options
from swebench.harness.run_evaluation import create_container
from swebench.types import TestSpec as Spec


@pytest.mark.parametrize("conflict", [False, True])
def test_offline_limits_apply_on_create_and_conflict_retry(conflict):
    client = MagicMock()
    client.containers.get.side_effect = docker.errors.NotFound("missing")
    if conflict:
        client.containers.create.side_effect = [
            docker.errors.APIError("409 Conflict"),
            MagicMock(),
        ]
    spec = Spec(
        "sample-1", "image", [], "repo", "1", [], [], container_profile="python_offline"
    )
    create_container(spec, client, "run", MagicMock())
    for call in client.containers.create.call_args_list:
        assert call.kwargs["network_mode"] == "none"
        assert call.kwargs["cap_drop"] == ["ALL"]
        assert "cap_add" not in call.kwargs and "volumes" not in call.kwargs
        assert call.kwargs["mem_limit"] and call.kwargs["pids_limit"] > 0


def test_existing_profile_and_unknown_profile():
    assert container_options() == {"cap_add": ["SYS_ADMIN"]}
    with pytest.raises(ValueError, match="Unknown"):
        container_options("arbitrary")


def test_modal_rejects_profile_before_connecting(monkeypatch):
    from swebench.harness.modal_eval import run_evaluation_modal as backend

    spec = Spec(
        "sample-1", "image", [], "repo", "1", [], [], container_profile="python_offline"
    )
    monkeypatch.setattr(backend, "make_test_spec", lambda row: spec)
    connect = MagicMock()
    monkeypatch.setattr(backend.app, "run", connect)
    with pytest.raises(ValueError, match="local Docker"):
        backend.run_instances_modal({}, [{}], [], "profile-test", 10)
    connect.assert_not_called()
