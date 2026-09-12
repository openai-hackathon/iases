"""Native Responses API execution with replayable reasoning and request accounting.

Each query makes exactly one SDK request. The optional append-only journal records
the start before network I/O so a terminated worker leaves an auditable attempt
whose response and billing are unknown. Credentials are read by the SDK from the
host environment and never belong in model configuration or telemetry.
"""

from __future__ import annotations

import copy
import json
import math
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from minisweagent.exceptions import FormatError
from minisweagent.models import GLOBAL_MODEL_STATS
from minisweagent.models.litellm_model import LitellmModelConfig
from minisweagent.models.litellm_response_model import LitellmResponseModel
from minisweagent.models.utils.actions_toolcall_response import (
    BASH_TOOL_RESPONSE_API,
    finish_reason_from_responses_api,
    parse_toolcall_actions_response,
)
from openai import OpenAI

OFFICIAL_API_BASE = "https://api.openai.com/v1"


class OpenAIResponsesModelConfig(LitellmModelConfig):
    request_log_path: Path | None = None
    pricing_per_million: dict[str, float] | None = None
    long_context_threshold: int = 272000
    long_context_input_multiplier: float = 2.0
    long_context_output_multiplier: float = 1.5


def normalize_usage(usage: dict | None) -> dict[str, int | None]:
    """Preserve unknown counters as None, including unreported cache writes."""
    usage = usage or {}
    inputs = usage.get("input_tokens_details") or {}
    outputs = usage.get("output_tokens_details") or {}
    return {
        "input_tokens": usage.get("input_tokens"),
        "cached_input_tokens": inputs.get("cached_tokens"),
        "cache_write_input_tokens": inputs.get("cache_write_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "reasoning_tokens": outputs.get("reasoning_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def estimate_cost(
    usage: dict[str, int | None],
    prices: dict[str, float] | None,
    *,
    long_context_threshold: int = 272000,
    input_multiplier: float = 2.0,
    output_multiplier: float = 1.5,
) -> float | None:
    """Estimate standard-tier USD from disjoint input categories and all output.

    Reasoning is already part of output_tokens and must not be billed twice.
    Missing billing counters do not silently become zero-cost observations.
    """
    if prices is None:
        return None
    names = (
        "input_tokens",
        "cached_input_tokens",
        "cache_write_input_tokens",
        "output_tokens",
    )
    counts = [usage.get(name) for name in names]
    if any(type(value) is not int or value < 0 for value in counts):
        return None
    inputs, cached, written, outputs = counts
    fresh = inputs - cached - written
    if fresh < 0:
        return None
    long_context = inputs > long_context_threshold
    input_factor = input_multiplier if long_context else 1.0
    output_factor = output_multiplier if long_context else 1.0
    return (
        input_factor
        * (
            fresh * prices["input"]
            + cached * prices["cached_input"]
            + written * prices["cache_write"]
        )
        + output_factor * outputs * prices["output"]
    ) / 1_000_000


class OpenAIResponseStatusError(RuntimeError):
    """The provider returned a response that cannot be executed."""


class OpenAIRequestError(RuntimeError):
    """A transport or API failure whose private response body is not logged."""


class OpenAIResponsesModel(LitellmResponseModel):
    """mini-SWE-agent Model adapter using the official SDK and native bash calls."""

    def __init__(self, **kwargs):
        self.config = OpenAIResponsesModelConfig(**kwargs)
        name = self.config.model_name
        self.api_model = name.removeprefix("openai/")
        if not self.api_model or "/" in self.api_model:
            raise ValueError(
                "Specify an OpenAI model name, optionally prefixed openai/"
            )
        options = copy.deepcopy(self.config.model_kwargs)
        if any(
            key in options for key in ("api_key", "extra_headers", "default_headers")
        ):
            raise ValueError(
                "Read OPENAI_API_KEY from the host environment, not model_kwargs"
            )
        base = options.pop("api_base", OFFICIAL_API_BASE).rstrip("/")
        if base != OFFICIAL_API_BASE:
            raise ValueError(
                "The native OpenAI adapter requires the official API endpoint"
            )
        timeout = options.pop("timeout", 90)
        if options.pop("num_retries", 0) != 0:
            raise ValueError("Responses request accounting requires num_retries=0")
        # mini's bundled config contains this LiteLLM-only switch.
        options.pop("drop_params", None)
        prohibited = {
            "api_base",
            "base_url",
            "api_key",
            "extra_body",
            "extra_headers",
            "default_headers",
            "max_retries",
            "model",
            "input",
            "tools",
            "previous_response_id",
            "conversation",
            "stream",
            "background",
            "max_tokens",
            "max_completion_tokens",
            "reasoning_effort",
        }
        if prohibited & options.keys():
            raise ValueError(
                "Use native Responses parameters without transport or history overrides"
            )
        if options.get("store", False) is not False:
            raise ValueError(
                "This adapter replays complete stateless Responses history"
            )
        if options.get("service_tier", "default") != "default":
            raise ValueError("Pinned cost estimates require service_tier=default")
        options["store"] = False
        options["service_tier"] = "default"
        include = list(options.get("include", []))
        if "reasoning.encrypted_content" not in include:
            include.append("reasoning.encrypted_content")
        options["include"] = include
        options.setdefault("parallel_tool_calls", False)
        options.setdefault("tool_choice", "required")
        self.request_options = options
        prices = self.config.pricing_per_million
        if prices is not None and (
            set(prices) != {"input", "cached_input", "cache_write", "output"}
            or any(not math.isfinite(value) or value < 0 for value in prices.values())
        ):
            raise ValueError(
                "Provide nonnegative finite prices for all four token categories"
            )
        self.client = OpenAI(base_url=base, timeout=timeout, max_retries=0)
        self.api_requests: list[dict[str, Any]] = []
        self.request_index = 0

    def _prepare_messages_for_api(self, messages: list[dict]) -> list[dict]:
        """Replay output protocol fields without SDK-generated null defaults.

        SDK output models populate absent optional fields such as reasoning.status
        with None. Those nulls are not valid Responses input parameters. Preserve
        the original response in the trajectory, including encrypted reasoning and
        assistant phase; normalize only protocol objects when replaying them.
        Function arguments and tool results remain unchanged strings.
        """

        def replay(value):
            if isinstance(value, dict):
                return {
                    key: replay(item)
                    for key, item in value.items()
                    if key != "extra" and item is not None
                }
            if isinstance(value, list):
                return [replay(item) for item in value]
            return value

        prepared = []
        for message in messages:
            if message.get("object") == "response":
                prepared.extend(replay(item) for item in message.get("output", []))
            else:
                prepared.append(
                    {key: value for key, value in message.items() if key != "extra"}
                )
        return prepared

    def _journal(self, record):
        if self.config.request_log_path is None:
            return
        path = self.config.request_log_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def query(self, messages: list[dict], **kwargs) -> dict:
        if kwargs:
            raise ValueError(
                "Set request parameters in model_kwargs before starting the run"
            )
        history = self._prepare_messages_for_api(messages)
        self.request_index += 1
        started_at = datetime.now(timezone.utc).isoformat()
        record = {
            "event": "request_started",
            "request_id": str(uuid.uuid4()),
            "request_index": self.request_index,
            "started_at": started_at,
            "requested_model": self.api_model,
            "reasoning_effort": (self.request_options.get("reasoning") or {}).get(
                "effort"
            ),
            "endpoint": OFFICIAL_API_BASE + "/responses",
        }
        self._journal(record)
        started = time.monotonic()
        bash_tool = copy.deepcopy(BASH_TOOL_RESPONSE_API)
        bash_tool["strict"] = True
        bash_tool["parameters"]["additionalProperties"] = False
        try:
            response = self.client.responses.create(
                model=self.api_model,
                input=history,
                tools=[bash_tool],
                **self.request_options,
            )
        except Exception as exc:  # noqa: BLE001 - journal every failed SDK attempt without its private body
            failed = {
                **record,
                "event": "request_failed",
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": time.monotonic() - started,
                "error_type": type(exc).__name__,
                "http_status": getattr(exc, "status_code", None),
                "response_id": None,
                "returned_model": None,
                "status": "error",
                "usage": None,
                "token_usage": normalize_usage(None),
                "estimated_cost_usd": None,
                "cost_source": "unavailable",
            }
            self.api_requests.append(failed)
            self._journal(failed)
            raise OpenAIRequestError(
                f"{failed['error_type']} (HTTP status {failed['http_status']}); see request telemetry"
            ) from None
        ended_at = datetime.now(timezone.utc).isoformat()
        duration = time.monotonic() - started
        message = (
            response.model_dump(mode="json")
            if hasattr(response, "model_dump")
            else copy.deepcopy(response)
        )
        usage = message.get("usage")
        tokens = normalize_usage(usage)
        cost = estimate_cost(
            tokens,
            self.config.pricing_per_million,
            long_context_threshold=self.config.long_context_threshold,
            input_multiplier=self.config.long_context_input_multiplier,
            output_multiplier=self.config.long_context_output_multiplier,
        )
        completed = {
            **record,
            "event": "request_completed",
            "ended_at": ended_at,
            "duration_seconds": duration,
            "response_id": message.get("id"),
            "returned_model": message.get("model"),
            "status": message.get("status"),
            "incomplete_reason": (message.get("incomplete_details") or {}).get(
                "reason"
            ),
            "service_tier": message.get("service_tier"),
            "usage": usage,
            "token_usage": tokens,
            "estimated_cost_usd": cost,
            "cost_source": "pinned_standard_prices"
            if cost is not None
            else "unavailable",
            "pricing_per_million": self.config.pricing_per_million,
        }
        self.api_requests.append(completed)
        self._journal(completed)
        message["extra"] = {
            "actions": [],
            "cost": cost if cost is not None else 0.0,
            "estimated_cost_usd": cost,
            "token_usage": tokens,
            "api_timing": completed,
            "timestamp": time.time(),
        }
        GLOBAL_MODEL_STATS.add(message["extra"]["cost"])
        if message.get("status") not in {"completed", "incomplete"}:
            raise OpenAIResponseStatusError(
                f"OpenAI response has non-executable status: {message.get('status')}"
            )
        try:
            actions = parse_toolcall_actions_response(
                message.get("output", []),
                format_error_template=self.config.format_error_template,
                template_kwargs={
                    "finish_reason": finish_reason_from_responses_api(message)
                },
            )
            if any(
                not isinstance(action["command"], str)
                or not isinstance(action["tool_call_id"], str)
                or not action["tool_call_id"]
                for action in actions
            ) or len({action["tool_call_id"] for action in actions}) != len(actions):
                raise FormatError(
                    {
                        "role": "user",
                        "content": "Each bash call needs a string command and a unique nonempty call_id.",
                        "extra": {"interrupt_type": "FormatError"},
                    }
                )
        except FormatError as exc:
            # Preserve billed reasoning/output even when no command can run. Close
            # valid call IDs with error observations before asking for a new call.
            outputs = []
            seen = set()
            for item in message.get("output", []):
                call_id = item.get("call_id")
                if (
                    item.get("type") == "function_call"
                    and isinstance(call_id, str)
                    and call_id
                    and call_id not in seen
                ):
                    outputs.append(
                        {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": "The tool call was not executed because the response contained an invalid bash call.",
                        }
                    )
                    seen.add(call_id)
            raise FormatError(message, *outputs, *exc.messages) from exc
        message["extra"]["actions"] = actions
        return message

    def serialize(self) -> dict:
        result = super().serialize()
        result["info"]["api_requests"] = copy.deepcopy(self.api_requests)
        return result
