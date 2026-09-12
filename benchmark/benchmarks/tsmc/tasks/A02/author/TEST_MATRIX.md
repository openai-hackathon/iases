# A02 Test matrix

| Test ID | Visibility | baseline -> reference |
|---|---|---|
| `assessment/tests/test_hidden.py::test_bad_valid_outcome` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_empty_requested_lot` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_exact_duplicate_invariant` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_hidden_cli_fixture` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_independent_oracle_generated` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_input_not_mutated` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_later_invalid_not_selected` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_latest_fail_replaces_pass` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_lexical_tie_break` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_lot_order_deduplicated` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_timestamp_requires_offset` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_unsorted` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_utc_instant_tie` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_wafer_id_scoped_to_lot` | hidden | PASS → PASS |
| `tests/test_public.py::test_invalid_row_excluded` | public | PASS → PASS |
| `tests/test_public.py::test_latest_wafer_result` | public | FAIL → PASS |
| `tests/test_public.py::test_no_data` | public | PASS → PASS |
| `tests/test_public.py::test_no_retest` | public | PASS → PASS |
| `tests/test_public.py::test_public_cli_fixture` | public | FAIL → PASS |
