# A04 Test matrix

| Test ID | Visibility | baseline -> reference |
|---|---|---|
| `assessment/tests/test_hidden.py::test_duplicate_new_offset_advances_checkpoint` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_generated_expected_sum` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_hidden_cli_fixture` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_invalid_offset` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_invalid_value_atomic` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_late_event_with_new_offset` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_machine_groups` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_no_input_mutation` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_partition_equivalence` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_replayed_old_offsets_not_counted` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_resume_json_roundtrip` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_unsorted_batch_sorted_by_ingest_offset` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_watermark_not_cursor` | hidden | PASS → PASS |
| `tests/test_public.py::test_empty_batch` | public | PASS → PASS |
| `tests/test_public.py::test_monotone_time` | public | PASS → PASS |
| `tests/test_public.py::test_one_event` | public | PASS → PASS |
| `tests/test_public.py::test_public_cli_fixture` | public | FAIL → PASS |
| `tests/test_public.py::test_same_timestamp_distinct_events` | public | FAIL → PASS |
