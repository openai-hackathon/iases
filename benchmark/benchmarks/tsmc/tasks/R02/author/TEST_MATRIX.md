# R02 Test matrix

| Test ID | Visibility | baseline -> reference |
|---|---|---|
| `assessment/tests/test_hidden.py::test_deterministic_interleaving_repeated` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_different_machine_capacities` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_double_release` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_failure_rolls_back` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_hidden_cli_fixture` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_id_conflict` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_invalid_units` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_multiunit_race` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_release_restores_capacity` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_repeated_id_idempotent` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_three_contenders_two_slots` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_unknown_machine` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_zero_capacity` | hidden | PASS → PASS |
| `tests/test_public.py::test_public_cli_fixture` | public | PASS → PASS |
| `tests/test_public.py::test_release` | public | PASS → PASS |
| `tests/test_public.py::test_sequential_full` | public | PASS → PASS |
| `tests/test_public.py::test_simultaneous_capacity_one` | public | FAIL → PASS |
| `tests/test_public.py::test_single_reservation` | public | PASS → PASS |
