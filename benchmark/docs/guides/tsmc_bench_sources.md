# Manufacturing references and expansion decisions

The benchmark now treats TSMC as an imagined semiconductor-factory setting.
Its software incidents, repositories, inputs, fixes and tests are synthetic.
No task is presented as an actual TSMC incident, and no source below identifies
the bundled data as proprietary TSMC data. The source registry is
[`benchmarks/tsmc/sources.json`](../../benchmarks/tsmc/sources.json).

## Selected references

| Priority | Reference and evidence | Best use in this benchmark |
| --- | --- | --- |
| Primary | [NIST SMS Test Bed](https://www.nist.gov/laboratories/tools-instruments/smart-manufacturing-systems-sms-test-bed): physical fabrication and inspection equipment, MTConnect streams, queryable data and technical packages | Machine states, telemetry services, inspection and data lifecycle. Most reliability tasks use this as operational context; their bugs are authored. |
| Primary | [Production Analysis with Process Mining Technology](https://doi.org/10.4121/uuid:68726926-5ac5-4fab-b873-ee76ea412399): production activity records associated with orders and resources | Routing, rework, scheduling and work-order flows. Semiconductor-specific reticle and lot examples extend these concepts. |
| Primary | [ZeMA hydraulic condition data](https://archive.ics.uci.edu/dataset/447/condition+monitoring+of+hydraulic+systems): 2,205 experimental cycles, 60 seconds each, with sensors sampled at 1, 10 and 100 Hz | Multirate alignment, pressure normalization, power integration and condition summaries. This is a test rig, not a fab. |
| Primary | [SECOM](https://archive.ics.uci.edu/dataset/179/secom): semiconductor measurements with missing values and signed pass/fail labels | Missing-value handling, quality aggregation and exact label decoding. Useful data semantics, without software-fix ground truth. |
| Secondary | [BPI Challenge 2019](https://research.tue.nl/en/datasets/bpi-challenge-2019/): 251,734 purchase-line cases and 1,595,923 events from a coatings and paints company | Purchase-line identity, partial receipts and invoices. F21 uses a simplified quantity contract inspired by three-way matching. |
| Secondary | [Bosch Production Line Performance](https://www.kaggle.com/c/bosch-production-line-performance/data): anonymized production-line records separated into numeric, categorical and date files | Part/station joins and missing observations. Competition files are not bundled. |

[MTConnect 2.0 Fundamentals](https://docs.mtconnect.org/MBSD_MTConnect_Part_1_2-0-0.pdf)
is a pinned protocol reference, separate from NIST's datasets. R23 specifically
uses its advertised `nextSequence` behavior. R10 and R27 are broader engineering
exercises about consumption and retention, not implementations certified against
the standard.

The selected sources provide realistic data characteristics and operational
constraints. They do not supply the seeded faults, repair patches or evaluation
oracle. Expected outputs were authored independently as literal examples;
reference implementations do not generate expected test answers.

The downloaded source archives were also inspected locally. The production CSV
contains 4,543 event rows, 225 case ids and 55 activity labels before preprocessing.
SECOM's archive contains 1,567 measurement rows with **590 numeric columns**, and
1,463 pass / 104 fail labels. Its landing page says 591 features; use the actual
file shape when implementing a parser. Archive SHA-256 values and inspection
counts are recorded in [`source_inspection.json`](../../benchmarks/tsmc/reports/source_inspection.json).

## Candidates considered but not selected as primary references

| Candidate | Decision |
| --- | --- |
| [AI4I 2020](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset) | Useful supplemental maintenance vocabulary, but its 10,000 records are synthetic. It does not strengthen the real-world provenance claim. |
| [NASA C-MAPSS degradation data](https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data) | Useful for trajectory-aware evaluation and remaining-life scenarios, but simulated engine degradation is less directly useful for the current software-repair scope. The degradation dataset must not be confused with a separately listed simulator package. |
| [SKAB](https://github.com/waico/skab) | Real test-bed anomaly sequences are relevant to future streaming extensions. Fault-detection labels do not establish software-repair correctness; verify dataset-specific reuse terms before importing data. |
| [WM-811K original dataset site](http://mirlab.org/dataSet/public/) | Potentially valuable wafer geometry and lot grouping. Original access and reuse terms could not be established reliably in this review, so no files or company-origin claims are imported. |
| [Tennessee Eastman simulations](https://doi.org/10.7910/DVN/6C3JR1) | Rich process-control scenarios, but simulated and less aligned with deterministic repository repair. |
| [Alibaba cluster traces](https://github.com/alibaba/clusterdata) | Useful for factory computing infrastructure, but not manufacturing process evidence. |

## Reuse and leakage boundaries

UCI currently labels SECOM and the hydraulic dataset CC BY 4.0. The production
log lists 4TU terms, while competition and other repositories require their own
terms to be checked. This release distributes newly authored fixtures only;
it does not copy raw dataset records, code, publications or large datasets.

Public source material is already available to model developers. Referencing it
does not make a task uncontaminated. The reserved split protects against tuning
on this release's task-specific feedback; it cannot prove that a model has never
seen a related manufacturing concept. Author checkouts contain private tests and
reference fixes. Publish generated solver exports, not the author checkout, if
the reserved evaluation material must remain secret.

For a future extension using raw data, split complete source units (work order,
lot, machine run or trajectory) before selecting windows or creating faults.
Keep all variants of one underlying issue in a single evaluation partition.
Do not split adjacent sensor windows from the same run randomly across training
and evaluation.
