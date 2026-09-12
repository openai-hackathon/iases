# F01 Test matrix

| Test ID | Visibility | baseline -> reference |
|---|---|---|
| `assessment/tests/test_hidden.py::test_distinct_ids_no_hardcoding` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_duplicate_row_no_effect` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_hidden_cli_fixture` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_hold_not_overridden_by_qualification` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_input_not_mutated` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_missing_records_fail_closed` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_no_qualification` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_qualification_machine_isolation` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_revoked_only` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_truth_table` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_unknown_machine` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_wrong_product` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_wrong_step` | hidden | PASS → PASS |
| `tests/test_public.py::test_hold_blocks_assignment` | public | FAIL → PASS |
| `tests/test_public.py::test_legal_assignment` | public | PASS → PASS |
| `tests/test_public.py::test_machine_offline` | public | PASS → PASS |
| `tests/test_public.py::test_public_cli_fixture` | public | FAIL → PASS |
| `tests/test_public.py::test_unknown_lot` | public | PASS → PASS |
