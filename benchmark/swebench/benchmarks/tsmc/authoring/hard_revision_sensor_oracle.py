"""Independent NumPy oracles used only to freeze authored numerical examples.

Run as a module to regenerate hard_revision_sensor_cases.json. Solver fixtures use
literal expected results and need only the standard library. These oracles never
import or execute the task's reference implementations.
"""

import copy
import json
import math
from pathlib import Path
import numpy as np


def cycle(name, values, run=None, start=0):
    return dict(
        id=name,
        features=values,
        run=run or name,
        start=start,
        end=start + 1,
        profile=[100, 100, 0, 130, 0],
    )


def campaign_expected(request):
    target = next(row for row in request["cycles"] if row["id"] == request["target"])

    def eligible(rows, campaign, cutoff):
        return sorted(
            [
                r
                for r in rows
                if r["run"] != campaign
                and r["end"] <= cutoff
                and r["profile"] == [100, 100, 0, 130, 0]
                and None not in r["features"]
            ],
            key=lambda r: (r["end"], r["id"]),
        )

    def model(rows):
        groups = sorted({r["run"] for r in rows})
        arrays = [
            np.array([r["features"] for r in rows if r["run"] == g], dtype=float)
            for g in groups
        ]
        center = np.mean([a.mean(axis=0) for a in arrays], axis=0)
        cov = np.mean([(a - center).T @ (a - center) / len(a) for a in arrays], axis=0)
        scale = np.sqrt(np.diag(cov))
        scale[scale == 0] = 1
        matrix = (1 - request["shrinkage"]) * cov / np.outer(scale, scale)
        np.fill_diagonal(matrix, 1)
        return center, scale, matrix

    def score(values, fit):
        center, scale, matrix = fit
        mask = np.array([v is not None for v in values])
        z = (np.array([v for v in values if v is not None]) - center[mask]) / scale[
            mask
        ]
        return float(
            len(values)
            / sum(mask)
            * (z @ np.linalg.inv(matrix[np.ix_(mask, mask)]) @ z)
        )

    rows = eligible(
        request["cycles"], target["run"], target["start"] - request["embargo"]
    )
    result = dict(
        training=[r["id"] for r in rows],
        center=None,
        scale=None,
        correlation=None,
        score=None,
        calibration=[],
        threshold=None,
        decision="insufficient_training",
    )
    if len(rows) < request["min_train"]:
        return result
    fit = model(rows)
    result.update(
        center=np.round(fit[0], 6).tolist(),
        scale=np.round(fit[1], 6).tolist(),
        correlation=np.round(fit[2], 6).tolist(),
    )
    threshold = request["threshold"]
    if request.get("calibrate"):
        observations = []
        for group in sorted({r["run"] for r in rows}):
            held = [r for r in rows if r["run"] == group]
            history = eligible(
                rows, group, min(r["start"] for r in held) - request["embargo"]
            )
            if len(history) >= request["min_train"]:
                observations.append(
                    [group, max(score(r["features"], model(history)) for r in held)]
                )
        rank = math.ceil((len(observations) + 1) * (1 - request["alpha"]))
        threshold = (
            sorted(v for _, v in observations)[rank - 1]
            if 0 < rank <= len(observations)
            else None
        )
        result["calibration"] = [[g, round(v, 6)] for g, v in observations]
    result["threshold"] = None if threshold is None else round(threshold, 6)
    if target["profile"][4] or sum(
        v is not None for v in target["features"]
    ) < request.get("min_observed", len(target["features"])):
        result["decision"] = "deferred"
    else:
        distance = score(target["features"], fit)
        result.update(
            score=round(distance, 6),
            decision="insufficient_calibration"
            if threshold is None
            else "alarm"
            if distance >= threshold
            else "normal",
        )
    return result


def spectral_expected(request):
    x = request["samples"]
    y = request.get("reference", x)
    n = request.get("segment_length", len(x))
    step = request.get("step", n)
    weight = np.hanning(n + 1)[:-1]
    accepted = []
    spectra = []
    slopes = []

    def repair(values):
        mask = np.array([v is not None for v in values])
        if not mask[0] or not mask[-1] or mask.mean() < request["min_coverage"]:
            return None
        observed = np.flatnonzero(mask)
        if np.max(np.diff(observed)) - 1 > request["max_gap"]:
            return None
        return np.interp(np.arange(n), observed, [values[i] for i in observed])

    for start in range(0, len(x) - n + 1, step):
        a, b = repair(x[start : start + n]), repair(y[start : start + n])
        if a is None or b is None:
            continue
        vectors = []
        for values in [a, b]:
            coefficients = np.polynomial.polynomial.polyfit(np.arange(n), values, 1)
            residual = values - np.polynomial.polynomial.polyval(
                np.arange(n), coefficients
            )
            vectors.append(np.fft.rfft(residual * weight))
        slopes.append(float(np.polynomial.polynomial.polyfit(np.arange(n), a, 1)[1]))
        accepted.append(start)
        spectra.append(vectors)
    output = dict(
        coverage=round(
            sum(a is not None and b is not None for a, b in zip(x, y)) / len(x), 6
        ),
        segments=accepted,
        slope=None,
        band_energy=None,
        total_energy=None,
        ratio=None,
        reference_energy=None,
        coherence=None,
        phase=None,
        decision="insufficient_data",
    )
    if len(accepted) < request.get("min_segments", 1):
        return output
    array = np.array(spectra)
    factors = np.full(n // 2 + 1, 2.0)
    factors[[0, -1]] = 1
    scale = factors / (n * np.dot(weight, weight))
    xx = np.mean(np.abs(array[:, 0]) ** 2, axis=0) * scale
    yy = np.mean(np.abs(array[:, 1]) ** 2, axis=0) * scale
    xy = np.mean(np.conjugate(array[:, 0]) * array[:, 1], axis=0) * scale
    freq = np.fft.rfftfreq(n, 1 / request["sample_rate"])
    mask = (freq >= request["band"][0]) & (freq < request["band"][1])
    first = float(xx[mask].sum())
    second = float(yy[mask].sum())
    total = float(xx.sum())
    cross = xy[mask].sum()
    coherence = (
        min(1, float(abs(cross) ** 2 / (first * second)))
        if first * second > 1e-12
        else 0.0
    )
    phase = float(np.angle(cross)) if abs(cross) > 1e-12 else 0.0
    if abs(phase + math.pi) < 1e-12:
        phase = math.pi
    ratio = first / total if total > 1e-12 else 0.0
    alarm = (
        first >= request["energy_threshold"]
        and ratio >= request["ratio_threshold"]
        and coherence >= request.get("coherence_threshold", 0)
        and abs(phase) <= request.get("phase_limit", math.pi)
    )
    output.update(
        slope=round(float(np.mean(slopes)), 6),
        band_energy=round(first, 6),
        total_energy=round(total, 6),
        ratio=round(ratio, 6),
        reference_energy=round(second, 6),
        coherence=round(coherence, 6),
        phase=round(phase, 6),
        decision="alarm" if alarm else "normal",
    )
    return output


def cases():
    result = {"A30": [], "A31": []}

    def add(task, name, request, public=False):
        oracle = campaign_expected if task == "A30" else spectral_expected
        result[task].append(
            dict(name=name, request=request, expected=oracle(request), public=public)
        )

    base = dict(
        cycles=[
            cycle("a", [0, 0], "old", 0),
            cycle("b", [2, 2], "old", 2),
            cycle("c", [4, 0], "new", 4),
            cycle("t", [3, 1], "target", 20),
        ],
        target="t",
        embargo=0,
        min_train=2,
        shrinkage=0.5,
        threshold=3,
    )
    add("A30", "unequal_campaign_mass", base, True)
    r = copy.deepcopy(base)
    r["cycles"][-1]["features"] = [3, None]
    r["min_observed"] = 1
    add("A30", "observed_principal_subspace", r, True)
    r = copy.deepcopy(base)
    r.update(calibrate=True, alpha=0.5)
    add("A30", "purged_run_calibration", r, True)
    for alpha in [0.1, 0.75]:
        r = copy.deepcopy(base)
        r.update(calibrate=True, alpha=alpha)
        add("A30", f"finite_sample_rank_{str(alpha).replace('.', '_')}", r)
    r = copy.deepcopy(base)
    r["cycles"].insert(3, cycle("d", [9, 2], "new", 6))
    r.update(calibrate=True, alpha=0.5)
    add("A30", "worst_member_per_run", r)
    r = copy.deepcopy(base)
    r["cycles"][-1]["features"] = [None, 1]
    r["min_observed"] = 1
    add("A30", "second_coordinate_only", r)
    r = copy.deepcopy(base)
    r["cycles"][-1]["features"] = [None, None]
    r["min_observed"] = 1
    add("A30", "no_observed_coordinate", r)
    r = copy.deepcopy(base)
    r["embargo"] = 2
    r.update(calibrate=True, alpha=0.5)
    add("A30", "calibration_embargo_removes_history", r)
    for dimension in [1, 3, 4, 5]:
        r = copy.deepcopy(base)
        r["cycles"] = [
            cycle(
                f"p{i}",
                [((i + 1) * (j + 2) % 7) - 3 for j in range(dimension)],
                f"g{i // 2}",
                i * 2,
            )
            for i in range(8)
        ]
        r["cycles"].append(cycle("t", [2] * dimension, "target", 30))
        r.update(calibrate=True, alpha=0.6, shrinkage=0.2)
        add("A30", f"dimension_{dimension}_calibration", r)
        if dimension > 1:
            r = copy.deepcopy(r)
            r["cycles"][-1]["features"][1] = None
            r["min_observed"] = 1
            add("A30", f"dimension_{dimension}_missing", r)
    spectral = dict(
        samples=[0, 1, 0, -1, 0, 1, 0, -1],
        reference=[0, 1, 0, -1, 0, -1, 0, 1],
        sample_rate=4,
        segment_length=4,
        step=4,
        max_gap=1,
        min_coverage=0.5,
        band=[0, 3],
        energy_threshold=0.01,
        ratio_threshold=0,
        coherence_threshold=0.5,
        phase_limit=math.pi,
    )
    add("A31", "opposite_windows_cancel_cross_spectrum", spectral, True)
    for shift in [0, 1, 2]:
        r = copy.deepcopy(spectral)
        r["reference"] = ([1, 0, -1, 0] * 3)[shift : shift + 8]
        add("A31", f"signed_phase_{shift}", r, shift == 0)
    r = copy.deepcopy(spectral)
    r["step"] = 2
    add("A31", "overlap_changes_ensemble", r, True)
    r = copy.deepcopy(spectral)
    r["step"] = 2
    r["reference"][1] = None
    add("A31", "overlap_with_local_reference_gap", r)
    r = copy.deepcopy(spectral)
    r["reference"][4] = None
    add("A31", "reference_endpoint_rejects_pair", r)
    r = copy.deepcopy(spectral)
    r["samples"][1] = None
    r["reference"][6] = None
    add("A31", "independent_interior_gap_repair", r)
    r = copy.deepcopy(spectral)
    r["reference"][1:3] = [None, None]
    add("A31", "long_reference_gap", r)
    r = copy.deepcopy(spectral)
    r["reference"][4] = None
    r["min_segments"] = 2
    add("A31", "paired_count_gate", r)
    r = copy.deepcopy(spectral)
    r["reference"][1] = None
    r["min_coverage"] = 0.8
    add("A31", "original_reference_coverage", r)
    r = copy.deepcopy(spectral)
    r["samples"] = [1, -1] * 4
    r["reference"] = [2, -2] * 4
    r["band"] = [2, 3]
    add("A31", "nyquist_cross_energy", r)
    r = copy.deepcopy(spectral)
    r["reference"] = [0] * 8
    add("A31", "zero_reference_power", r)
    r = copy.deepcopy(spectral)
    r["samples"] = [0] * 8
    r["reference"] = [0] * 8
    add("A31", "both_zero_power", r)
    r = copy.deepcopy(spectral)
    r["band"] = [0.1, 0.9]
    add("A31", "empty_bin_band", r)
    r = copy.deepcopy(spectral)
    r["samples"] += [3, 4]
    r["reference"] += [5, 6]
    add("A31", "discard_partial_tail", r)
    r = copy.deepcopy(spectral)
    r["reference"] = [1, 0, -1, 0] * 2
    r["phase_limit"] = 0.1
    add("A31", "phase_gate_uses_signed_cross", r)
    return result


if __name__ == "__main__":
    target = Path(__file__).with_name("hard_revision_sensor_cases.json")
    target.write_text(
        json.dumps(cases(), indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    print(target)
