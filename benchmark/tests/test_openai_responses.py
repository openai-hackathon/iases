"""Exercise SDK serialization, reasoning continuity and auditable request failures."""

import importlib
import json
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

PRICES = {"input": 4, "cached_input": 0.4, "cache_write": 5, "output": 20}


def response(output=None, *, number=1, usage=True, status="completed"):
    return {
        "id": f"resp_{number}",
        "object": "response",
        "created_at": 1,
        "status": status,
        "model": "gpt-5.6-sol",
        "service_tier": "default",
        "output": output if output is not None else [tool_call(number=number)],
        "usage": {
            "input_tokens": 100,
            "input_tokens_details": {"cached_tokens": 20, "cache_write_tokens": 10},
            "output_tokens": 30,
            "output_tokens_details": {"reasoning_tokens": 25},
            "total_tokens": 130,
        }
        if usage
        else None,
    }


def tool_call(command="pwd", number=1):
    return {
        "id": f"fc_{number}",
        "type": "function_call",
        "call_id": f"call_{number}",
        "name": "bash",
        "arguments": json.dumps({"command": command}),
        "status": "completed",
    }


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    monkeypatch.setenv("MSWEA_GLOBAL_CONFIG_DIR", str(tmp_path / "global"))
    monkeypatch.setenv("MSWEA_SILENT_STARTUP", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-never-sent")
    pytest.importorskip("minisweagent")
    module = importlib.import_module("swebench.inference.openai_responses")
    monkeypatch.setattr(module.GLOBAL_MODEL_STATS, "add", lambda _: None)
    clients = []

    def build(handler, **config):
        from openai import OpenAI

        def client_factory(**options):
            assert options == {
                "base_url": "https://api.openai.com/v1",
                "timeout": 600,
                "max_retries": 0,
            }
            client = OpenAI(
                api_key="test-key-never-sent",
                http_client=httpx.Client(transport=httpx.MockTransport(handler)),
                **options,
            )
            clients.append(client)
            return client

        monkeypatch.setattr(module, "OpenAI", client_factory)
        return module.OpenAIResponsesModel(
            model_name="openai/gpt-5.6-sol",
            model_kwargs={
                "api_base": "https://api.openai.com/v1",
                "timeout": 600,
                "num_retries": 0,
                "drop_params": True,
                "reasoning": {"effort": "medium"},
                "max_output_tokens": 32768,
            },
            pricing_per_million=PRICES,
            request_log_path=tmp_path / "requests.jsonl",
            **config,
        )

    yield module, build, tmp_path / "requests.jsonl"
    for client in clients:
        client.close()


def test_native_sdk_replays_reasoning_phase_and_tool_outputs(adapter):
    _, build, journal = adapter
    requests = []
    reasoning = {
        "id": "rs_1",
        "type": "reasoning",
        "summary": [],
        "encrypted_content": "encrypted-fixture",
    }
    commentary = {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "phase": "commentary",
        "content": [
            {"type": "output_text", "text": "Inspecting files.", "annotations": []}
        ],
    }

    def handler(request):
        records = [json.loads(line) for line in journal.read_text().splitlines()]
        assert records[-1]["event"] == "request_started"
        assert str(request.url) == "https://api.openai.com/v1/responses"
        requests.append(json.loads(request.content))
        output = (
            [reasoning, commentary, tool_call()]
            if len(requests) == 1
            else [tool_call(number=2)]
        )
        return httpx.Response(200, json=response(output, number=len(requests)))

    model = build(handler)
    history = [
        {"role": "system", "content": "Repair the repository."},
        {"role": "user", "content": "Inspect."},
    ]
    first = model.query(history)
    observations = model.format_observation_messages(
        first, [{"output": "/testbed", "returncode": 0, "exception_info": None}]
    )
    second = model.query([*history, first, *observations])
    assert first["extra"]["actions"] == [{"command": "pwd", "tool_call_id": "call_1"}]
    assert second["extra"]["actions"][0]["tool_call_id"] == "call_2"
    assert requests[0]["model"] == "gpt-5.6-sol"
    assert requests[0]["reasoning"] == {"effort": "medium"}
    assert requests[0]["max_output_tokens"] == 32768
    assert requests[0]["store"] is False
    assert requests[0]["service_tier"] == "default"
    assert requests[0]["tools"][0]["name"] == "bash"
    assert requests[0]["parallel_tool_calls"] is False
    assert "reasoning.encrypted_content" in requests[0]["include"]
    replay = requests[1]["input"]
    assert (
        next(item for item in replay if item.get("type") == "reasoning")[
            "encrypted_content"
        ]
        == "encrypted-fixture"
    )
    assert (
        next(item for item in replay if item.get("role") == "assistant")["phase"]
        == "commentary"
    )
    assert replay[-1]["type"] == "function_call_output"
    assert replay[-1]["call_id"] == "call_1"
    assert not any("extra" in item for item in replay)
    assert "previous_response_id" not in requests[1]
    assert first["extra"]["token_usage"] == {
        "input_tokens": 100,
        "cached_input_tokens": 20,
        "cache_write_input_tokens": 10,
        "output_tokens": 30,
        "reasoning_tokens": 25,
        "total_tokens": 130,
    }
    assert first["extra"]["cost"] == pytest.approx(
        (70 * 4 + 20 * 0.4 + 10 * 5 + 30 * 20) / 1e6
    )
    ledger = model.serialize()["info"]["api_requests"]
    assert len(ledger) == 2
    assert all(record["duration_seconds"] >= 0 for record in ledger)
    assert ledger[0]["returned_model"] == "gpt-5.6-sol"
    assert ledger[0]["response_id"] == "resp_1"
    assert [json.loads(line)["event"] for line in journal.read_text().splitlines()] == [
        "request_started",
        "request_completed",
        "request_started",
        "request_completed",
    ]
    assert "test-key-never-sent" not in json.dumps(model.serialize())
    assert "test-key-never-sent" not in journal.read_text()


def test_format_error_keeps_billed_reasoning_and_closes_bad_call(adapter):
    module, build, _ = adapter
    requests = []
    malformed = tool_call()
    malformed["arguments"] = "not JSON"
    reasoning = {
        "id": "rs_1",
        "type": "reasoning",
        "summary": [],
        "encrypted_content": "preserved",
    }

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json=response(
                [reasoning, malformed] if len(requests) == 1 else [tool_call(number=2)]
            ),
        )

    model = build(handler)
    initial = [{"role": "user", "content": "Inspect."}]
    with pytest.raises(module.FormatError) as caught:
        model.query(initial)
    recovered = caught.value.messages
    assert recovered[0]["object"] == "response"
    assert recovered[0]["extra"]["cost"] > 0
    assert recovered[0]["extra"]["actions"] == []
    assert recovered[1]["type"] == "function_call_output"
    assert recovered[1]["call_id"] == "call_1"
    model.query([*initial, *recovered])
    assert requests[1]["input"][1]["encrypted_content"] == "preserved"
    assert any(
        item.get("type") == "function_call_output" for item in requests[1]["input"]
    )


def test_replay_omits_sdk_null_protocol_fields_without_changing_raw_response(adapter):
    _, build, _ = adapter
    requests = []
    output = [
        {
            "id": "rs_1",
            "type": "reasoning",
            "summary": [],
            "content": None,
            "status": None,
            "encrypted_content": "preserve-encrypted-bytes",
        },
        {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "phase": "commentary",
            "content": [
                {
                    "type": "output_text",
                    "text": "Inspecting.",
                    "annotations": [],
                    "logprobs": None,
                }
            ],
        },
        {**tool_call("printf 'null\\n'"), "caller": None, "namespace": None},
    ]

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        for item in body["input"]:
            if item.get("type") == "reasoning":
                # Reproduces the live API's unknown_parameter input[N].status
                # rejection after a reasoning item first enters the history.
                assert "status" not in item
                assert "content" not in item
            if item.get("type") == "function_call":
                assert "caller" not in item and "namespace" not in item
        return httpx.Response(
            200, json=response(output if len(requests) == 1 else None)
        )

    model = build(handler)
    initial = [{"role": "user", "content": "Inspect."}]
    first = model.query(initial)
    before = json.dumps(first, sort_keys=True)
    observation = model.format_observation_messages(
        first, [{"output": '{"value":null}', "returncode": 0, "exception_info": None}]
    )
    model.query([*initial, first, *observation])
    assert json.dumps(first, sort_keys=True) == before
    assert first["output"][0]["status"] is None
    replayed = requests[1]["input"]
    assert replayed[1]["encrypted_content"] == "preserve-encrypted-bytes"
    assert replayed[2]["phase"] == "commentary"
    assert "logprobs" not in replayed[2]["content"][0]
    assert replayed[3]["arguments"] == output[2]["arguments"]
    assert '{"value":null}' in replayed[-1]["output"]


def test_incomplete_reasoning_usage_is_not_lost(adapter):
    module, build, journal = adapter
    data = response(
        [
            {
                "id": "rs_1",
                "type": "reasoning",
                "summary": [],
                "encrypted_content": "partial",
            }
        ],
        status="incomplete",
    )
    data["incomplete_details"] = {"reason": "max_output_tokens"}
    model = build(lambda _: httpx.Response(200, json=data))
    with pytest.raises(module.FormatError) as caught:
        model.query([{"role": "user", "content": "Inspect."}])
    assert caught.value.messages[0]["extra"]["token_usage"]["reasoning_tokens"] == 25
    assert (
        json.loads(journal.read_text().splitlines()[-1])["incomplete_reason"]
        == "max_output_tokens"
    )


@pytest.mark.parametrize("kind", ["rate_limit", "timeout"])
def test_failed_http_attempt_has_one_safe_terminal_record(adapter, kind):
    module, build, journal = adapter
    calls = []

    def handler(request):
        calls.append(request)
        if kind == "timeout":
            raise httpx.ReadTimeout("private provider error text", request=request)
        return httpx.Response(
            429,
            json={
                "error": {
                    "message": "private provider error text",
                    "type": "rate_limit_error",
                    "code": "rate_limit_exceeded",
                }
            },
        )

    model = build(handler)
    with pytest.raises(module.OpenAIRequestError) as caught:
        model.query([{"role": "user", "content": "Inspect."}])
    assert len(calls) == 1
    assert "private provider error text" not in str(caught.value)
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    assert [event["event"] for event in events] == ["request_started", "request_failed"]
    assert events[-1]["estimated_cost_usd"] is None
    assert events[-1]["usage"] is None
    assert events[-1]["error_type"] == (
        "APITimeoutError" if kind == "timeout" else "RateLimitError"
    )
    assert "private provider error text" not in journal.read_text()


def test_interruption_preserves_unfinished_request_start(adapter):
    _, build, journal = adapter

    def handler(_):
        raise KeyboardInterrupt

    model = build(handler)
    with pytest.raises(KeyboardInterrupt):
        model.query([{"role": "user", "content": "Inspect."}])
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    assert len(events) == 1
    assert events[0]["event"] == "request_started"
    assert model.serialize()["info"]["api_requests"] == []


def test_missing_usage_and_cache_write_are_unknown(adapter):
    module, build, _ = adapter
    model = build(lambda _: httpx.Response(200, json=response(usage=False)))
    message = model.query([{"role": "user", "content": "Inspect."}])
    assert all(value is None for value in message["extra"]["token_usage"].values())
    assert message["extra"]["estimated_cost_usd"] is None
    missing_write = response()["usage"]
    del missing_write["input_tokens_details"]["cache_write_tokens"]
    assert module.estimate_cost(module.normalize_usage(missing_write), PRICES) is None


def test_long_context_pricing_threshold_and_output_includes_reasoning(adapter):
    module, _, _ = adapter
    counts = {
        "input_tokens": 272000,
        "cached_input_tokens": 2000,
        "cache_write_input_tokens": 1000,
        "output_tokens": 100,
        "reasoning_tokens": 90,
    }
    short = module.estimate_cost(counts, PRICES)
    assert short == pytest.approx((269000 * 4 + 2000 * 0.4 + 1000 * 5 + 100 * 20) / 1e6)
    counts["input_tokens"] += 1
    long = module.estimate_cost(counts, PRICES)
    assert long == pytest.approx(
        (2 * (269001 * 4 + 2000 * 0.4 + 1000 * 5) + 1.5 * 100 * 20) / 1e6
    )


def test_responses_workspace_agent_rejects_empty_then_collects_actual_edit(
    adapter, tmp_path
):
    _, build, _ = adapter
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.exceptions import Submitted

    from swebench.benchmarks.tsmc.common import init_git
    from swebench.inference.workspace_agent import workspace_agent_class

    repo = tmp_path / "repository"
    (repo / "fabops").mkdir(parents=True)
    (repo / "fabops/service.py").write_text("value = 1\n")
    init_git(repo)
    commands = iter(
        [
            "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT",
            "printf 'value = 2\\n' > fabops/service.py",
            "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT",
        ]
    )
    counter = []

    def handler(_):
        counter.append(1)
        return httpx.Response(
            200,
            json=response(
                [tool_call(next(commands), number=len(counter))], number=len(counter)
            ),
        )

    class Environment:
        def execute(self, action):
            command = action["command"]
            if command == "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT":
                raise Submitted(
                    {
                        "role": "exit",
                        "content": "Submitted",
                        "extra": {"exit_status": "Submitted", "submission": ""},
                    }
                )
            result = subprocess.run(
                command,
                shell=True,
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
                env={"PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin"},
            )
            return {
                "returncode": result.returncode,
                "output": result.stdout + result.stderr,
                "exception_info": None,
            }

        def get_template_vars(self):
            return {}

        def serialize(self):
            return {}

    agent = workspace_agent_class(DefaultAgent)(
        build(handler),
        Environment(),
        system_template="Repair the code.",
        instance_template="{{task}}",
        step_limit=5,
        cost_limit=0,
    )
    agent.instance_id = "tsmc__fixture-v1.0"
    result = agent.run("Set value to 2.")
    assert result["exit_status"] == "Submitted", result
    assert "+value = 2" in result["submission"]
    assert len(agent.rejected_submissions) == 1
    assert len(counter) == 3
    serialized = agent.serialize()
    assert serialized["info"]["model_submission"] == ""
    assert serialized["info"]["submission_source"] == "workspace_diff"
