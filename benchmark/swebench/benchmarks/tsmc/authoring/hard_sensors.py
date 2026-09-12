"""Hard synthetic cycle analytics inspired by UCI hydraulic condition monitoring."""

from .schema import Case, Change, Task, code


def tasks():
    yield phase_energy()
    yield temporal_diagnosis()
    yield spectral_diagnosis()


def phase_energy():
    files = {
        "fabops/segments.py": code('''
            """Build cycle-local calibrated linear segments without bridging bad data."""
            def segments(rows, cycle, calibration, max_gap):
                points = sorted((row for row in rows if row["cycle"] == cycle["id"]
                                 and cycle["start"] <= row["t"] <= cycle["end"]),
                                key=lambda row: row["t"])
                result = []
                for left, right in zip(points, points[1:]):
                    width = right["t"] - left["t"]
                    if not (left["valid"] and right["valid"]):
                        continue
                    if width > max_gap:
                        continue
                    values = [row["value"] * calibration["gain"] + calibration["offset"]
                              for row in (left, right)]
                    result.append((left["t"], right["t"], *values))
                return result

            def value(segment, time):
                left, right, first, last = segment
                return first + (last - first) * (time - left) / (right - left)
        '''),
        "fabops/integrate.py": code('''
            """Integrate two calibrated affine signals on their common valid support."""
            from .segments import value

            def joint_integrals(pressure, flow):
                duration = volume = work = 0.0
                for p in pressure:
                    for q in flow:
                        left, right = max(p[0], q[0]), min(p[1], q[1])
                        if left >= right:
                            continue
                        width = right - left
                        p0, p1 = value(p, left), value(p, right)
                        q0, q1 = value(q, left), value(q, right)
                        dp, dq = p1 - p0, q1 - q0
                        duration += width
                        volume += width * (q0 + q1) / 120
                        work += width * (p0 * q0 + (p0 * dq + q0 * dp) / 2
                                         + dp * dq / 3) / 600
                return duration, volume, work
        '''),
        "fabops/domain.py": code('''
            """Report cycle work only when jointly supported measurements cover enough time."""
            from .integrate import joint_integrals
            from .segments import segments

            def run(request):
                output = []
                for cycle in sorted(request["cycles"], key=lambda row: (row["start"], row["id"])):
                    pressure = segments(request["pressure"], cycle, request["calibration"]["pressure"],
                                        request["max_gap"]["pressure"])
                    flow = segments(request["flow"], cycle, request["calibration"]["flow"],
                                    request["max_gap"]["flow"])
                    duration, volume, work = joint_integrals(pressure, flow)
                    coverage = duration / (cycle["end"] - cycle["start"])
                    accepted = duration > 0 and coverage >= request["min_coverage"]
                    output.append(dict(cycle=cycle["id"], coverage=round(coverage, 6),
                                       accepted=accepted,
                                       volume=round(volume, 6) if accepted else None,
                                       work=round(work, 6) if accepted else None))
                return output
        '''),
    }
    faults = (
        Change(
            "fabops/segments.py",
            'if not (left["valid"] and right["valid"]):',
            'if not (left["valid"] or right["valid"]):',
        ),
        Change(
            "fabops/segments.py",
            "if width > max_gap:",
            'if width / (cycle["end"] - cycle["start"]) > max_gap:',
        ),
        Change("fabops/integrate.py", "dp * dq / 3", "dp * dq / 2"),
        Change(
            "fabops/domain.py",
            'coverage = duration / (cycle["end"] - cycle["start"])',
            'coverage = min(sum(s[1] - s[0] for s in pressure), sum(s[1] - s[0] for s in flow)) / (cycle["end"] - cycle["start"])',
        ),
    )
    return Task(
        "A29",
        "Multirate cycle work integrates unsupported phases and couples the wrong coverage",
        "hard",
        "multirate_joint_support_cycle_energy",
        code("""
        A synthetic factory utility monitor combines pressure (bar) and flow (litres/minute)
        sampled at different rates. This service is inspired by cycle-wise, multirate hydraulic
        monitoring. Its short traces and missing/quality scenarios are newly authored; the source
        dataset reports no missing values.

        Input contains cycles {id,start,end}, pressure and flow lists of {cycle,t,value,valid},
        calibration mappings for both channels {gain,offset}, max_gap for each channel, and
        min_coverage in [0,1]. Cycle ids are unique, end>start, timestamps and values are finite,
        and timestamps are unique within each channel/cycle. Lists may be unordered. Times are
        absolute seconds; cycles may touch or overlap. max_gap is positive. Each channel's affine
        calibration is applied to every endpoint before integration.

        Process each cycle independently: retain only its own rows with start<=t<=end and sort
        by t. A supported segment joins ADJACENT retained observations only when BOTH are valid
        and their separation is <= that channel's max_gap. Bad observations break support; do
        not drop them and bridge their neighbors. Never extrapolate or borrow another cycle's
        rows, even at a shared boundary. Between supported endpoints the signal is linear.

        Intersect the two channels' supported intervals. Integrate flow and pressure*flow only
        on this JOINT support, splitting at either channel's knots. volume is integral(flow)/60
        litres; work is integral(pressure*flow)/600 kJ. Integrate the product of two linear
        signals exactly, including its quadratic term; endpoint-product trapezoids are not exact.
        coverage is the joint supported duration divided by the FULL cycle duration, not a count
        of samples or the smaller of two separately supported durations. Accept iff joint duration
        is positive and UNROUNDED coverage>=min_coverage. Otherwise volume/work are None.

        Return a list sorted by (cycle start,id), each {cycle,coverage,accepted,volume,work}.
        Round numeric results to six decimals only for output. Empty cycle lists return [].
        Empty channels and one-point channels provide no supported duration. Inputs never change.
        """),
        files,
        faults,
        dict(
            zip(
                (
                    "quality_not_repaired",
                    "gap_not_repaired",
                    "product_not_repaired",
                    "coverage_not_repaired",
                ),
                ((fault,) for fault in faults),
            )
        ),
        tuple(phase_cases()),
        ("zema-hydraulic",),
        difficulty_reason="Requires reconstructing two piecewise-linear supports, intersecting them across independent knots, exactly integrating a quadratic product, and coupling the result to a cycle-duration quality gate across three modules. Unlike A11 scalar integration, A14 as-of calibration, and A18 nearest alignment, neither per-channel integration nor nearest-sample pairing can satisfy the joint-support energy contract.",
    )


def phase_request(pressure, flow, *, end=4, gap=4, coverage=1, calibration=None):
    def rows(points):
        return [
            dict(
                cycle="c",
                t=point[0],
                value=point[1],
                valid=point[2] if len(point) == 3 else True,
            )
            for point in points
        ]

    return dict(
        cycles=[dict(id="c", start=0, end=end)],
        pressure=rows(pressure),
        flow=rows(flow),
        max_gap=dict(pressure=gap, flow=gap),
        min_coverage=coverage,
        calibration=calibration
        or dict(pressure=dict(gain=1, offset=0), flow=dict(gain=1, offset=0)),
    )


def phase_result(coverage, volume=None, work=None, cycle="c"):
    return [
        dict(
            cycle=cycle,
            coverage=coverage,
            accepted=volume is not None,
            volume=volume,
            work=work,
        )
    ]


def phase_cases():
    yield Case(
        "constant_phases",
        phase_request([(0, 60), (4, 60)], [(0, 60), (4, 60)]),
        phase_result(1.0, 4.0, 24.0),
        public=True,
    )
    yield Case(
        "affine_product",
        phase_request([(0, 0), (4, 120)], [(0, 0), (4, 120)]),
        phase_result(1.0, 4.0, 32.0),
        public=True,
    )
    yield Case(
        "bad_knot_breaks_both_neighbors",
        phase_request(
            [(0, 60), (1, 60, False), (2, 60), (4, 60)],
            [(0, 60), (4, 60)],
            coverage=0.5,
        ),
        phase_result(0.5, 2.0, 12.0),
        public=True,
    )
    yield Case(
        "individually_covered_but_disjoint",
        phase_request([(0, 60), (2, 60)], [(2, 60), (4, 60)], coverage=0.5),
        phase_result(0.0),
        public=True,
    )
    yield Case(
        "gap_rejects_sparse_span",
        phase_request(
            [(0, 60), (1, 60), (4, 60)], [(0, 60), (4, 60)], gap=2, coverage=0.1
        ),
        phase_result(0.0),
    )
    yield Case(
        "gap_equality_is_supported",
        phase_request([(0, 60), (2, 60), (4, 60)], [(0, 60), (2, 60), (4, 60)], gap=2),
        phase_result(1.0, 4.0, 24.0),
    )
    yield Case(
        "knots_from_either_channel",
        phase_request([(0, 0), (4, 120)], [(0, 0), (2, 120), (4, 0)]),
        phase_result(1.0, 4.0, 24.0),
    )
    yield Case(
        "crossed_affine_slopes",
        phase_request([(0, 120), (4, 0)], [(0, 0), (4, 120)]),
        phase_result(1.0, 4.0, 16.0),
    )
    yield Case(
        "calibrate_before_product",
        phase_request(
            [(0, 0), (4, 60)],
            [(0, 0), (4, 60)],
            calibration=dict(
                pressure=dict(gain=2, offset=60), flow=dict(gain=1, offset=30)
            ),
        ),
        phase_result(1.0, 4.0, 52.0),
    )
    yield Case(
        "coverage_gate_uses_full_cycle",
        phase_request([(1, 60), (3, 60)], [(1, 60), (3, 60)], coverage=0.6),
        phase_result(0.5),
    )
    yield Case(
        "joint_not_marginal_coverage",
        phase_request([(0, 60), (3, 60)], [(1, 60), (4, 60)], coverage=0.6),
        phase_result(0.5),
    )
    yield Case(
        "single_observation_cannot_extrapolate",
        phase_request([(2, 60)], [(0, 60), (4, 60)], coverage=0),
        phase_result(0.0),
    )
    yield Case(
        "empty_channel",
        phase_request([], [(0, 60), (4, 60)], coverage=0),
        phase_result(0.0),
    )
    yield Case(
        "unsorted_inputs",
        phase_request([(4, 120), (0, 0)], [(4, 120), (0, 0)]),
        phase_result(1.0, 4.0, 32.0),
    )
    yield Case(
        "bad_rows_are_not_removed_before_adjacency",
        phase_request(
            [(0, 60), (2, 60, False), (4, 60)], [(0, 60), (4, 60)], coverage=0
        ),
        phase_result(0.0),
    )
    request = phase_request(
        [(-1, 60), (1, 60), (3, 60), (5, 60)], [(0, 60), (4, 60)], coverage=0.5
    )
    yield Case(
        "outside_rows_do_not_extend_support", request, phase_result(0.5, 2.0, 12.0)
    )
    request = phase_request([(0, 60), (4, 60)], [(0, 60), (4, 60)])
    request["cycles"].insert(0, dict(id="b", start=4, end=8))
    request["pressure"] += [
        dict(cycle="b", t=4, value=120, valid=True),
        dict(cycle="b", t=8, value=120, valid=True),
    ]
    request["flow"] += [
        dict(cycle="b", t=4, value=30, valid=True),
        dict(cycle="b", t=8, value=30, valid=True),
    ]
    yield Case(
        "cycle_boundary_identity",
        request,
        phase_result(1.0, 4.0, 24.0) + phase_result(1.0, 2.0, 24.0, "b"),
    )
    request = phase_request(
        [(0, 60), (1, 60)], [(0, 60), (1, 60)], end=3, coverage=0.3333334
    )
    yield Case("gate_before_rounding", request, phase_result(0.333333))


def temporal_diagnosis():
    files = {
        "fabops/cohort.py": code('''
            """Select a purged, stable, healthy cohort without campaign leakage."""
            def training_rows(rows, target, embargo):
                selected = []
                for row in rows:
                    if row["run"] == target["run"]:
                        continue
                    if row["end"] > target["start"] - embargo:
                        continue
                    if row["profile"][4] != 0:
                        continue
                    if row["profile"][:4] != [100, 100, 0, 130]:
                        continue
                    if any(value is None for value in row["features"]):
                        continue
                    selected.append(row)
                return sorted(selected, key=lambda row: (row["end"], row["id"]))
        '''),
        "fabops/model.py": code('''
            """Fit training-only moments and a shrunk two-feature correlation model."""
            from math import sqrt

            def fit(rows, target, shrinkage):
                values = [row["features"] for row in rows]
                center = [sum(row[j] for row in values) / len(values) for j in range(2)]
                variance = [sum((row[j] - center[j]) ** 2 for row in values) / len(values)
                            for j in range(2)]
                scale = [sqrt(value) if value > 0 else 1.0 for value in variance]
                correlation = sum((row[0] - center[0]) * (row[1] - center[1]) for row in values)
                correlation /= len(values) * scale[0] * scale[1]
                return center, scale, (1 - shrinkage) * correlation

            def score(features, center, scale, correlation):
                first, second = [(features[j] - center[j]) / scale[j] for j in range(2)]
                return ((first * first - 2 * correlation * first * second + second * second)
                        / (1 - correlation * correlation))
        '''),
        "fabops/domain.py": code('''
            """Diagnose one cycle using only eligible historical campaigns."""
            from .cohort import training_rows
            from .model import fit, score

            def run(request):
                target = next(row for row in request["cycles"] if row["id"] == request["target"])
                rows = training_rows(request["cycles"], target, request["embargo"])
                result = dict(training=[row["id"] for row in rows], center=None, scale=None,
                              correlation=None, score=None, decision="insufficient_training")
                if len(rows) < request["min_train"]:
                    return result
                center, scale, correlation = fit(rows, target, request["shrinkage"])
                result.update(center=[round(value, 6) for value in center],
                              scale=[round(value, 6) for value in scale],
                              correlation=round(correlation, 6))
                if target["profile"][4] != 0 or any(value is None for value in target["features"]):
                    result["decision"] = "deferred"
                    return result
                distance = score(target["features"], center, scale, correlation)
                result.update(score=round(distance, 6),
                              decision="alarm" if distance >= request["threshold"] else "normal")
                return result
        '''),
    }
    faults = (
        Change(
            "fabops/cohort.py",
            'if row["run"] == target["run"]:',
            'if row["id"] == target["id"]:',
        ),
        Change(
            "fabops/cohort.py",
            'if row["end"] > target["start"] - embargo:',
            'if row["start"] > target["start"] - embargo:',
        ),
        Change(
            "fabops/cohort.py",
            'if row["profile"][4] != 0:',
            'if row["profile"][4] and row["profile"][:4] != [100, 100, 0, 130]:',
        ),
        Change(
            "fabops/cohort.py",
            'if row["profile"][:4] != [100, 100, 0, 130]:',
            'if row["profile"][0] != 100:',
        ),
        Change(
            "fabops/model.py",
            'values = [row["features"] for row in rows]',
            'values = [row["features"] for row in rows] + ([target["features"]] if all(value is not None for value in target["features"]) else [])',
        ),
        Change(
            "fabops/model.py",
            "first * first - 2 * correlation * first * second",
            "first * first + 2 * correlation * first * second",
        ),
    )
    return Task(
        "A30",
        "Campaign leakage and covariance inversion corrupt cycle anomaly scores",
        "hard",
        "purged_group_training_correlated_cycle_diagnosis",
        code("""
        Fit and apply a deterministic two-feature cycle monitor. Hydraulic source profiles
        motivate the five condition fields, but these fixtures and fault scenarios are synthetic.
        Each cycle has unique id, run (campaign id), start,end with end>start, features [x,y],
        and profile [cooler,valve,pump_leakage,accumulator,stable_flag]. Known healthy conditions
        are exactly [100,100,0,130]; stable_flag=0 means stable and 1 means possibly transient.
        Finite feature values may be None for unavailable measurements. Input order is arbitrary.

        request.target identifies one existing cycle. Other parameters are nonnegative embargo,
        integer min_train>=2, shrinkage in [0.05,1], and nonnegative threshold. Select training cycles
        only when their run differs from the target's ENTIRE run, end<=target.start-embargo,
        stable_flag==0, ALL four component conditions are healthy, and neither feature is None.
        Purge using the candidate END time, not start; equality at the embargo boundary is allowed.
        Sort the selected rows by (end,id). Never train on future rows, target-run siblings,
        transient rows, partially faulty profiles, or the target feature vector.

        With fewer than min_train rows return their training ids, None for center,scale,correlation,
        score and decision='insufficient_training'. Otherwise fit both coordinate means and
        POPULATION variances on only those rows. Scale is sqrt(variance), or 1 for zero variance.
        The raw correlation is mean((x-center_x)*(y-center_y))/(scale_x*scale_y), including zero
        when either feature is constant. Store r=(1-shrinkage)*raw_correlation. This is shrinkage
        of a standardized correlation matrix toward the identity, not a raw covariance matrix.

        With z_j=(target_feature_j-center_j)/scale_j, score is the squared Mahalanobis distance
        (z_x^2-2*r*z_x*z_y+z_y^2)/(1-r^2). Score the target even when its component labels are
        unhealthy; labels are training eligibility only. If the target is transient or missing a
        feature, still return the fitted model but score=None, decision='deferred'. Otherwise
        decision is 'alarm' iff the UNROUNDED score>=threshold, else 'normal'. Return training ids,
        center[2],scale[2],correlation,score,decision; round model numbers and score to six decimals
        only for output. All fitting and scoring calculations use unrounded values. Inputs are immutable.
        """),
        files,
        faults,
        dict(
            zip(
                (
                    "group_leakage",
                    "end_time_purge",
                    "transient_training",
                    "partial_profile",
                    "target_scaling",
                    "correlation_sign",
                ),
                ((fault,) for fault in faults),
            )
        ),
        tuple(temporal_cases()),
        ("zema-hydraulic",),
        difficulty_reason="Couples embargoed interval selection, campaign-level exclusion and five-field profile eligibility with training-only standardization and inversion of a shrunk correlation matrix across three modules. Unlike A16 scalar chart baselines or A23 pooled variance, correct cohort membership changes a multivariate geometry, and a marginal z-score or random split cannot reproduce the diagnostic.",
    )


def cycle_row(name, values, *, run=None, start=0, end=1, profile=None):
    return dict(
        id=name,
        run=run or name,
        start=start,
        end=end,
        features=values,
        profile=profile or [100, 100, 0, 130, 0],
    )


def temporal_request(
    *, target=(3, 1), rows=None, threshold=5, shrinkage=0.5, embargo=1, min_train=2
):
    training = (
        rows
        if rows is not None
        else [cycle_row("a", [0, 0]), cycle_row("b", [2, 2], start=2, end=3)]
    )
    return dict(
        cycles=[
            *training,
            cycle_row("t", list(target), run="target-run", start=10, end=11),
        ],
        target="t",
        embargo=embargo,
        min_train=min_train,
        shrinkage=shrinkage,
        threshold=threshold,
    )


def temporal_result(
    score=5.333333,
    decision="alarm",
    *,
    training=None,
    center=None,
    scale=None,
    correlation=0.5,
):
    return dict(
        training=training if training is not None else ["a", "b"],
        center=center if center is not None else [1.0, 1.0],
        scale=scale if scale is not None else [1.0, 1.0],
        correlation=correlation,
        score=score,
        decision=decision,
    )


def temporal_cases():
    yield Case(
        "correlated_training", temporal_request(), temporal_result(), public=True
    )
    request = temporal_request()
    request["cycles"].insert(
        0, cycle_row("sibling", [100, 100], run="target-run", end=2)
    )
    yield Case("exclude_entire_campaign", request, temporal_result(), public=True)
    request = temporal_request()
    request["cycles"].insert(0, cycle_row("overlap", [100, 100], start=8, end=9.5))
    yield Case("purge_by_end_not_start", request, temporal_result(), public=True)
    yield Case(
        "cross_term_sign",
        temporal_request(target=(3, 3), threshold=6),
        temporal_result(5.333333, "normal"),
        public=True,
    )
    request = temporal_request(target=(3, 3), threshold=6)
    request["cycles"] += [
        cycle_row("same_campaign", [100, -100], run="target-run", start=6, end=8),
        cycle_row("crossing_embargo", [-100, 100], start=7, end=10),
    ]
    yield Case(
        "campaign_and_overlap_cannot_rotate_model",
        request,
        temporal_result(5.333333, "normal"),
    )
    request = temporal_request()
    request["cycles"].insert(
        0, cycle_row("transient", [100, 100], profile=[100, 100, 0, 130, 1])
    )
    yield Case("stable_flag_zero_is_eligible", request, temporal_result())
    for name, profile in (
        ("valve", [100, 90, 0, 130, 0]),
        ("pump", [100, 100, 1, 130, 0]),
        ("accumulator", [100, 100, 0, 115, 0]),
        ("cooler", [20, 100, 0, 130, 0]),
    ):
        request = temporal_request()
        request["cycles"].insert(0, cycle_row(name, [100, 100], profile=profile))
        yield Case("exclude_unhealthy_" + name, request, temporal_result())
    request = temporal_request()
    request["cycles"].insert(0, cycle_row("future", [100, 100], start=20, end=21))
    yield Case("future_features_do_not_fit", request, temporal_result())
    request = temporal_request()
    request["cycles"][1].update(start=8, end=9)
    yield Case("embargo_equality_is_allowed", request, temporal_result())
    rows = [cycle_row("a", [0, 0]), cycle_row("b", [2, -2], start=2, end=3)]
    yield Case(
        "negative_correlation",
        temporal_request(rows=rows, target=(3, 1)),
        temporal_result(16.0, center=[1.0, -1.0], correlation=-0.5),
    )
    yield Case(
        "full_shrinkage_is_identity",
        temporal_request(target=(3, 3), shrinkage=1, threshold=8),
        temporal_result(8.0, correlation=0.0),
    )
    rows = [cycle_row("a", [0, 7]), cycle_row("b", [2, 7], start=2, end=3)]
    yield Case(
        "constant_coordinate_uses_unit_scale",
        temporal_request(rows=rows, target=(3, 8)),
        temporal_result(5.0, center=[1.0, 7.0], correlation=0.0),
    )
    rows = [
        cycle_row("a", [-2, 0]),
        cycle_row("b", [0, 0], start=1, end=2),
        cycle_row("c", [2, 0], start=2, end=3),
    ]
    yield Case(
        "population_scale_and_unrounded_scoring",
        temporal_request(rows=rows, target=(2, 1), threshold=3),
        temporal_result(
            2.5,
            "normal",
            training=["a", "b", "c"],
            center=[0.0, 0.0],
            scale=[1.632993, 1.0],
            correlation=0.0,
        ),
    )
    request = temporal_request()
    request["cycles"][-1]["profile"][4] = 1
    yield Case(
        "transient_target_is_deferred_after_fit",
        request,
        temporal_result(None, "deferred"),
    )
    request = temporal_request(target=(None, 1))
    yield Case(
        "missing_target_is_deferred_after_fit",
        request,
        temporal_result(None, "deferred"),
    )
    request = temporal_request()
    request["cycles"][-1]["profile"] = [3, 73, 2, 90, 0]
    yield Case("unhealthy_target_is_still_scored", request, temporal_result())
    request = temporal_request()
    request["cycles"].insert(0, cycle_row("missing", [None, 100]))
    yield Case("missing_training_is_excluded", request, temporal_result())
    request = temporal_request(rows=[])
    yield Case(
        "empty_history",
        request,
        dict(
            training=[],
            center=None,
            scale=None,
            correlation=None,
            score=None,
            decision="insufficient_training",
        ),
    )
    request = temporal_request(rows=[cycle_row("a", [0, 0])])
    yield Case(
        "one_training_cycle",
        request,
        dict(
            training=["a"],
            center=None,
            scale=None,
            correlation=None,
            score=None,
            decision="insufficient_training",
        ),
    )
    request = temporal_request()
    request["cycles"] = list(reversed(request["cycles"]))
    yield Case("order_independent_selection", request, temporal_result())
    yield Case(
        "threshold_before_rounding",
        temporal_request(threshold=5.3333332),
        temporal_result(),
    )


def spectral_diagnosis():
    files = {
        "fabops/preprocess.py": code('''
            """Repair short interior holes, retaining observed coverage and least-squares trend."""
            def fill(samples, max_gap):
                observed = sum(value is not None for value in samples)
                if samples[0] is None or samples[-1] is None:
                    return None, observed / len(samples)
                values = list(samples)
                index = 0
                while index < len(values):
                    if values[index] is not None:
                        index += 1
                        continue
                    start = index
                    while values[index] is None:
                        index += 1
                    width = index - start
                    if width > max_gap:
                        return None, observed / len(samples)
                    first, last = values[start - 1], values[index]
                    for offset in range(width):
                        fraction = (offset + 1) / (width + 1)
                        values[start + offset] = first + fraction * (last - first)
                return values, observed / len(samples)

            def detrend(values):
                count = len(values)
                middle = (count - 1) / 2
                mean = sum(values) / count
                slope = (sum((index - middle) * (value - mean) for index, value in enumerate(values))
                         / sum((index - middle) ** 2 for index in range(count)))
                return [value - mean - slope * (index - middle)
                        for index, value in enumerate(values)], slope
        '''),
        "fabops/spectrum.py": code('''
            """Periodic Hann window and energy-conserving one-sided DFT bands."""
            from math import cos, sin, pi

            def window(values):
                count = len(values)
                weights = [0.5 - 0.5 * cos(2 * pi * index / count) for index in range(count)]
                return [value * weight for value, weight in zip(values, weights)], sum(weight * weight for weight in weights)

            def energies(values, normalizer, sample_rate, band):
                count = len(values)
                selected = total = 0.0
                for frequency in range(count // 2 + 1):
                    real = sum(value * cos(2 * pi * frequency * index / count)
                               for index, value in enumerate(values))
                    imag = -sum(value * sin(2 * pi * frequency * index / count)
                                for index, value in enumerate(values))
                    factor = 1 if frequency in (0, count // 2) else 2
                    energy = factor * (real * real + imag * imag) / (count * normalizer)
                    total += energy
                    if band[0] <= frequency * sample_rate / count < band[1]:
                        selected += energy
                return selected, total
        '''),
        "fabops/domain.py": code('''
            """Apply quality gating before an ordered spectral diagnostic pipeline."""
            from .preprocess import fill, detrend
            from .spectrum import window, energies

            def run(request):
                values, coverage = fill(request["samples"], request["max_gap"])
                output = dict(coverage=round(coverage, 6), slope=None, band_energy=None,
                              total_energy=None, ratio=None, decision="insufficient_data")
                if values is None or coverage < request["min_coverage"]:
                    return output
                residual, slope = detrend(values)
                windowed, normalizer = window(residual)
                energy, total = energies(windowed, normalizer, request["sample_rate"], request["band"])
                ratio = energy / total if total > 1e-12 else 0.0
                decision = ("alarm" if energy >= request["energy_threshold"]
                            and ratio >= request["ratio_threshold"] else "normal")
                output.update(slope=round(slope, 6), band_energy=round(energy, 6),
                              total_energy=round(total, 6), ratio=round(ratio, 6), decision=decision)
                return output
        '''),
    }
    faults = (
        Change(
            "fabops/preprocess.py",
            "fraction = (offset + 1) / (width + 1)",
            "fraction = offset / (width + 1)",
        ),
        Change(
            "fabops/preprocess.py",
            "return values, observed / len(samples)",
            "return values, sum(value is not None for value in values) / len(values)",
        ),
        Change(
            "fabops/domain.py",
            "residual, slope = detrend(values)\n    windowed, normalizer = window(residual)",
            "windowed, normalizer = window(values)\n    windowed, slope = detrend(windowed)",
        ),
        Change(
            "fabops/spectrum.py",
            "cos(2 * pi * index / count)",
            "cos(2 * pi * index / (count - 1))",
        ),
        Change(
            "fabops/spectrum.py",
            "factor = 1 if frequency in (0, count // 2) else 2",
            "factor = 1 if frequency == 0 else 2",
        ),
    )
    return Task(
        "A31",
        "Window order and Nyquist weighting hide vibration-band faults after gap repair",
        "hard",
        "quality_gated_detrended_one_sided_spectrum",
        code("""
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
        """),
        files,
        faults,
        dict(
            zip(
                (
                    "interpolation_fraction",
                    "imputed_coverage",
                    "window_before_trend",
                    "symmetric_window",
                    "nyquist_doubling",
                ),
                ((fault,) for fault in faults),
            )
        ),
        tuple(spectral_cases()),
        ("zema-hydraulic",),
        difficulty_reason="Requires preserving original observation quality through interpolation, enforcing the noncommuting detrend/window order, and reconstructing an energy-normalized one-sided spectrum with distinct DC/Nyquist weights across three modules. Unlike A09 hysteresis, A22 unit conversion or A23 scalar variance, the defect changes frequency-domain geometry and invalid data can pass a downstream diagnosis unless stages agree.",
    )


def spectral_request(
    samples,
    *,
    sample_rate=4,
    band=(1, 2),
    max_gap=1,
    coverage=0.75,
    energy=0.5,
    ratio=0.6,
):
    return dict(
        samples=samples,
        sample_rate=sample_rate,
        band=list(band),
        max_gap=max_gap,
        min_coverage=coverage,
        energy_threshold=energy,
        ratio_threshold=ratio,
    )


def spectral_result(
    slope=None,
    energy=None,
    total=None,
    ratio=None,
    decision="insufficient_data",
    coverage=1.0,
):
    return dict(
        coverage=coverage,
        slope=slope,
        band_energy=energy,
        total_energy=total,
        ratio=ratio,
        decision=decision,
    )


def spectral_cases():
    yield Case(
        "constant_trace",
        spectral_request([2, 2, 2, 2]),
        spectral_result(0.0, 0.0, 0.0, 0.0, "normal"),
        public=True,
    )
    yield Case(
        "periodic_band_energy",
        spectral_request([1, -1, -1, 1]),
        spectral_result(0.0, 0.666667, 1.0, 0.666667, "alarm"),
        public=True,
    )
    yield Case(
        "remove_trend_before_window",
        spectral_request([1, 1, 3, 7]),
        spectral_result(2.0, 0.666667, 1.0, 0.666667, "alarm"),
        public=True,
    )
    yield Case(
        "imputation_cannot_raise_coverage",
        spectral_request([1, None, -1, 1], coverage=0.8),
        spectral_result(coverage=0.75),
        public=True,
    )
    yield Case(
        "least_squares_not_endpoint_detrend",
        spectral_request([1, -2, 1, 0], ratio=0.4),
        spectral_result(0.0, 0.666667, 1.333333, 0.5, "alarm"),
    )
    yield Case(
        "sign_reversal_preserves_spectrum",
        spectral_request([-1, 2, -1, 0], ratio=0.4),
        spectral_result(0.0, 0.666667, 1.333333, 0.5, "alarm"),
    )
    yield Case(
        "energy_scales_quadratically",
        spectral_request([2, -2, -2, 2]),
        spectral_result(0.0, 2.666667, 4.0, 0.666667, "alarm"),
    )
    yield Case(
        "nyquist_has_one_side_only",
        spectral_request([1, -2, 1, 0], band=(2, 3), ratio=0.4),
        spectral_result(0.0, 0.666667, 1.333333, 0.5, "alarm"),
    )
    yield Case(
        "dc_not_doubled",
        spectral_request([1, -1, -1, 1], band=(0, 1), energy=0.1, ratio=0.1),
        spectral_result(0.0, 0.166667, 1.0, 0.166667, "alarm"),
    )
    yield Case(
        "whole_spectrum_band",
        spectral_request([1, -1, -1, 1], band=(0, 3)),
        spectral_result(0.0, 1.0, 1.0, 1.0, "alarm"),
    )
    yield Case(
        "empty_band_has_zero_energy",
        spectral_request([1, -1, -1, 1], band=(0.1, 0.9)),
        spectral_result(0.0, 0.0, 1.0, 0.0, "normal"),
    )
    yield Case(
        "frequency_uses_rate_and_length",
        spectral_request([1, -1, -1, 1, 1, -1, -1, 1], sample_rate=8, band=(2, 3)),
        spectral_result(0.0, 0.666667, 1.0, 0.666667, "alarm"),
    )
    yield Case(
        "eight_sample_trend_and_offset",
        spectral_request([11, 12, 15, 20, 23, 24, 27, 32], sample_rate=8, band=(2, 3)),
        spectral_result(3.0, 0.666667, 1.0, 0.666667, "alarm"),
    )
    yield Case(
        "linear_interior_interpolation",
        spectral_request([1, None, -1, 1]),
        spectral_result(-0.1, 0.6, 1.11, 0.540541, "normal", 0.75),
    )
    yield Case(
        "two_holes_at_limit",
        spectral_request([1, None, None, 1], max_gap=2, coverage=0.5),
        spectral_result(0.0, 0.0, 0.0, 0.0, "normal", 0.5),
    )
    yield Case(
        "no_endpoint_extrapolation",
        spectral_request([None, 0, 0, 0]),
        spectral_result(coverage=0.75),
    )
    yield Case(
        "hole_exceeds_limit",
        spectral_request([1, None, None, 1], coverage=0.5),
        spectral_result(coverage=0.5),
    )
    yield Case(
        "all_samples_missing",
        spectral_request([None, None, None, None], coverage=0),
        spectral_result(coverage=0.0),
    )
    yield Case(
        "coverage_equality_is_accepted",
        spectral_request([1, None, -1, 1], ratio=0.54),
        spectral_result(-0.1, 0.6, 1.11, 0.540541, "alarm", 0.75),
    )
    yield Case(
        "threshold_uses_unrounded_energy",
        spectral_request([1, -1, -1, 1], energy=0.6666668, ratio=0),
        spectral_result(0.0, 0.666667, 1.0, 0.666667, "normal"),
    )
    yield Case(
        "pure_linear_signal_has_zero_energy",
        spectral_request([1, 3, 5, 7]),
        spectral_result(2.0, 0.0, 0.0, 0.0, "normal"),
    )
    yield Case(
        "zero_thresholds_are_inclusive",
        spectral_request([2, 2, 2, 2], energy=0, ratio=0),
        spectral_result(0.0, 0.0, 0.0, 0.0, "alarm"),
    )
