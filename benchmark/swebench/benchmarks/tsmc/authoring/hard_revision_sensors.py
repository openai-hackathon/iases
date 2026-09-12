"""Campaign-calibrated multivariate monitoring and paired Welch diagnostics."""

from dataclasses import replace
import json
from pathlib import Path
from .schema import Case, Change, code
from .hard_sensors import temporal_diagnosis, spectral_diagnosis


def tasks():
    return [campaign_monitor(), paired_spectrum()]


def extra_cases(task_id):
    path = Path(__file__).with_name("hard_revision_sensor_cases.json")
    return tuple(Case(**row) for row in json.loads(path.read_text())[task_id])


def campaign_monitor():
    original = temporal_diagnosis()
    files = {"fabops/cohort.py": original.files["fabops/cohort.py"]}
    files["fabops/linalg.py"] = code('''
        """Solve the observed correlation system without inverting missing coordinates."""
        def solve(matrix, vector):
            size = len(vector)
            augmented = [list(row) + [value] for row, value in zip(matrix, vector)]
            for column in range(size):
                pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
                augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
                divisor = augmented[column][column]
                augmented[column] = [value / divisor for value in augmented[column]]
                for row in range(size):
                    if row != column:
                        factor = augmented[row][column]
                        augmented[row] = [a - factor*b for a, b in zip(augmented[row], augmented[column])]
            return [row[-1] for row in augmented]
    ''')
    files["fabops/model.py"] = code('''
        """Equal campaign mass, within-campaign moments, and observed-subspace scoring."""
        from collections import Counter
        from math import sqrt
        from .linalg import solve

        def fit(rows, shrinkage):
            counts = Counter(row["run"] for row in rows)
            weights = [1 / (len(counts) * counts[row["run"]]) for row in rows]
            dimension = len(rows[0]["features"])
            center = [sum(weight * row["features"][j] for row, weight in zip(rows, weights)) for j in range(dimension)]
            covariance = [[sum(weight * (row["features"][j]-center[j]) * (row["features"][k]-center[k])
                               for row, weight in zip(rows, weights)) for k in range(dimension)] for j in range(dimension)]
            scale = [sqrt(covariance[j][j]) if covariance[j][j] > 0 else 1.0 for j in range(dimension)]
            correlation = [[1.0 if j == k else (1-shrinkage)*covariance[j][k]/(scale[j]*scale[k])
                            for k in range(dimension)] for j in range(dimension)]
            return center, scale, correlation

        def score(features, model):
            center, scale, correlation = model
            observed = [j for j, value in enumerate(features) if value is not None]
            z = [(features[j]-center[j])/scale[j] for j in observed]
            matrix = [[correlation[j][k] for k in observed] for j in observed]
            solution = solve(matrix, z)
            return len(features)/len(observed) * sum(a*b for a, b in zip(z, solution))
    ''')
    files["fabops/calibration.py"] = code('''
        """Purged leave-campaign-out calibration with equal mass per held-out campaign."""
        from math import ceil
        from .cohort import training_rows
        from .model import fit, score

        def calibrate(rows, request):
            calibration = []
            for campaign in sorted({row["run"] for row in rows}):
                held = [row for row in rows if row["run"] == campaign]
                anchor = dict(held[0], start=min(row["start"] for row in held))
                training = training_rows(rows, anchor, request["embargo"])
                if len(training) < request["min_train"]:
                    continue
                model = fit(training, request["shrinkage"])
                calibration.append([campaign, max(score(row["features"], model) for row in held)])
            rank = ceil((len(calibration)+1)*(1-request["alpha"]))
            if not calibration or rank > len(calibration):
                return calibration, None
            return calibration, sorted(value for _, value in calibration)[rank-1]
    ''')
    files["fabops/domain.py"] = code("""
        from .cohort import training_rows
        from .model import fit, score
        from .calibration import calibrate

        def run(request):
            target = next(row for row in request["cycles"] if row["id"] == request["target"])
            rows = training_rows(request["cycles"], target, request["embargo"])
            result = dict(training=[row["id"] for row in rows], center=None, scale=None,
                          correlation=None, score=None, calibration=[], threshold=None,
                          decision="insufficient_training")
            if len(rows) < request["min_train"]:
                return result
            model = fit(rows, request["shrinkage"])
            center, scale, correlation = model
            result.update(center=[round(value,6) for value in center], scale=[round(value,6) for value in scale],
                          correlation=[[round(value,6) for value in row] for row in correlation])
            threshold = request["threshold"]
            if request.get("calibrate", False):
                calibration, threshold = calibrate(rows, request)
                result["calibration"] = [[name, round(value,6)] for name,value in calibration]
            result["threshold"] = None if threshold is None else round(threshold,6)
            if target["profile"][4] != 0 or sum(value is not None for value in target["features"]) < request.get("min_observed", len(target["features"])):
                result["decision"] = "deferred"
                return result
            distance = score(target["features"], model)
            result["score"] = round(distance,6)
            result["decision"] = "insufficient_calibration" if threshold is None else "alarm" if distance >= threshold else "normal"
            return result
    """)
    weight = Change(
        "fabops/model.py",
        'weights = [1 / (len(counts) * counts[row["run"]]) for row in rows]',
        "weights = [1 / len(rows) for row in rows]",
    )
    diagonal = Change(
        "fabops/linalg.py",
        files["fabops/linalg.py"],
        code('''
        """Legacy marginal approximation ignores coupled sensor geometry."""
        def solve(matrix, vector):
            return [value / matrix[index][index] for index, value in enumerate(vector)]
    '''),
    )
    leakage = Change(
        "fabops/calibration.py",
        'training = training_rows(rows, anchor, request["embargo"])',
        "training = rows",
    )
    faults = (*original.faults[:4], weight, diagonal, leakage)
    mutants = {
        f"cohort_rule_{index}": (fault,)
        for index, fault in enumerate(original.faults[:4])
    }
    mutants.update(
        {
            "row_weighted_campaigns": (weight,),
            "diagonal_approximation": (diagonal,),
            "calibration_leakage": (leakage,),
            "missing_dimension_not_normalized": (
                Change("fabops/model.py", "len(features)/len(observed) * ", ""),
            ),
            "zero_impute_missing": (
                Change(
                    "fabops/model.py",
                    "observed = [j for j, value in enumerate(features) if value is not None]",
                    "features = [0 if value is None else value for value in features]\n    observed = list(range(len(features)))",
                ),
            ),
            "wrong_conformal_rank": (
                Change(
                    "fabops/calibration.py", "(len(calibration)+1)", "len(calibration)"
                ),
            ),
            "average_instead_of_worst_campaign": (
                Change(
                    "fabops/calibration.py",
                    'max(score(row["features"], model) for row in held)',
                    'sum(score(row["features"], model) for row in held)/len(held)',
                ),
            ),
        }
    )
    legacy_cases = []
    for case in original.cases:
        expected = dict(case.expected, calibration=[], threshold=None)
        if expected["correlation"] is not None:
            r = expected["correlation"]
            expected["correlation"] = [[1.0, r], [r, 1.0]]
            expected["threshold"] = round(case.request["threshold"], 6)
        legacy_cases.append(replace(case, expected=expected))
    contract = code("""
        Fit a campaign-balanced hydraulic monitor for 1..5 feature coordinates. Cycles have
        unique id, run, start,end (end>start), equally sized features of finite numbers or
        None, and profile [cooler,valve,pump_leakage,accumulator,stable_flag]. Healthy is
        [100,100,0,130] and stable_flag=0. target identifies an existing cycle. Select only
        complete, healthy, stable rows from other runs with end<=target.start-embargo.
        embargo>=0. Sort training by (end,id). min_train>=2 counts rows, not runs. No target
        run member, future row, incomplete row or faulty component can enter training.

        Give each selected run total weight 1/G and each of its n_g rows weight 1/(G*n_g).
        Compute weighted means and population covariance, including between-run variation.
        Scale_j=sqrt(cov_jj), or 1 when variance is zero. Correlation has diagonal 1 and
        off-diagonal (1-shrinkage)*cov_jk/(scale_j*scale_k), shrinkage in [0.05,1].
        Target labels do not affect eligibility to score except stable_flag. The optional
        min_observed is 1..dimension, default dimension. Insufficient observed target
        coordinates or a transient target gives deferred after model/calibration fitting.
        Otherwise select the OBSERVED principal submatrix of correlation, solve R_obs*u=z,
        and score=(dimension/observed_count)*dot(z,u). This uses the inverse of the observed
        covariance submatrix, not the corresponding block of the full precision matrix;
        do not impute missing target features. Use unrounded numbers throughout.

        threshold>=0 is used unless calibrate=true. With calibration enabled, alpha is in
        (0,1). For each run in the outer training cohort, hold out its ENTIRE run. Fit a
        fresh model only on eligible outer rows from other runs ending no later than
        min(held_run.start)-embargo. Skip a run when its fresh training has fewer than
        min_train rows. Score every held row with that model and retain their MAX score
        as one calibration observation. Sort returned [run,score] pairs by run. For m
        observations, take one-based rank ceil((m+1)*(1-alpha)) of ascending raw scores.
        If m=0 or rank>m, threshold=None. No interpolation or clipping of rank is allowed.

        Return training,center,scale,correlation (a matrix),score,calibration,threshold,
        decision. Insufficient outer training gives all numerical fields None, calibration=[]
        and decision=insufficient_training. Otherwise fit and calibrate, then defer an
        unscorable target; else report its score and insufficient_calibration if threshold
        is None, alarm iff raw score>=raw threshold, otherwise normal. Round reported
        numbers to six decimals only. At most 24 cycles. Inputs must remain unchanged.
    """)
    return replace(
        original,
        version="2.0",
        title="Campaign calibration leaks future runs and scores the wrong sensor subspace",
        family="campaign_weighted_purged_calibration_subspace",
        contract=contract,
        files=files,
        faults=faults,
        mutants=mutants,
        cases=(*legacy_cases, *extra_cases("A30")),
        difficulty_reason="Requires weighted multivariate covariance, observed-subspace linear solves and temporally purged leave-campaign-out calibration with finite-sample rank selection; campaign leakage, unequal sampling and missing dimensions interact across four algorithms.",
    )


def paired_spectrum():
    original = spectral_diagnosis()
    files = {
        "fabops/preprocess.py": original.files["fabops/preprocess.py"],
        "fabops/spectrum.py": original.files["fabops/spectrum.py"],
    }
    files["fabops/segments.py"] = code('''
        """Select complete paired windows before averaging any spectra."""
        from .preprocess import fill, detrend
        from .spectrum import window

        def segments(request):
            x = request["samples"]
            y = request.get("reference", x)
            length = request.get("segment_length", len(x))
            step = request.get("step", length)
            accepted = []
            for start in range(0, len(x)-length+1, step):
                first, cx = fill(x[start:start+length], request["max_gap"])
                second, cy = fill(y[start:start+length], request["max_gap"])
                if first is None or second is None or min(cx, cy) < request["min_coverage"]:
                    continue
                first, slope = detrend(first)
                second, _ = detrend(second)
                first, normalizer = window(first)
                second, _ = window(second)
                accepted.append((start, first, second, slope, normalizer))
            return accepted
    ''')
    files["fabops/welch.py"] = code('''
        """Average complex cross spectra before forming band coherence or phase."""
        from cmath import exp, phase
        from math import pi

        def transform(values):
            n = len(values)
            return [sum(value*exp(-2j*pi*k*i/n) for i,value in enumerate(values)) for k in range(n//2+1)]

        def summarize(segments, request):
            n = len(segments[0][1])
            xx, yy, xy = [0.0]*(n//2+1), [0.0]*(n//2+1), [0j]*(n//2+1)
            for _, first, second, _, normalizer in segments:
                fx, fy = transform(first), transform(second)
                for k in range(n//2+1):
                    factor = 1 if k in (0, n//2) else 2
                    weight = factor / (n*normalizer*len(segments))
                    xx[k] += weight*abs(fx[k])**2
                    yy[k] += weight*abs(fy[k])**2
                    xy[k] += weight*fx[k].conjugate()*fy[k]
            chosen = [k for k in range(n//2+1) if request["band"][0] <= k*request["sample_rate"]/n < request["band"][1]]
            first, second, cross = sum(xx[k] for k in chosen), sum(yy[k] for k in chosen), sum(xy[k] for k in chosen)
            coherence = min(1.0, abs(cross)**2/(first*second)) if first*second > 1e-12 else 0.0
            angle = phase(cross) if abs(cross) > 1e-12 else 0.0
            # Normalize numerical -pi to the documented (-pi, pi] convention.
            if abs(angle + pi) < 1e-12:
                angle = pi
            return first, sum(xx), second, coherence, angle
    ''')
    files["fabops/domain.py"] = code("""
        from math import pi
        from .segments import segments
        from .welch import summarize

        def run(request):
            first = request["samples"]
            second = request.get("reference", first)
            coverage = sum(a is not None and b is not None for a,b in zip(first,second))/len(first)
            selected = segments(request)
            output = dict(coverage=round(coverage,6), segments=[row[0] for row in selected],
                          slope=None,band_energy=None,total_energy=None,ratio=None,
                          reference_energy=None,coherence=None,phase=None,decision="insufficient_data")
            if len(selected) < request.get("min_segments", 1):
                return output
            energy, total, reference_energy, coherence, phase = summarize(selected, request)
            ratio = energy/total if total > 1e-12 else 0.0
            slope = sum(row[3] for row in selected)/len(selected)
            decision = ("alarm" if energy >= request["energy_threshold"] and ratio >= request["ratio_threshold"]
                        and coherence >= request.get("coherence_threshold",0)
                        and abs(phase) <= request.get("phase_limit",pi) else "normal")
            output.update(slope=round(slope,6),band_energy=round(energy,6),total_energy=round(total,6),
                          ratio=round(ratio,6),reference_energy=round(reference_energy,6),
                          coherence=round(coherence,6),phase=round(phase,6),decision=decision)
            return output
    """)
    averaging = Change(
        "fabops/welch.py",
        "xy[k] += weight*fx[k].conjugate()*fy[k]",
        "xy[k] += weight*abs(fx[k].conjugate()*fy[k])",
    )
    ordering = Change(
        "fabops/segments.py",
        "first, slope = detrend(first)\n        second, _ = detrend(second)\n        first, normalizer = window(first)\n        second, _ = window(second)",
        "first, normalizer = window(first)\n        second, _ = window(second)\n        first, slope = detrend(first)\n        second, _ = detrend(second)",
    )
    nyquist = Change(
        "fabops/welch.py",
        "factor = 1 if k in (0, n//2) else 2",
        "factor = 1 if k == 0 else 2",
    )
    faults = (
        original.faults[0],
        original.faults[1],
        original.faults[3],
        averaging,
        ordering,
        nyquist,
    )
    mutants = {
        name: (fault,)
        for name, fault in zip(
            [
                "gap_fraction",
                "imputed_coverage",
                "symmetric_window",
                "cross_magnitude_before_average",
                "window_before_detrend",
                "doubled_nyquist",
            ],
            faults,
        )
    }
    mutants.update(
        {
            "conjugate_other_channel": (
                Change(
                    "fabops/welch.py",
                    "fx[k].conjugate()*fy[k]",
                    "fx[k]*fy[k].conjugate()",
                ),
            ),
            "ignore_reference_quality": (
                Change(
                    "fabops/segments.py",
                    'second, cy = fill(y[start:start+length], request["max_gap"])',
                    'second, cy = fill(x[start:start+length], request["max_gap"])',
                ),
            ),
            "nonoverlapping_windows_only": (
                Change(
                    "fabops/segments.py",
                    'step = request.get("step", length)',
                    "step = length",
                ),
            ),
            "last_window_omitted": (
                Change("fabops/segments.py", "len(x)-length+1", "len(x)-length"),
            ),
            "segment_count_ignored": (
                Change("fabops/domain.py", 'request.get("min_segments", 1)', "1"),
            ),
        }
    )
    legacy = []
    for case in original.cases:
        expected = dict(case.expected)
        valid = expected["band_energy"] is not None
        expected.update(
            segments=[0] if valid else [],
            reference_energy=expected["band_energy"],
            coherence=(1.0 if expected["band_energy"] ** 2 > 1e-12 else 0.0)
            if valid
            else None,
            phase=0.0 if valid else None,
        )
        legacy.append(replace(case, expected=expected))
    contract = original.contract + code("""

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
    """)
    return replace(
        original,
        version="2.0",
        title="Paired vibration windows lose phase cancellation and share incompatible support",
        family="paired_welch_support_coherence_phase",
        contract=contract,
        files=files,
        faults=faults,
        mutants=mutants,
        cases=(*legacy, *extra_cases("A31")),
        difficulty_reason="Reconstruct paired gap-valid windows, per-window detrending, energy-normalized complex cross spectra and ensemble-before-ratio coherence/phase; independent channel filtering and averaging magnitudes destroy the joint diagnostic even when each scalar spectrum looks plausible.",
    )
