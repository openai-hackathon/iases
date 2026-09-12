# R04 Test matrix

| Test ID | Visibility | baseline -> reference |
|---|---|---|
| `assessment/tests/test_hidden.py::test_callback_type_error_cleanup` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_cancel_before_start` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_concurrency_ceiling` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_exception_then_next_job` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_hidden_cli_fixture` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_internal_cancelled_error` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_limits_reject_bool_negative_float` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_many_successes_no_double_release` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_running_task_cancellation_cleanup` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_success_result_preserved` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_waiter_cancellation_does_not_release_owner_slot` | hidden | PASS → PASS |
| `tests/test_public.py::test_error_releases_slot` | public | FAIL → PASS |
| `tests/test_public.py::test_invalid_limit` | public | PASS → PASS |
| `tests/test_public.py::test_normal_result` | public | PASS → PASS |
| `tests/test_public.py::test_public_cli_fixture` | public | FAIL → PASS |
