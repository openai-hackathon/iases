# Public behavior contract

A synthetic condition-monitoring service summarizes one cycle's uniformly sampled
vibration trace. The hydraulic source motivates cycle monitoring, not these missing-data
fixtures or a real production bug. Input samples is an EVEN-length list (4<=N<=64) of
finite numbers or None. sample_rate>0 is Hz, max_gap is a nonnegative integer,
min_coverage and ratio_threshold lie in [0,1], energy_threshold>=0, and band=[low,high]
has 0<=low<high<=sample_rate/2+sample_rate/N. A band may contain no DFT bins.

coverage is the fraction of ORIGINAL non-None samples. Retain it even after interpolation.
Any missing endpoint or consecutive interior hole longer than max_gap makes the cycle
insufficient_data. Otherwise fill every interior run of m holes by equally spaced LINEAR
interpolation: for left L and right R, hole j=1..m is L+j*(R-L)/(m+1).
Also gate insufficient_data when UNROUNDED observed coverage<min_coverage. Never turn
imputed samples into observed coverage. For gated cycles report coverage and None for
slope,band_energy,total_energy,ratio, with decision='insufficient_data'.

For an accepted cycle, first remove the least-squares straight line fitted to ALL filled
samples at indices 0..N-1, including both intercept and slope. Report this pre-window slope
in units/sample. THEN multiply residuals by the PERIODIC Hann window
w_i=0.5-0.5*cos(2*pi*i/N). Detrending after windowing is not equivalent; do not window twice
or use the symmetric N-1 window. Compute the unnormalized DFT X_k=sum(y_i*exp(-2*pi*j*k*i/N)).
For k=0..N/2 inclusive, use energy_k=c_k*|X_k|^2/(N*sum(w_i^2)), where c_k=1 at DC AND
Nyquist (k=N/2), and 2 at all interior positive-frequency bins. Total energy is the sum of
these one-sided bins. Band energy includes exactly low<=k*sample_rate/N<high.

ratio=band_energy/total_energy when total_energy>1e-12, otherwise zero. Decide 'alarm'
iff UNROUNDED band_energy>=energy_threshold AND ratio>=ratio_threshold; otherwise 'normal'.
Return coverage,slope,band_energy,total_energy,ratio,decision. Round each reported number
to six decimals only at output; do not round intermediate energies or thresholds. The
ratio guard defines behavior for numerically zero detrended signals. Never mutate samples.
Version 2 computes a paired Welch diagnostic. reference optionally supplies a
second trace of the same length; omission uses samples as its own reference.
segment_length is even, 4..N (default N); step is 1..segment_length (default
segment_length). The band's upper bound may reach sample_rate/2+sample_rate/L,
using segment length L instead of full trace length N. Windows start at
0,step,2*step,... while start+length<=N;
discard incomplete trailing windows. A segment is accepted only if BOTH channels
independently pass the original endpoint, max_gap and original coverage rules
within that segment. Fill gaps locally; neighboring windows cannot repair a
missing segment endpoint. Use EXACTLY the same accepted segment set for both
auto spectra and the cross spectrum. min_segments>=1 defaults to 1.

Detrend each channel independently within each accepted segment, then apply
periodic Hann. At bin k let c_k be 1 at DC and Nyquist, otherwise 2. For each
segment form Pxx=c_k*abs(X)^2/(L*sum(w^2)), Pyy similarly, and
Pxy=c_k*conj(X)*Y/(L*sum(w^2)). Average these quantities over accepted segments
BEFORE computing nonlinear ratios or taking cross-spectrum magnitudes/phases.
Frequencies are k*sample_rate/L. Sum averaged Pxx over all bins for total_energy,
over the half-open band for band_energy; sum band Pyy for reference_energy and
band complex Pxy for C. Coherence=min(1,abs(C)^2/(band_energy*reference_energy))
when that product>1e-12, otherwise 0. phase=arg(C) in (-pi,pi] when abs(C)>1e-12,
otherwise 0. Map a numerical angle within 1e-12 of -pi to +pi.

Keep original output fields and add segments (accepted window start indexes),
reference_energy,coherence,phase. Report coverage as the fraction of positions
where BOTH ORIGINAL full traces are observed, even when windows are rejected.
Report slope as the mean pre-window slope of samples across accepted segments.
If fewer than min_segments survive, numerical diagnostics are None and decision
is insufficient_data; still report coverage and accepted indexes. Otherwise alarm
requires the original energy/ratio gates AND coherence>=coherence_threshold
(default 0, range [0,1]) AND abs(phase)<=phase_limit (default pi, range [0,pi]).
All gates use unrounded values. Round only reported diagnostics to six decimals.
These window-local quality rules supersede the original whole-trace processing.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
