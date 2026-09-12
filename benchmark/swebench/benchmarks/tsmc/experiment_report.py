"""Aggregate experiment evidence without treating missing accounting as free usage."""

from __future__ import annotations

from collections import Counter
from math import isfinite

TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "reasoning_tokens",
    "total_tokens",
)

ACCOUNTING_NOTES = [
    "Costs are estimates from recorded API responses or mini-SWE-agent metadata, not invoices.",
    "Cached input tokens are included in input tokens; reasoning tokens are included in output tokens.",
    "Observed totals sum available evidence; failed or interrupted requests can leave billable usage unknown.",
    "Agent queries and HTTP requests are separate counts; legacy trajectories do not expose retries.",
    "Total task time combines solver startup, inference, cleanup and grading; solve_total_seconds excludes grading.",
]


def _number(value):
    return (
        value
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and value >= 0
        else None
    )


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _usage(raw):
    raw = _mapping(raw)
    inputs = _mapping(raw.get("input_tokens_details", raw.get("prompt_tokens_details")))
    outputs = _mapping(
        raw.get("output_tokens_details", raw.get("completion_tokens_details"))
    )
    result = {
        "input_tokens": _number(raw.get("input_tokens", raw.get("prompt_tokens"))),
        "output_tokens": _number(
            raw.get("output_tokens", raw.get("completion_tokens"))
        ),
        "cached_input_tokens": _number(
            raw.get("cached_input_tokens", inputs.get("cached_tokens"))
        ),
        "cache_write_input_tokens": _number(
            raw.get("cache_write_input_tokens", inputs.get("cache_write_tokens"))
        ),
        "reasoning_tokens": _number(
            raw.get("reasoning_tokens", outputs.get("reasoning_tokens"))
        ),
        "total_tokens": _number(raw.get("total_tokens")),
    }
    if (
        result["total_tokens"] is None
        and result["input_tokens"] is not None
        and result["output_tokens"] is not None
    ):
        result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
    return result


def _ledger_records(events):
    requests = {}
    conflicts = False
    for index, raw in enumerate(events):
        event = _mapping(raw)
        kind = event.get("event")
        if kind not in {"request_started", "request_completed", "request_failed"}:
            conflicts = True
            continue
        if not event.get("request_id"):
            conflicts = True
        identifier = event.get("request_id") or f"missing-id-{index}"
        record = requests.setdefault(identifier, {})
        if kind == "request_started":
            record.setdefault("started", event)
        else:
            if "terminal" in record and record["terminal"] != event:
                conflicts = True
            record["terminal"] = event
    completed, failed, incomplete = [], [], 0
    for record in requests.values():
        terminal = record.get("terminal")
        if terminal is None:
            incomplete += 1
        elif terminal["event"] == "request_completed":
            completed.append(terminal)
        else:
            failed.append(terminal)
    records = [
        {
            "usage": _usage(event.get("token_usage") or event.get("usage")),
            "cost": _number(event.get("estimated_cost_usd")),
            "model": event.get("returned_model"),
        }
        for event in completed
    ]
    return records, {
        "request_count": len(requests),
        "failed_request_count": len(failed),
        "incomplete_request_count": incomplete,
        "request_error_types": sorted(
            {
                event["error_type"]
                for event in failed
                if isinstance(event.get("error_type"), str)
            }
        ),
        "accounting_conflict": conflicts,
        "complete": not failed and not incomplete and not conflicts,
    }


def _trajectory_records(trajectory):
    records, seen = [], set()
    messages = trajectory.get("messages", [])
    for raw in messages if isinstance(messages, list) else []:
        message = _mapping(raw)
        extra = _mapping(message.get("extra"))
        response = (
            message
            if message.get("object") == "response"
            else _mapping(extra.get("response"))
        )
        if not response:
            continue
        identifier = response.get("id")
        if identifier and identifier in seen:
            continue
        if identifier:
            seen.add(identifier)
        records.append(
            {
                "usage": _usage(extra.get("token_usage") or response.get("usage")),
                "cost": _number(extra.get("estimated_cost_usd", extra.get("cost"))),
                "explicit_cost_estimate": "estimated_cost_usd" in extra,
                "model": response.get("model"),
            }
        )
    return records


def _accounting(trajectory, request_events):
    info = _mapping(trajectory.get("info"))
    stats = _mapping(info.get("model_stats"))
    queries = _number(stats.get("api_calls"))
    if request_events is None and isinstance(info.get("api_requests"), list):
        request_events = info["api_requests"]
    if request_events is not None:
        records, requests = _ledger_records(request_events)
        complete = requests.pop("complete")
        recorded_queries = queries if queries is not None else 0
        known_responses = len(_trajectory_records(trajectory))
        if max(recorded_queries, known_responses) > requests["request_count"]:
            requests["accounting_conflict"] = True
            complete = False
        source = "api_request_ledger"
    else:
        records = _trajectory_records(trajectory)
        complete = queries is not None and queries == len(records)
        source = "trajectory_responses"
        requests = dict(
            request_count=None,
            failed_request_count=None,
            incomplete_request_count=None,
            request_error_types=[],
            accounting_conflict=False,
        )
    observed_usage, usage, completeness = {}, {}, {}
    for field in TOKEN_FIELDS:
        known = [
            record["usage"][field]
            for record in records
            if record["usage"][field] is not None
        ]
        observed_usage[field] = sum(known) if known or complete else None
        completeness[field] = complete and len(known) == len(records)
        usage[field] = sum(known) if completeness[field] else None
    costs = [record["cost"] for record in records if record["cost"] is not None]
    cost_complete = complete and len(costs) == len(records)
    observed_cost = sum(costs) if costs or complete else None
    cost_source = source
    if (
        request_events is None
        and not any(
            record.get("explicit_cost_estimate") and record["cost"] is None
            for record in records
        )
        and (reported_cost := _number(stats.get("instance_cost"))) is not None
    ):
        observed_cost = reported_cost
        cost_source = "mini_model_stats"
        cost_complete = complete
        model = _mapping(_mapping(info.get("config")).get("model"))
        if model.get("cost_tracking") == "ignore_errors" and reported_cost == 0:
            cost_complete = False
    return {
        **requests,
        "agent_query_count": queries,
        "response_count": len(records),
        "response_models": sorted(
            {
                record["model"]
                for record in records
                if isinstance(record.get("model"), str)
            }
        ),
        "usage": usage,
        "observed_usage": observed_usage,
        "usage_completeness": completeness,
        "usage_complete": all(
            completeness[field]
            for field in ("input_tokens", "output_tokens", "total_tokens")
        ),
        "estimated_cost_usd": observed_cost if cost_complete else None,
        "observed_cost_usd": observed_cost,
        "cost_estimate_complete": cost_complete,
        "cost_source": cost_source,
    }


def _failure_category(status, evaluation, timing, accounting, has_trajectory):
    if evaluation.get("resolved") is True:
        return None
    if (
        status in {"NotStarted", "Pending"}
        and not evaluation
        and not accounting["failed_request_count"]
    ):
        return "pending"
    if (
        timing.get("patch_collection_error")
        or status == "PatchCollectionError"
        or evaluation.get("status") == "submission_mismatch"
    ):
        return "submission_error"
    if (
        timing.get("hard_timeout")
        or any(
            name in {"Timeout", "TimeoutError", "APITimeoutError"}
            for name in accounting["request_error_types"]
        )
        or status
        in {
            "HardTimeout",
            "TimeExceeded",
            "Timeout",
            "TimeoutError",
            "APITimeoutError",
        }
    ):
        return "timeout"
    if status in {"LimitsExceeded", "CostLimitExceeded"}:
        return "budget_exhausted"
    if status in {"FormatError", "RepeatedFormatError"}:
        return "format_error"
    if status in {"InvalidTrajectory", "IncompleteTrajectory"} or timing.get(
        "trajectory_error"
    ):
        return "invalid_trajectory"
    if status in {
        "AuthenticationError",
        "PermissionDeniedError",
        "NotFoundError",
        "BadRequestError",
        "RateLimitError",
        "APIConnectionError",
        "APIError",
        "InternalServerError",
        "UnsupportedParamsError",
        "OpenAIRequestError",
    }:
        return "api_error"
    if status not in {"Submitted", "NoChanges"} and accounting["failed_request_count"]:
        return "api_error"
    if status == "NoChanges" or evaluation.get("status") in {
        "empty_patch",
        "empty_submission",
    }:
        return "empty_submission"
    if evaluation.get("infra_failure") or evaluation.get("status") in {
        "error",
        "infra_error",
        "evaluation_error",
        "grading_error",
        "infrastructure_failure",
    }:
        return "evaluation_error"
    if evaluation.get("patch_applied") is False:
        return "patch_apply_error"
    if evaluation.get("resolved") is False:
        return "test_failure"
    if status == "Submitted":
        if timing.get("nonempty_submission") is False:
            return "empty_submission"
        return "evaluation_pending"
    if status == "OpenAIResponseStatusError":
        return "execution_error"
    if status == "MissingTrajectory" or not has_trajectory:
        return "missing_trajectory"
    return "execution_error"


def summarize_trial(
    instance_id, *, timing=None, trajectory=None, evaluation=None, request_events=None
):
    """Summarize one trial using allowlisted metrics, without messages or credentials.

    ``evaluation`` is a per-trial mapping with resolved, status, grading_seconds,
    patch_applied, tests_passed, tests_failed and tests_total when available.
    ``request_events`` is the adapter JSONL journal parsed as a list of mappings.
    """
    timing, trajectory, evaluation = map(_mapping, (timing, trajectory, evaluation))
    info = _mapping(trajectory.get("info"))
    status = timing.get("exit_status") or info.get("exit_status") or "NotStarted"
    accounting = _accounting(trajectory, request_events)
    resolved = evaluation.get("resolved")
    if not isinstance(resolved, bool):
        resolved = None
    inference_seconds = _number(timing.get("inference_seconds"))
    solve_seconds = _number(timing.get("total_seconds"))
    grading_seconds = _number(evaluation.get("grading_seconds"))
    cleanup_seconds = (
        solve_seconds - inference_seconds
        if solve_seconds is not None
        and inference_seconds is not None
        and solve_seconds >= inference_seconds
        else None
    )
    return {
        "instance_id": instance_id,
        "inference_status": status,
        "evaluation_status": evaluation.get("status", "not_run"),
        "resolved": resolved,
        "failure_category": _failure_category(
            status, evaluation, timing, accounting, bool(trajectory)
        ),
        "inference_seconds": inference_seconds,
        "solve_total_seconds": solve_seconds,
        "cleanup_seconds": cleanup_seconds,
        "total_seconds": (
            solve_seconds + grading_seconds
            if solve_seconds is not None and grading_seconds is not None
            else None
        ),
        "grading_seconds": grading_seconds,
        "patch_applied": evaluation.get("patch_applied")
        if isinstance(evaluation.get("patch_applied"), bool)
        else None,
        "nonempty_submission": timing.get("nonempty_submission")
        if isinstance(timing.get("nonempty_submission"), bool)
        else None,
        "tests_passed": _number(evaluation.get("tests_passed")),
        "tests_failed": _number(evaluation.get("tests_failed")),
        "tests_total": _number(evaluation.get("tests_total")),
        **accounting,
    }


def _totals(records, field, expected_tasks=None):
    values = [_number(record.get(field)) for record in records]
    known = [value for value in values if value is not None]
    return {
        "total": sum(known)
        if len(known) == len(values)
        and len(records) == (expected_tasks or len(records))
        else None,
        "observed": sum(known),
        "known_trials": len(known),
    }


def summarize_condition(records, expected_tasks=10):
    """Keep requested trials in the accuracy denominator, including execution failures."""
    if (
        not isinstance(expected_tasks, int)
        or isinstance(expected_tasks, bool)
        or expected_tasks <= 0
    ):
        raise ValueError("expected_tasks must be a positive integer")
    if len(records) > expected_tasks:
        raise ValueError("More trial records than requested tasks")
    ids = [record["instance_id"] for record in records]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate instance_id in one condition")

    def is_pending(record):
        if record.get("state") == "completed":
            return False
        return (
            record.get("state") in {"pending", "running"}
            or record.get("inference_status") in {"Pending", "NotStarted"}
            or record.get("failure_category") in {"pending", "evaluation_pending"}
        )

    pending = sum(is_pending(record) for record in records)
    completed = len(records) - pending
    graded = [
        record
        for record in records
        if isinstance(record.get("resolved"), bool)
        and record.get("failure_category") in {None, "test_failure"}
    ]
    resolved = sum(record.get("resolved") is True for record in records)
    failure_counts = Counter(
        record["failure_category"]
        for record in records
        if record.get("failure_category") not in {None, "pending", "evaluation_pending"}
    )
    token_totals = {}
    observed_tokens = {}
    for field in TOKEN_FIELDS:
        values = [_mapping(record.get("usage")).get(field) for record in records]
        token_totals[field] = (
            sum(values)
            if len(records) == expected_tasks
            and all(_number(value) is not None for value in values)
            else None
        )
        observed_tokens[field] = sum(
            _number(_mapping(record.get("observed_usage")).get(field)) or 0
            for record in records
        )
    cost = _totals(records, "estimated_cost_usd", expected_tasks)
    return {
        "expected_tasks": expected_tasks,
        "recorded_tasks": len(records),
        "completed_tasks": completed,
        "pending_tasks": expected_tasks - completed,
        "graded_tasks": len(graded),
        "resolved_tasks": resolved,
        "accuracy": resolved / expected_tasks,
        "accuracy_complete": completed == expected_tasks,
        "grading_accuracy": resolved / len(graded) if graded else None,
        "provisional": completed != expected_tasks,
        "failure_counts": dict(sorted(failure_counts.items())),
        "inference_time": _totals(records, "inference_seconds", expected_tasks),
        "solve_total_time": _totals(records, "solve_total_seconds", expected_tasks),
        "cleanup_time": _totals(records, "cleanup_seconds", expected_tasks),
        "total_time": _totals(records, "total_seconds", expected_tasks),
        "grading_time": _totals(records, "grading_seconds", expected_tasks),
        "usage": token_totals,
        "observed_usage": observed_tokens,
        "usage_complete": len(records) == expected_tasks
        and all(record.get("usage_complete") is True for record in records),
        "estimated_cost_usd": cost["total"] if len(records) == expected_tasks else None,
        "observed_cost_usd": sum(
            _number(record.get("observed_cost_usd")) or 0 for record in records
        ),
        "cost_estimate_complete": len(records) == expected_tasks
        and all(record.get("cost_estimate_complete") is True for record in records),
        "cost_known_trials": cost["known_trials"],
        "accounting_notes": list(ACCOUNTING_NOTES),
    }
