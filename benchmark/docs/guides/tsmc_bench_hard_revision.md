# Hard-task reconstruction (manufacturing-90-v4)

This revision strengthens A30, A31, F19, F26, F27, R22, R30, R31 and R32 along
their existing manufacturing scenarios. A29, F25 and R29 are explicitly excluded.
All task material is in English. Difficulty is an author estimate, not a measured
model success rate. No reserved task is used for model-driven calibration.

The design targets interacting algorithms and recovery invariants, not obscure
requirements, longer prompts alone, or tighter timeouts. Public contracts define
every tested rule, including input bounds, ordering, numerical conventions and
failure precedence. Author-only reference repairs and deliberately incorrect
repairs are validated separately from solver exports.

| Task | Existing direction | Added difficulty |
| --- | --- | --- |
| F19 | Dispatch and snapshot commit | Exact temporal allocation with alternative tools, reticle reuse, calendars, precedence and atomic reservations |
| F26 | Ambiguous lifecycle correlation | Global resource-capacity and route constraints across all maximum interpretations |
| F27 | Revisioned material receipts | Historical visibility and atomic bundles whose feasible internal order must be reconstructed |
| R22 | Durable lease fencing | Scoped multi-resource grants, renewal, ownership checks and atomic fenced multi-key writes |
| R30 | Verified technical packages | Global version-range resolution, rollback protection and staged compare-and-swap publication |
| R31 | Telemetry snapshot recovery | Causal cross-source cuts that must retreat together, durable gaps and epoch-sensitive dependencies |
| R32 | Resumable verified imports | Revision-bound publication across multiple uploads with tombstones, read sets and atomic group commit |
| A30 | Leakage-free multivariate monitoring | Campaign-balanced fitting, missing-coordinate geometry and leave-campaign-out calibration |
| A31 | Vibration spectral diagnostics | Paired segment selection, Welch cross-spectra, coherence and phase across missing data |

The following primary sources inform these independently authored scenarios:

- [OR-Tools job-shop scheduling](https://developers.google.com/optimization/scheduling/job_shop)
  describes ordered operations, exclusive machines and nonpreemptive scheduling.
  F19 extends these concepts with reticle capacity and snapshot-checked publication.
- [Mining Uncertain Event Data in Process Mining](https://arxiv.org/abs/1910.00089)
  motivates preserving multiple event interpretations. F26 defines its own
  lifecycle, route and capacity constraints; these are not a dataset's ground truth.
- [NIST SMS Test Bed](https://www.nist.gov/laboratories/tools-instruments/smart-manufacturing-systems-sms-test-bed)
  supplies manufacturing telemetry and technical-package context.
- [SQLite isolation](https://www.sqlite.org/isolation.html) documents transaction
  isolation and snapshot behavior. The reliability tasks require real persisted
  transactions and independently opened connections where specified.
- [The Chubby lock service](https://research.google/pubs/the-chubby-lock-service-for-loosely-coupled-distributed-systems/)
  explains acquisition counters and rejection of delayed writes. R22 adds an
  explicitly specified atomic resource-set protocol; it is not a Chubby replica.
- [The Update Framework specification](https://theupdateframework.github.io/specification/latest/)
  motivates revision consistency and rollback protection. R30 is a bounded package
  protocol and does not claim to implement TUF or cryptographic signature checking.
- [Apache Beam watermarks and late data](https://beam.apache.org/documentation/programming-guide/#watermarks-and-late-data)
  informs the distinction between event time and processing progress in R31.
- [Chandy and Lamport, Distributed Snapshots](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/12/Determining-Global-States-of-a-Distributed-System.pdf)
  motivates causal consistency of a distributed state. R31 implements its own
  bounded dependency-closed prefix calculation, not the paper's marker protocol.
- [NIST Digital Thread for Smart Manufacturing](https://www.nist.gov/programs-projects/digital-thread-smart-manufacturing)
  motivates trustworthy links across design, production and inspection data.
  R30 and R32 turn that context into explicit revision and publication contracts.
- [scikit-learn covariance estimation](https://scikit-learn.org/stable/modules/covariance.html)
  describes shrinkage and multivariate distance. A30 specifies its own campaign
  weighting and calibration protocol explicitly.
- [SciPy cross spectral density](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.csd.html)
  documents Welch averaging and the conjugation convention for cross spectra.
  A31's quality gates and phase decision are authored additions.

No source code, raw dataset rows or proprietary production data are copied into
the fixtures. Source references provide technical context, not evidence of real
TSMC incidents. Prior task versions and their release manifest are archived before
replacement so that existing scores retain their original meaning.

The nine replacements use task version `2.0`; split assignments remain unchanged
(F19 is `dev`; the other eight are reserved `test`). The release still has 90 tasks.
All 81 unselected task trees, all scenarios and `sources.json` retain their exact
pre-revision hashes. The v3 manifest is preserved in
`benchmarks/tsmc/releases/manufacturing-90-v3.json`, with the nine original task
trees under `benchmarks/tsmc/releases/manufacturing-90-v3/tasks/`. Release validation
checks the complete predecessor chain, rejects partial migrations, and rejects
changes to protected tasks or archived fixtures. Formatting hooks exclude archives.

| Task | Previous tests | Revised tests | Baseline FAIL_TO_PASS | Wrong repairs |
| --- | ---: | ---: | ---: | ---: |
| A30 | 25 | 41 | 34 | 11 |
| A31 | 23 | 40 | 35 | 11 |
| F19 | 13 | 23 | 13 | 9 |
| F26 | 21 | 34 | 16 | 11 |
| F27 | 21 | 37 | 14 | 12 |
| R22 | 13 | 22 | 13 | 8 |
| R30 | 21 | 38 | 21 | 8 |
| R31 | 20 | 34 | 16 | 9 |
| R32 | 22 | 38 | 13 | 9 |
| Total | 179 | 307 | 175 | 88 |

Numerical expectations for the new A30/A31 cases are frozen literals produced by
an independent NumPy oracle (`hard_revision_sensor_oracle.py`), using array
covariance/inversion and FFT routines. It never calls the task reference code,
which uses standard-library linear algebra and direct Fourier summation. NumPy
2.5.2 reproduced the checked-in JSON exactly; it is needed only to regenerate
those author examples, never by a solver. Existing regression expectations are
retained or adapted analytically to the documented output extension. Scheduling
and package-resolution cases include their full supported search dimensions.

The formal Docker audit passed all nine tasks in 115 executions: baseline, gold,
gold repeat and every wrong repair. Both reference runs passed every required
test; all 88 wrong repairs failed at least one hidden test. Test collection,
baseline FAIL_TO_PASS/PASS_TO_PASS classification and repeat grading agreed.
The release-bound report, including immutable image IDs, is
[`native_hard_revision_9_validation.json`](../../benchmarks/tsmc/reports/native_hard_revision_9_validation.json).
Detailed local artifacts are under `logs/evaluation/tsmc-hard-v4-native-002/`.
The complete TSMC regression suite also passed: `227 passed` from
`python -m pytest -q tests/test_tsmc_*.py`, including release preservation,
reserved exports, grading, image checks and scenario integration. Ruff 0.9.6
lint/format checks passed for the changed authoring and release modules.

To repeat the author audit with a fresh run ID:

```bash
uv run python -m swebench.benchmarks.tsmc.prepare \
  --output .generated/tsmc-hard-v4 \
  --task A30 --task A31 --task F19 --task F26 --task F27 \
  --task R22 --task R30 --task R31 --task R32
uv run swebench images build .generated/tsmc-hard-v4/task-repo -n swebench -j 2 \
  -i tsmc__a30-v2.0 -i tsmc__a31-v2.0 -i tsmc__f19-v2.0 \
  -i tsmc__f26-v2.0 -i tsmc__f27-v2.0 -i tsmc__r22-v2.0 \
  -i tsmc__r30-v2.0 -i tsmc__r31-v2.0 -i tsmc__r32-v2.0
uv run python -m swebench.benchmarks.tsmc.validate \
  --task-repo .generated/tsmc-hard-v4/task-repo \
  --run-id tsmc-hard-v4-native-003 --workers 3
```

Difficulty remains an author judgment. More tests and rejection of plausible
wrong repairs demonstrate correctness coverage, not a measured reduction in
model success rate. Historical v2/v3 model scores must retain their release hashes
and must not be relabeled as v4 results.
