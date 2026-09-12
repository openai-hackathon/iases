"""Verify the OpenAI overlay with mini-SWE-agent's real native tool adapter."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


@pytest.fixture
def openai_config(tmp_path, monkeypatch):
    # Do not load the developer's global credentials when mini is first imported.
    monkeypatch.setenv("MSWEA_GLOBAL_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("MSWEA_SILENT_STARTUP", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-never-sent")
    monkeypatch.delenv("MSWEA_MODEL_NAME", raising=False)
    pytest.importorskip("minisweagent")
    from minisweagent.config import builtin_config_dir
    from minisweagent.utils.serialize import recursive_merge

    root = Path(__file__).resolve().parents[1]
    paths = [
        Path(builtin_config_dir) / "benchmarks/swebench.yaml",
        root / "benchmarks/tsmc/configs/agent.yaml",
        root / "benchmarks/tsmc/configs/openai.yaml",
    ]
    return recursive_merge(*(yaml.safe_load(path.read_text()) for path in paths))


def test_openai_overlay_clears_bundled_model_and_keeps_workspace_collection(
    openai_config,
):
    from minisweagent.models import get_model_name

    assert openai_config["model"]["model_name"] is None
    with pytest.raises(ValueError, match="No default model"):
        get_model_name(config=openai_config["model"])
    assert openai_config["run"]["collect_workspace"] is True
    assert openai_config["environment"]["forward_env"] == []
    assert (
        "automatically collects workspace changes"
        in openai_config["agent"]["instance_template"]
    )


def test_openai_native_tool_request_and_observation_round_trip(openai_config):
    import litellm
    from minisweagent.models import get_model
    from minisweagent.models.litellm_model import LitellmModel

    model = get_model("openai/gpt-4.1-mini", openai_config["model"])
    assert type(model) is LitellmModel
    response = litellm.ModelResponse(
        model="gpt-4.1-mini",
        choices=[
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_inspect",
                            "type": "function",
                            "function": {
                                "name": "bash",
                                "arguments": '{"command":"git status --short"}',
                            },
                        }
                    ],
                },
            }
        ],
        usage={"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
    )
    with (
        patch(
            "minisweagent.models.litellm_model.litellm.completion",
            return_value=response,
        ) as completion,
        patch.object(model, "_calculate_cost", return_value={"cost": 0.001}),
        patch("minisweagent.models.litellm_model.GLOBAL_MODEL_STATS.add"),
    ):
        message = model.query([{"role": "user", "content": "Inspect the repository"}])

    kwargs = completion.call_args.kwargs
    assert kwargs["api_base"] == "https://api.openai.com/v1"
    assert kwargs["tools"][0]["function"]["name"] == "bash"
    assert kwargs["tool_choice"] == "required"
    assert kwargs["parallel_tool_calls"] is False
    assert not {"api_key", "temperature", "top_p", "extra_body"} & kwargs.keys()
    assert message["extra"]["actions"][0]["command"] == "git status --short"
    observations = model.format_observation_messages(
        message,
        [{"returncode": 0, "output": " M fabops/quality.py", "exception_info": None}],
    )
    assert observations[0]["role"] == "tool"
    assert observations[0]["tool_call_id"] == "call_inspect"
    assert "fabops/quality.py" in observations[0]["content"]
    serialized = model.serialize()
    assert "api_key" not in serialized["info"]["config"]["model"]["model_kwargs"]
    assert "test-key-never-sent" not in str(serialized)
