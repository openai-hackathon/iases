# Author notes

Design difficulty: hard. Requires preserving original observation quality through interpolation, enforcing the noncommuting detrend/window order, and reconstructing an energy-normalized one-sided spectrum with distinct DC/Nyquist weights across three modules. Unlike A09 hysteresis, A22 unit conversion or A23 scalar variance, the defect changes frequency-domain geometry and invalid data can pass a downstream diagnosis unless stages agree.

Family: `quality_gated_detrended_one_sided_spectrum`. References: zema-hydraulic.

Fixtures are newly authored. No external dataset rows are redistributed.
