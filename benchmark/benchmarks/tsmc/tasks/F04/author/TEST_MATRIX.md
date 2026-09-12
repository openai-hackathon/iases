# F04 Test matrix

| Test ID | Visibility | baseline -> reference |
|---|---|---|
| `assessment/tests/test_hidden.py::test_boolean_not_number` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_equal_temperature[25-C]` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_equal_temperature[298.15-K]` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_equal_temperature[77-F]` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_equivalent_pressure[0.003-MPa]` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_equivalent_pressure[3-kPa]` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_equivalent_pressure[30-mbar]` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_equivalent_pressure[3000-Pa]` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_hidden_cli_fixture` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_input_unchanged` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_invalid_dimension` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_invalid_string` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_nan_inf` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_string_numeric` | hidden | FAIL → PASS |
| `assessment/tests/test_hidden.py::test_unknown_sensor` | hidden | PASS → PASS |
| `assessment/tests/test_hidden.py::test_unknown_unit` | hidden | PASS → PASS |
| `tests/test_public.py::test_base_unit_normal` | public | PASS → PASS |
| `tests/test_public.py::test_equal_not_alarm` | public | PASS → PASS |
| `tests/test_public.py::test_kpa_conversion` | public | FAIL → PASS |
| `tests/test_public.py::test_missing` | public | PASS → PASS |
| `tests/test_public.py::test_public_cli_fixture` | public | FAIL → PASS |
