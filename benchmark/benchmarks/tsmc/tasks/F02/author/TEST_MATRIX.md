# F02 Test matrix

| Test ID | Visibility | baseline -> reference |
|---|---|---|
| `assessment/tests/test_hidden.py::test_cached_upgrade` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_event_defensive_copy` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_generated_version_transitions` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_hidden_cli_fixture` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_independent_keys` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_invalid_version` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_negative_cache_refresh` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_old_version_cannot_restore_revoked` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_product_isolation` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_revoke_after_many_reads` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_same_version_conflict_atomic` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_same_version_replay` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_step_isolation` | hidden | PASS → PASS |
| `tests/test_public.py::test_cached_revocation` | public | FAIL → PASS |
| `tests/test_public.py::test_initial_allowed` | public | PASS → PASS |
| `tests/test_public.py::test_missing_false` | public | PASS → PASS |
| `tests/test_public.py::test_public_cli_fixture` | public | FAIL → PASS |
| `tests/test_public.py::test_stale_update_ignored` | public | PASS → PASS |
