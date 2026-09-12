# F03 Test matrix

| Test ID | Visibility | baseline -> reference |
|---|---|---|
| `assessment/tests/test_hidden.py::test_bad_state_rejected` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_batch_incremental_equivalence` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_clock_not_ordering_key` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_equal_sequence_conflict` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_hidden_cli_fixture` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_initial_state_protected` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_inputs_unchanged_on_conflict` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_multiple_machines_out_of_order` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_negative_sequence_rejected` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_permutation_unique_sequences` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_replay_no_effect` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_stale_conflict_not_current_is_ignored` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_zero_sequence` | hidden | PASS → PASS |
| `tests/test_public.py::test_empty` | public | PASS → PASS |
| `tests/test_public.py::test_in_order` | public | PASS → PASS |
| `tests/test_public.py::test_independent_machines` | public | PASS → PASS |
| `tests/test_public.py::test_late_older_event` | public | FAIL → PASS |
| `tests/test_public.py::test_public_cli_fixture` | public | FAIL → PASS |
