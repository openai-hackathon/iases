"""Keep experiment verdicts, API accounting and incomplete trials distinguishable."""

import copy

import pytest

from swebench.benchmarks.tsmc.experiment_report import (
    summarize_condition,
    summarize_trial,
)


def completed_request(identifier="r1", *, cost=0.01, usage=None):
    return {
        "event": "request_completed",
        "request_id": identifier,
        "returned_model": "example-model",
        "estimated_cost_usd": cost,
        "token_usage": usage
        if usage is not None
        else {
            "input_tokens": 100,
            "output_tokens": 30,
            "cached_input_tokens": 70,
            "cache_write_input_tokens": 0,
            "reasoning_tokens": 20,
            "total_tokens": 130,
        },
    }


def successful_trial(identifier="task-1"):
    return summarize_trial(
        identifier,
        timing={
            "exit_status": "Submitted",
            "inference_seconds": 10,
            "total_seconds": 11,
            "nonempty_submission": True,
        },
        trajectory={"info": {"model_stats": {"api_calls": 1}}},
        evaluation={
            "resolved": True,
            "status": "resolved",
            "grading_seconds": 2,
            "patch_applied": True,
            "tests_passed": 12,
            "tests_failed": 0,
            "tests_total": 12,
        },
        request_events=[completed_request()],
    )


def test_returned_ledger_usage_is_not_double_counted_with_trajectory():
    event = completed_request()
    events = [
        {"event": "request_started", "request_id": "r1"},
        event,
        copy.deepcopy(event),
    ]
    trajectory = {
        "info": {"model_stats": {"api_calls": 1, "instance_cost": 9}},
        "messages": [
            {"object": "response", "id": "response-1", "usage": {"input_tokens": 999}}
        ],
    }
    before = copy.deepcopy(events)
    result = summarize_trial("task", trajectory=trajectory, request_events=events)
    assert result["request_count"] == result["response_count"] == 1
    assert result["estimated_cost_usd"] == 0.01
    assert result["usage"]["input_tokens"] == 100
    assert result["usage"]["output_tokens"] == 30
    assert result["usage"]["total_tokens"] == 130
    assert result["usage"]["cached_input_tokens"] == 70
    assert result["usage"]["reasoning_tokens"] == 20
    assert result["usage_complete"] is True
    assert events == before


def test_failed_and_interrupted_requests_leave_strict_totals_unknown():
    result = summarize_trial(
        "task",
        timing={"exit_status": "HardTimeout", "hard_timeout": True},
        request_events=[
            completed_request(),
            {
                "event": "request_failed",
                "request_id": "r2",
                "error_type": "RateLimitError",
            },
            {"event": "request_started", "request_id": "r3"},
        ],
    )
    assert result["request_count"] == 3
    assert (
        result["response_count"]
        == result["failed_request_count"]
        == result["incomplete_request_count"]
        == 1
    )
    assert result["estimated_cost_usd"] is None
    assert result["observed_cost_usd"] == 0.01
    assert result["usage"]["input_tokens"] is None
    assert result["observed_usage"]["input_tokens"] == 100
    assert result["cost_estimate_complete"] is result["usage_complete"] is False
    assert result["failure_category"] == "timeout"


def test_missing_usage_is_not_reported_as_zero():
    result = summarize_trial(
        "task", request_events=[completed_request(cost=None, usage={})]
    )
    assert result["response_count"] == 1
    assert result["usage"]["input_tokens"] is None
    assert result["estimated_cost_usd"] is None
    assert result["usage_complete"] is result["cost_estimate_complete"] is False


def test_explicit_empty_request_journal_means_no_api_usage_yet():
    result = summarize_trial("task", request_events=[])
    assert result["failure_category"] == "pending"
    assert result["request_count"] == 0
    assert result["estimated_cost_usd"] == 0
    assert result["usage"]["input_tokens"] == 0
    unknown = summarize_trial("unknown")
    assert unknown["request_count"] is None
    assert unknown["estimated_cost_usd"] is None
    assert unknown["usage"]["input_tokens"] is None


@pytest.mark.parametrize(
    "trajectory",
    [
        {"info": {"model_stats": {"api_calls": 1, "instance_cost": 0.01}}},
        {
            "messages": [
                {
                    "object": "response",
                    "id": "paid-response",
                    "usage": {"input_tokens": 100, "output_tokens": 20},
                }
            ]
        },
    ],
)
def test_empty_journal_cannot_override_evidence_that_a_query_occurred(trajectory):
    result = summarize_trial("task", trajectory=trajectory, request_events=[])
    assert result["accounting_conflict"] is True
    assert result["cost_estimate_complete"] is result["usage_complete"] is False
    assert result["estimated_cost_usd"] is None
    assert result["usage"]["input_tokens"] is None


def test_truncated_journal_preserves_known_subtotal_but_not_complete_usage():
    result = summarize_trial(
        "task",
        trajectory={"info": {"model_stats": {"api_calls": 2}}},
        request_events=[completed_request()],
    )
    assert result["accounting_conflict"] is True
    assert result["request_count"] == 1
    assert result["agent_query_count"] == 2
    assert result["estimated_cost_usd"] is None
    assert result["observed_cost_usd"] == 0.01
    assert result["usage"]["input_tokens"] is None
    assert result["observed_usage"]["input_tokens"] == 100


def test_responses_api_objects_and_chat_format_errors_are_both_accounted():
    trajectory = {
        "info": {"model_stats": {"api_calls": 2, "instance_cost": 0.03}},
        "messages": [
            {
                "object": "response",
                "id": "one",
                "model": "responses-model",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "input_tokens_details": {"cached_tokens": 2},
                    "output_tokens_details": {"reasoning_tokens": 3},
                },
                "extra": {"estimated_cost_usd": 0.01},
            },
            {
                "role": "user",
                "extra": {
                    "interrupt_type": "FormatError",
                    "cost": 0.02,
                    "response": {
                        "id": "two",
                        "model": "chat-model",
                        "usage": {
                            "prompt_tokens": 20,
                            "completion_tokens": 7,
                            "prompt_tokens_details": {"cached_tokens": 6},
                            "completion_tokens_details": {"reasoning_tokens": 4},
                        },
                    },
                },
            },
        ],
    }
    result = summarize_trial("task", trajectory=trajectory)
    assert result["usage"]["input_tokens"] == 30
    assert result["usage"]["output_tokens"] == 12
    assert result["usage"]["total_tokens"] == 42
    assert result["usage"]["cached_input_tokens"] == 8
    assert result["usage"]["reasoning_tokens"] == 7
    assert result["estimated_cost_usd"] == 0.03
    assert result["cost_source"] == "mini_model_stats"
    assert result["agent_query_count"] == 2
    assert result["request_count"] is None
    assert result["response_models"] == ["chat-model", "responses-model"]


def test_legacy_response_gap_censors_cost_and_usage():
    trajectory = {
        "info": {
            "exit_status": "Timeout",
            "model_stats": {"api_calls": 2, "instance_cost": 0.01},
        },
        "messages": [
            {
                "extra": {
                    "cost": 0.01,
                    "response": {
                        "id": "r",
                        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
                    },
                }
            }
        ],
    }
    result = summarize_trial("task", trajectory=trajectory)
    assert result["estimated_cost_usd"] is None
    assert result["observed_cost_usd"] == 0.01
    assert result["usage"]["input_tokens"] is None
    assert result["observed_usage"]["input_tokens"] == 10


def test_adapter_unknown_cost_is_not_overridden_by_mini_compatibility_zero():
    trajectory = {
        "info": {"model_stats": {"api_calls": 1, "instance_cost": 0}},
        "messages": [
            {
                "object": "response",
                "id": "r",
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "extra": {"cost": 0, "estimated_cost_usd": None},
            }
        ],
    }
    result = summarize_trial("task", trajectory=trajectory)
    assert result["usage_complete"] is True
    assert result["estimated_cost_usd"] is None
    assert result["cost_estimate_complete"] is False
    assert result["cost_source"] == "trajectory_responses"


def test_conflicting_or_malformed_journal_cannot_claim_complete_accounting():
    for events in (
        [completed_request(), completed_request(cost=0.9)],
        [{"event": "unrecognized"}],
        [{"event": "request_completed", "token_usage": {"input_tokens": 1}}],
    ):
        result = summarize_trial("task", request_events=events)
        assert result["accounting_conflict"] is True
        assert result["cost_estimate_complete"] is result["usage_complete"] is False


@pytest.mark.parametrize(
    "status,category",
    [
        ("NotFoundError", "api_error"),
        ("BadRequestError", "api_error"),
        ("LimitsExceeded", "budget_exhausted"),
        ("RepeatedFormatError", "format_error"),
        ("PatchCollectionError", "submission_error"),
        ("NoChanges", "empty_submission"),
        ("InvalidTrajectory", "invalid_trajectory"),
        ("MissingTrajectory", "missing_trajectory"),
    ],
)
def test_inference_failures_are_not_classified_as_incorrect_repairs(status, category):
    result = summarize_trial(
        "task", timing={"exit_status": status}, evaluation={"resolved": None}
    )
    assert result["resolved"] is None
    assert result["failure_category"] == category


def test_evaluator_verdict_is_independent_of_inference_timeout():
    result = summarize_trial(
        "task",
        timing={"exit_status": "HardTimeout", "hard_timeout": True},
        evaluation={"resolved": True, "status": "resolved"},
    )
    assert result["resolved"] is True
    assert result["failure_category"] is None
    assert result["inference_status"] == "HardTimeout"


def test_grader_failure_and_patch_rejection_are_distinct_from_test_failure():
    timing = {"exit_status": "Submitted", "nonempty_submission": True}
    for evaluation, category in (
        ({"status": "evaluation_error"}, "evaluation_error"),
        ({"status": "infrastructure_failure"}, "evaluation_error"),
        ({"status": "submission_mismatch"}, "submission_error"),
        ({"resolved": False, "patch_applied": False}, "patch_apply_error"),
        ({"resolved": False, "patch_applied": True}, "test_failure"),
    ):
        assert (
            summarize_trial("task", timing=timing, evaluation=evaluation)[
                "failure_category"
            ]
            == category
        )


def test_total_task_time_includes_grading_without_hiding_solver_and_cleanup():
    result = successful_trial()
    assert result["inference_seconds"] == 10
    assert result["cleanup_seconds"] == 1
    assert result["solve_total_seconds"] == 11
    assert result["grading_seconds"] == 2
    assert result["total_seconds"] == 13
    without_grade = summarize_trial(
        "task", timing={"inference_seconds": 10, "total_seconds": 11}
    )
    assert without_grade["solve_total_seconds"] == 11
    assert without_grade["total_seconds"] is None


def test_adapter_error_types_remain_distinct_when_the_exception_is_sanitized():
    timeout = summarize_trial(
        "task",
        timing={"exit_status": "OpenAIRequestError"},
        request_events=[
            {
                "event": "request_failed",
                "request_id": "r",
                "error_type": "APITimeoutError",
            }
        ],
    )
    assert timeout["failure_category"] == "timeout"
    failed_response = summarize_trial(
        "task",
        timing={"exit_status": "OpenAIResponseStatusError"},
        request_events=[completed_request()],
    )
    assert failed_response["failure_category"] == "execution_error"


def test_pending_placeholders_keep_accuracy_provisional_and_requested_denominator():
    complete = successful_trial()
    error = summarize_trial(
        "task-2",
        timing={"exit_status": "NotFoundError"},
        evaluation={"resolved": None, "status": "not_run"},
    )
    error["state"] = "completed"
    pending = {
        "instance_id": "task-3",
        "inference_status": "Pending",
        "evaluation_status": "pending",
        "resolved": None,
    }
    summary = summarize_condition([complete, error, pending], expected_tasks=3)
    assert summary["accuracy"] == 1 / 3
    assert summary["grading_accuracy"] == 1
    assert summary["completed_tasks"] == 2
    assert summary["pending_tasks"] == 1
    assert summary["accuracy_complete"] is False
    assert summary["provisional"] is True
    assert summary["failure_counts"] == {"api_error": 1}
    assert summary["estimated_cost_usd"] is None
    assert summary["observed_cost_usd"] == 0.01
    assert summary["usage"]["input_tokens"] is None
    assert summary["observed_usage"]["input_tokens"] == 100


def test_completed_condition_totals_and_accuracy():
    records = [successful_trial("one"), successful_trial("two")]
    records[1].update(resolved=False, failure_category="test_failure")
    summary = summarize_condition(records, expected_tasks=2)
    assert summary["accuracy"] == summary["grading_accuracy"] == 0.5
    assert summary["accuracy_complete"] is True
    assert summary["provisional"] is False
    assert summary["estimated_cost_usd"] == 0.02
    assert summary["usage"]["input_tokens"] == 200
    assert summary["usage"]["output_tokens"] == 60
    assert summary["usage"]["total_tokens"] == 260
    assert summary["inference_time"] == {"total": 20, "observed": 20, "known_trials": 2}
    assert summary["grading_time"]["total"] == 4


def test_unrecorded_tasks_do_not_turn_partial_duration_into_complete_total():
    summary = summarize_condition([successful_trial()], expected_tasks=10)
    assert summary["pending_tasks"] == 9
    assert summary["inference_time"]["total"] is None
    assert summary["inference_time"]["observed"] == 10


def test_duplicate_trials_and_invalid_denominators_are_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_condition([successful_trial(), successful_trial()])
    with pytest.raises(ValueError, match="More trial"):
        summarize_condition(
            [successful_trial("a"), successful_trial("b")], expected_tasks=1
        )
    with pytest.raises(ValueError, match="positive integer"):
        summarize_condition([], expected_tasks=0)


def test_invalid_numbers_and_unrecognized_resolved_values_are_not_truthy_success():
    result = summarize_trial(
        "task",
        timing={"inference_seconds": float("nan"), "total_seconds": -1},
        evaluation={"resolved": "false", "tests_passed": True},
        request_events=[
            completed_request(
                cost=float("inf"), usage={"input_tokens": -2, "output_tokens": True}
            )
        ],
    )
    assert result["inference_seconds"] is result["total_seconds"] is None
    assert result["resolved"] is result["tests_passed"] is None
    assert result["estimated_cost_usd"] is None
    assert result["usage"]["input_tokens"] is result["usage"]["output_tokens"] is None
