# R01 Test matrix

| Test ID | Visibility | baseline -> reference |
|---|---|---|
| `assessment/tests/test_hidden.py::test_concurrent_same_key` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_conflict_does_not_create_order` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_different_machine_conflict` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_distinct_keys_same_payload_distinct_operations` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_empty_key` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_failed_validation_has_no_effect` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_hidden_cli_fixture` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_lost_response_retry` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_many_replays_one_order` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_payload_key_order_irrelevant` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_reopen_persists_idempotency` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_special_characters_in_key` | hidden | FAIL → PASS |
| `tests/test_public.py::test_fresh_key` | public | PASS → PASS |
| `tests/test_public.py::test_public_cli_fixture` | public | FAIL → PASS |
| `tests/test_public.py::test_receipt_lookup` | public | PASS → PASS |
| `tests/test_public.py::test_repeated_key_same_order` | public | FAIL → PASS |
| `tests/test_public.py::test_unknown_receipt` | public | PASS → PASS |
