# R03 Test matrix

| Test ID | Visibility | baseline -> reference |
|---|---|---|
| `assessment/tests/test_hidden.py::test_append_new_suffix` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_every_fault_location[1-after_checkpoint]` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_every_fault_location[1-after_output]` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_every_fault_location[2-after_checkpoint]` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_every_fault_location[2-after_output]` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_every_fault_location[3-after_checkpoint]` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_every_fault_location[3-after_output]` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_hidden_cli_fixture` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_invalid_order_atomic` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_invalid_zero_sequence` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_no_duplicates_after_replay` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_noncontiguous_ordered_source` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_progress_survives_reinitialize` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_repeated_crash_same_event` | hidden | FAIL → PASS |
| `tests/test_public.py::test_crash_then_resume_no_loss` | public | FAIL → PASS |
| `tests/test_public.py::test_empty` | public | PASS → PASS |
| `tests/test_public.py::test_normal` | public | PASS → PASS |
| `tests/test_public.py::test_public_cli_fixture` | public | FAIL → PASS |
| `tests/test_public.py::test_replay` | public | PASS → PASS |
