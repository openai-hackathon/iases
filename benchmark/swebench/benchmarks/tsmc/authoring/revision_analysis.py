"""Revised metrology and hydraulic analytics with independently specified cases.

Primary context: NIST manufacturing-data traceability (AMS 300-10), NIST sensor
timestamp/data-quality work (publication 903569), and UCI hydraulic dataset 447.
Revision protocols, quality corrections and clock failures are authored examples;
they are not defects or missing-data claims attributed to those sources.
"""

from .schema import Case, Change, Task, code


def tasks():
    yield historical_metrology()
    yield revised_hydraulic_windows()


def historical_metrology():
    visibility = code('''
        """Resolve identity revisions at the recorded-time visibility frontier."""
        def visible(rows, asof):
            current = {}
            for row in rows:
                if row["recorded"] > asof:
                    continue
                old = current.get(row["id"])
                if old is None or row["revision"] > old["revision"]:
                    current[row["id"]] = row
            return current
    ''')
    files = {
        "fabops/history.py": visibility,
        "fabops/metrology.py": code('''
            """Join the chosen measurement to quality and calibration at its own time."""
            from fractions import Fraction

            def choose(measurements, quality, at):
                selected = {}
                for row in measurements.values():
                    if row["deleted"] or row["event"] > at:
                        continue
                    key = (row["part"], row["station"])
                    old = selected.get(key)
                    if old is None or (row["event"], row["id"]) > (old["event"], old["id"]):
                        selected[key] = row
                return selected

            def cell(row, quality, calibrations, at):
                if row is None:
                    return None
                verdict = quality.get(row["id"])
                valid = row["valid"] if verdict is None else verdict["valid"]
                if not valid or row["raw"] is None:
                    return None
                calibration = calibrations.get(row["calibration"])
                if calibration is None or calibration["deleted"]:
                    return None
                if not calibration["start"] <= row["event"] < calibration["end"]:
                    return None
                value = Fraction(row["raw"]) * Fraction(calibration["gain"]) + Fraction(calibration["offset"])
                return dict(measurement=row["id"], revision=row["revision"],
                            calibration_revision=calibration["revision"], value=str(value))
        '''),
        "fabops/domain.py": code('''
            """Materialize ordered historical left joins without sharing query state."""
            from .history import visible
            from .metrology import choose, cell

            def run(request):
                output = []
                for query in request["queries"]:
                    measurements = visible(request["measurements"], query["asof"])
                    quality = visible(request["quality"], query["asof"])
                    calibrations = visible(request["calibrations"], query["asof"])
                    selected = choose(measurements, quality, query["at"])
                    output.append([
                        dict(part=part, values=[cell(selected.get((part, station)), quality, calibrations, query["at"])
                                              for station in request["stations"]])
                        for part in request["parts"]])
                return output
        '''),
    }
    latest_then_visibility = code('''
        """Resolve identity revisions at the recorded-time visibility frontier."""
        def visible(rows, asof):
            current = {}
            for row in sorted(rows, key=lambda row: row["revision"]):
                current[row["id"]] = row
            return {key: row for key, row in current.items() if row["recorded"] <= asof}
    ''')
    # Match complete selection blocks to model credible but incorrect join plans.
    old_selection = (
        files["fabops/metrology.py"]
        .split("    selected = {}\n", 1)[1]
        .split("    return selected", 1)[0]
    )
    usable_selection = old_selection.replace(
        'if row["deleted"] or row["event"] > at:',
        'if row["deleted"] or row["event"] > at or not quality.get(row["id"], row)["valid"]:',
    )
    faults = (
        Change("fabops/history.py", visibility, latest_then_visibility),
        Change("fabops/metrology.py", old_selection, usable_selection),
        Change(
            "fabops/metrology.py",
            '(row["event"], row["id"]) > (old["event"], old["id"])',
            '(row["recorded"], row["id"]) > (old["recorded"], old["id"])',
        ),
        Change(
            "fabops/metrology.py",
            'calibration["start"] <= row["event"] < calibration["end"]',
            'calibration["start"] <= at < calibration["end"]',
        ),
        Change(
            "fabops/metrology.py",
            'Fraction(row["raw"]) * Fraction(calibration["gain"]) + Fraction(calibration["offset"])',
            '(Fraction(row["raw"]) + Fraction(calibration["offset"])) * Fraction(calibration["gain"])',
        ),
    )
    resurrection = Change(
        "fabops/history.py",
        'if row["recorded"] > asof:',
        'if row["recorded"] > asof or row.get("deleted", False):',
    )
    mutants = dict(
        zip(
            (
                "future_revision_hides_history",
                "quality_filtered_before_join",
                "arrival_order_wins",
                "calibration_at_query_time",
                "offset_scaled_twice",
            ),
            ((fault,) for fault in faults),
        )
    )
    mutants["tombstone_resurrection"] = (resurrection,)
    return Task(
        "A12",
        "Historical metrology joins mix future corrections with the wrong calibration interval",
        "medium",
        "revisioned_bitemporal_metrology_join",
        code("""
            Reconstruct the station measurement matrix that could have been known at each query.
            parts and stations are ordered unique string lists. queries contains {asof,at}; their
            order is arbitrary and must be preserved. asof is the inclusive recorded-time cutoff;
            at is the inclusive measurement event-time cutoff. Times are integers.

            measurements: {id,revision,recorded,part,station,event,raw,valid,deleted,calibration}.
            calibrations: {id,revision,recorded,start,end,gain,offset,deleted} with start<end.
            quality: {id,revision,recorded,valid}, where id names a measurement identity. Each list
            has unique (id,revision); revisions are positive integers. Input order and recorded
            order need not match revision order. raw is None or an exact decimal/rational string;
            gain and offset are such strings. Every revision is a full replacement record.

            For EACH query independently, first discard versions recorded after asof, then choose
            the greatest revision per id in each list. A selected deleted measurement/calibration
            removes that identity; never resurrect a superseded version. Among remaining measurement
            identities for each requested (part,station), choose greatest (event,id) with event<=at.
            This selection occurs BEFORE quality, missing-value or calibration checks. Thus a newer
            invalid measurement suppresses an older valid one; unavailable cells stay None.

            A visible quality revision overrides the selected measurement's valid flag; otherwise
            use the measurement flag. The chosen cell is None for false validity, raw=None, missing
            or deleted calibration, or calibration not covering the MEASUREMENT event time in
            [start,end). Otherwise calculate raw*gain+offset exactly and return
            {measurement:id,revision:measurement_revision,calibration_revision:revision,value:string}.
            value is a reduced fraction 'numerator/denominator', or an integer string when denominator
            is 1, as produced by fractions.Fraction. Preserve zero and negative results.

            Return one matrix per query: [{part,values:[cell in requested station order]}] in the
            requested part order. Keep parts with no measurements and ignore unrelated identities.
            At most 100 versions per list and 20 queries are supplied. No input is changed.
            The revision/query protocol is synthetic context for manufacturing-data provenance,
            not a claim of a defect in a NIST system.
        """),
        files,
        faults,
        mutants,
        tuple(metrology_cases()),
        ("nist-sms",),
        difficulty_reason="Replace a two-line static join with revision visibility, tombstone and quality precedence, event-time selection and independent calibration-time semantics across three modules. Medium difficulty remains bounded to exact relational selection; unlike the revised hydraulic task it has no continuous interval reconstruction or publication retractions.",
        version="2.0",
    )


def metrology_cases():
    def measurement(key="m", revision=1, recorded=1, event=4, raw="10", **values):
        return dict(
            id=key,
            revision=revision,
            recorded=recorded,
            event=event,
            raw=raw,
            part=values.pop("part", "p"),
            station=values.pop("station", "s"),
            valid=values.pop("valid", True),
            deleted=values.pop("deleted", False),
            calibration=values.pop("calibration", "c"),
            **values,
        )

    def calibration(
        revision=1, recorded=0, start=0, end=20, gain="1", offset="0", **values
    ):
        return dict(
            id=values.pop("id", "c"),
            revision=revision,
            recorded=recorded,
            start=start,
            end=end,
            gain=gain,
            offset=offset,
            deleted=values.pop("deleted", False),
            **values,
        )

    def quality(valid, revision=1, recorded=2, key="m"):
        return {"id": key, "revision": revision, "recorded": recorded, "valid": valid}

    def cell(value="10", key="m", revision=1, cal=1):
        return {
            "measurement": key,
            "revision": revision,
            "calibration_revision": cal,
            "value": value,
        }

    def matrix(*values, part="p"):
        return [{"part": part, "values": list(values)}]

    def request(
        rows=(), cals=None, flags=(), queries=((10, 10),), parts=("p",), stations=("s",)
    ):
        return {
            "parts": list(parts),
            "stations": list(stations),
            "measurements": list(rows),
            "calibrations": [calibration()] if cals is None else list(cals),
            "quality": list(flags),
            "queries": [{"asof": asof, "at": at} for asof, at in queries],
        }

    m = measurement()
    rows = [
        (
            "ordered_missing_cells",
            request([m], parts=("q", "p"), stations=("other", "s")),
            [
                [
                    {"part": "q", "values": [None, None]},
                    {"part": "p", "values": [None, cell()]},
                ]
            ],
        ),
        (
            "future_correction_preserves_old_view",
            request([m, measurement(revision=2, recorded=20, raw="30")]),
            [matrix(cell())],
        ),
        (
            "measurement_time_calibration",
            request([m], [calibration(end=5)]),
            [matrix(cell())],
        ),
        (
            "quality_correction_suppresses_newest",
            request([measurement("old", event=1), m], flags=[quality(False)]),
            [matrix(None)],
        ),
        (
            "later_query_sees_corrected_raw",
            request(
                [m, measurement(revision=2, recorded=20, raw="30")],
                queries=((10, 10), (20, 10)),
            ),
            [matrix(cell()), matrix(cell("30", revision=2))],
        ),
        (
            "queries_do_not_share_future_state",
            request(
                [m, measurement(revision=2, recorded=20, raw="30")],
                queries=((20, 10), (10, 10)),
            ),
            [matrix(cell("30", revision=2)), matrix(cell())],
        ),
        (
            "latest_event_not_latest_arrival",
            request([m, measurement("late", recorded=9, event=2, raw="99")]),
            [matrix(cell())],
        ),
        (
            "tombstone_does_not_resurrect",
            request([m, measurement(revision=2, recorded=5, deleted=True)]),
            [matrix(None)],
        ),
        (
            "calibration_tombstone",
            request(
                [m], [calibration(), calibration(revision=2, recorded=5, deleted=True)]
            ),
            [matrix(None)],
        ),
        (
            "quality_revocation_then_clear",
            request(
                [m],
                flags=[quality(False), quality(True, revision=2, recorded=7)],
                queries=((5, 10), (7, 10)),
            ),
            [matrix(None), matrix(cell())],
        ),
        (
            "future_quality_is_invisible",
            request(
                [m], flags=[quality(True), quality(False, revision=2, recorded=30)]
            ),
            [matrix(cell())],
        ),
        (
            "future_calibration_preserves_known_revision",
            request(
                [m], [calibration(), calibration(revision=2, recorded=30, gain="2")]
            ),
            [matrix(cell())],
        ),
        (
            "gain_and_offset_are_distinct",
            request([measurement(raw="3/2")], [calibration(gain="2", offset="1/3")]),
            [matrix(cell("10/3"))],
        ),
        (
            "zero_and_negative",
            request([measurement(raw="0")], [calibration(gain="3", offset="-2")]),
            [matrix(cell("-2"))],
        ),
        ("zero_preserved", request([measurement(raw="0")]), [matrix(cell("0"))]),
        (
            "newest_null_does_not_fallback",
            request([measurement("old", event=1), measurement(raw=None)]),
            [matrix(None)],
        ),
        (
            "calibration_end_is_exclusive",
            request([m], [calibration(end=4)], queries=((10, 3), (10, 4))),
            [matrix(None), matrix(None)],
        ),
        (
            "event_cutoff_and_start_inclusive",
            request([m], [calibration(start=4)], queries=((1, 4),)),
            [matrix(cell())],
        ),
        (
            "event_tie_uses_id",
            request([measurement("a", raw="1"), measurement("z", raw="2")]),
            [matrix(cell("2", key="z"))],
        ),
        (
            "unknown_calibration_does_not_fallback",
            request([measurement("old", event=1), measurement(calibration="absent")]),
            [matrix(None)],
        ),
        (
            "quality_overrides_raw_flag",
            request([measurement(valid=False)], flags=[quality(True)]),
            [matrix(cell())],
        ),
        (
            "greatest_revision_not_recorded_time",
            request(
                [
                    measurement(revision=3, recorded=2, raw="3"),
                    measurement(revision=2, recorded=8, raw="2"),
                ]
            ),
            [matrix(cell("3", revision=3))],
        ),
        (
            "calibration_interval_corrected",
            request(
                [m],
                [calibration(), calibration(revision=2, recorded=5, start=6)],
                queries=((4, 10), (5, 10)),
            ),
            [matrix(cell()), matrix(None)],
        ),
        (
            "all_cells_unavailable",
            request([], parts=("q", "p")),
            [[{"part": "q", "values": [None]}, {"part": "p", "values": [None]}]],
        ),
        ("no_stations", request([m], stations=()), [[{"part": "p", "values": []}]]),
        (
            "hidden_quality_correction_blocks_older_fallback",
            request(
                [measurement("old", event=1), m],
                flags=[quality(False, recorded=5)],
                queries=((4, 10), (5, 10)),
            ),
            [matrix(cell()), matrix(None)],
        ),
        (
            "newer_raw_invalid_blocks_older_fallback",
            request([measurement("old", event=1), measurement(valid=False)]),
            [matrix(None)],
        ),
        ("no_queries", request([m], queries=()), []),
    ]
    for index, (name, data, expected) in enumerate(rows):
        yield Case(name, data, expected, public=index < 4)


def revised_hydraulic_windows():
    history = code('''
        """Resolve full replacement records before interpreting deletion or quality."""
        def visible(rows, asof):
            selected = {}
            for row in rows:
                if row["recorded"] <= asof:
                    old = selected.get(row["id"])
                    if old is None or row["revision"] > old["revision"]:
                        selected[row["id"]] = row
            return [row for row in selected.values() if not row["deleted"]]
    ''')
    calibrate = code("""
        def calibrate(segment, calibrations):
            a, b, va, vb = segment
            result = []
            for calibration in calibrations:
                left = max(a, F(calibration["start"]))
                right = min(b, F(calibration["end"]))
                if left >= right:
                    continue
                gain, offset = F(calibration["gain"]), F(calibration["offset"])
                raw_left = va + (vb - va) * (left - a) / (b - a)
                raw_right = va + (vb - va) * (right - a) / (b - a)
                result.append((left, right, raw_left * gain + offset, raw_right * gain + offset))
            return result
    """)
    files = {
        "fabops/history.py": history,
        "fabops/support.py": code('''
            """Build factory-time support, respecting epochs, invalid knots and calibration intervals."""
            from fractions import Fraction as F

            def segments(samples, clocks, calibrations, channel, maximum_gap):
                groups = {}
                for sample in samples:
                    if sample["channel"] == channel:
                        groups.setdefault(sample["epoch"], []).append(sample)
                clock_map = {(clock["channel"], clock["epoch"]): clock for clock in clocks}
                active = [row for row in calibrations if row["channel"] == channel]
                result = []
                for epoch, rows in groups.items():
                    clock = clock_map[channel, epoch]
                    def factory_time(row):
                        return F(clock["global_origin"]) + (F(row["t"]) - F(clock["local_origin"])) * F(clock["rate"])
                    ordered = sorted(rows, key=lambda row: F(row["t"]))
                    for first, second in zip(ordered, ordered[1:]):
                        a, b = factory_time(first), factory_time(second)
                        if not first["valid"] or not second["valid"]:
                            continue
                        if b - a > F(maximum_gap):
                            continue
                        segment = (a, b, F(first["raw"]), F(second["raw"]))
                        result.extend(calibrate(segment, active))
                return sorted(result)

        ''')
        + "\n"
        + calibrate,
        "fabops/integrate.py": code('''
            """Integrate products over intersections of two piecewise linear supports."""
            from fractions import Fraction as F

            def value(segment, at):
                a, b, va, vb = segment
                return va + (vb - va) * (at - a) / (b - a)

            def measure(pressure, flow, start, end):
                covered = volume = work = F(0)
                for p in pressure:
                    for q in flow:
                        left, right = max(start, p[0], q[0]), min(end, p[1], q[1])
                        if left >= right:
                            continue
                        width = right - left
                        p0, p1 = value(p, left), value(p, right)
                        q0, q1 = value(q, left), value(q, right)
                        dp, dq = p1 - p0, q1 - q0
                        covered += width
                        volume += width * (q0 + q1) / 120
                        work += width * (p0 * q0 + (p0 * dq + q0 * dp) / 2 + dp * dq / 3) / 600
                return covered, volume, work
        '''),
        "fabops/windows.py": code('''
            """Publish exact window values and compensating retractions for changed results."""
            from fractions import Fraction as F
            from .integrate import measure

            def summarize(window, pressure, flow, minimum):
                start, end = F(window["start"]), F(window["end"])
                covered, volume, work = measure(pressure, flow, start, end)
                coverage = covered / (end - start)
                accepted = covered > 0 and coverage >= F(minimum)
                return dict(id=window["id"], coverage=str(coverage), accepted=accepted,
                            volume=str(volume) if accepted else None,
                            work=str(work) if accepted else None)

            def changes(previous, current):
                events = []
                for key in sorted(current):
                    old, new = previous.get(key), current[key]
                    if old == new:
                        continue
                    if old is not None:
                        events.append(dict(op="retract", value=old))
                    events.append(dict(op="upsert", value=new))
                return events
        '''),
        "fabops/domain.py": code('''
            """Reconstruct each recorded-time snapshot, then publish only derived changes."""
            from .history import visible
            from .support import segments
            from .windows import summarize, changes

            def run(request):
                output, previous = [], {}
                for asof in request["queries"]:
                    samples = visible(request["samples"], asof)
                    calibrations = visible(request["calibrations"], asof)
                    support = {channel: segments(samples, request["clocks"], calibrations, channel,
                                                 request["max_gap"][channel])
                               for channel in ("pressure", "flow")}
                    current = {window["id"]: summarize(window, support["pressure"], support["flow"],
                                                       request["min_coverage"])
                               for window in request["windows"]}
                    output.append(dict(windows=[current[key] for key in sorted(current)],
                                       changes=changes(previous, current)))
                    previous = current
                return output
        '''),
    }
    stale_history = code('''
        """Resolve full replacement records before interpreting deletion or quality."""
        def visible(rows, asof):
            selected = {}
            for row in sorted(rows, key=lambda row: row["revision"]):
                selected[row["id"]] = row
            return [row for row in selected.values() if row["recorded"] <= asof and not row["deleted"]]
    ''')
    whole_segment_calibration = code("""
        def calibrate(segment, calibrations):
            a, b, va, vb = segment
            for calibration in calibrations:
                if F(calibration["start"]) <= a < F(calibration["end"]):
                    gain, offset = F(calibration["gain"]), F(calibration["offset"])
                    return [(a, b, va * gain + offset, vb * gain + offset)]
            return []
    """)
    coarse_measure = code("""
        def measure(pressure, flow, start, end):
            if not pressure or not flow:
                return F(0), F(0), F(0)
            left = max(start, pressure[0][0], flow[0][0])
            right = min(end, pressure[-1][1], flow[-1][1])
            if left >= right:
                return F(0), F(0), F(0)
            def sample_at(signal, at):
                earlier = [segment for segment in signal if segment[0] <= at]
                segment = max(earlier, key=lambda row: row[0]) if earlier else signal[0]
                return value(segment, min(segment[1], max(segment[0], at)))
            p0, p1 = sample_at(pressure, left), sample_at(pressure, right)
            q0, q1 = sample_at(flow, left), sample_at(flow, right)
            width = right - left
            return width, width * (q0 + q1) / 120, width * (p0 * q0 + p1 * q1) / 1200
    """)
    exact_measure = (
        "def measure" + files["fabops/integrate.py"].split("def measure", 1)[1]
    )
    product_mutation = Change(
        "fabops/integrate.py",
        "p0 * q0 + (p0 * dq + q0 * dp) / 2 + dp * dq / 3",
        "(p0 * q0 + p1 * q1) / 2",
    )
    faults = (
        Change("fabops/history.py", history, stale_history),
        Change(
            "fabops/support.py",
            'F(clock["global_origin"]) + (F(row["t"]) - F(clock["local_origin"])) * F(clock["rate"])',
            '(F(clock["global_origin"]) + F(row["t"]) - F(clock["local_origin"])) * F(clock["rate"])',
        ),
        Change(
            "fabops/support.py",
            'ordered = sorted(rows, key=lambda row: F(row["t"]))',
            'ordered = sorted((row for row in rows if row["valid"]), key=lambda row: F(row["t"]))',
        ),
        Change("fabops/support.py", calibrate, whole_segment_calibration),
        Change("fabops/integrate.py", exact_measure, coarse_measure),
        Change(
            "fabops/support.py",
            "if b - a > F(maximum_gap):",
            'if F(second["t"]) - F(first["t"]) > F(maximum_gap):',
        ),
        Change(
            "fabops/windows.py",
            "coverage = covered / (end - start)",
            "coverage = min(sum(max(F(0), min(end, row[1]) - max(start, row[0])) for row in pressure),\n                   sum(max(F(0), min(end, row[1]) - max(start, row[0])) for row in flow)) / (end - start)",
        ),
        Change(
            "fabops/windows.py",
            'if old is not None:\n            events.append(dict(op="retract", value=old))',
            'if old is not None and old["accepted"] is False:\n            events.append(dict(op="retract", value=old))',
        ),
    )
    names = (
        "future_revision_erases_known_knots",
        "clock_offset_scaled",
        "invalid_knots_removed",
        "single_calibration_per_segment",
        "coarse_window_resampling",
        "local_time_gap_check",
        "marginal_coverage",
        "missing_accepted_retractions",
    )
    mutants = dict(zip(names, ((fault,) for fault in faults)))
    mutants["product_endpoint_trapezoid"] = (product_mutation,)
    return Task(
        "A29",
        "Hydraulic window revisions lose joint support and publish uncompensated corrections",
        "hard",
        "revisioned_multirate_hydraulic_retractions",
        code("""
            Reconstruct exact hydraulic analytics at each recorded-time frontier and emit a
            compensating publication changelog. This is a bounded synthetic streaming protocol
            inspired by multirate hydraulic measurements and manufacturing clock/data provenance;
            it is not a claim that the source dataset has missing data or these faults.

            samples contains full replacement versions:
            {id,revision,recorded,channel,epoch,t,raw,valid,deleted}. calibrations contains versions:
            {id,revision,recorded,channel,start,end,gain,offset,deleted}. channel is pressure or flow.
            queries is a nondecreasing list of inclusive recorded-time cutoffs. For EACH query and
            each version list, exclude recorded>asof FIRST, select greatest revision per identity,
            then remove deleted identities. Revisions are positive integers; (id,revision) is unique
            per list; input/recorded order need not agree with revision order. Corrections can change
            every other field. An invalid sample remains an adjacency barrier; deletion removes it.

            clocks has one fixed map per (channel,epoch): {channel,epoch,local_origin,global_origin,rate}.
            Factory time = global_origin + (t-local_origin)*rate, with rate>0. Group samples by channel
            AND epoch, sort by local t, and consider ONLY adjacent pairs. Never bridge epoch resets.
            Keep a pair only when both valid and factory-time width<=max_gap[channel]. Its raw value
            varies linearly between endpoints. There is no extrapolation or hold-last-value support.
            Selected sample timestamps are unique per group. Different epoch spans of a channel do
            not overlap (touching is allowed). All referenced clock maps exist.

            Selected calibration intervals [start,end) are in FACTORY time and do not overlap for
            a channel. They may have gaps. Split raw linear support at these boundaries; interpolate
            RAW value at each intersection endpoint, then apply raw*gain+offset under that interval.
            A calibration step is a discontinuity, not a ramp between differently calibrated knots.
            Missing calibration means unsupported time. All times, raw values, gains, offsets,
            max_gap and min_coverage are exact integer/decimal/rational strings, except recorded,
            revision and queries which are integers. Valid calibrated values are nonnegative.

            windows contains unique {id,start,end}, start<end; windows may overlap. Intersect pressure
            and flow supports within each window, splitting at knots/boundaries of BOTH channels.
            coverage is JOINT supported duration / full window duration. Accept only if duration>0
            and coverage>=min_coverage (0<=minimum<=1). Integrate flow (litres/minute) over supported
            seconds and divide by 60 to get volume (litres). Integrate pressure (bar) times flow and
            divide by 600 to get work (kJ). The product of two linear signals is quadratic and must
            be integrated exactly, not by trapezoids of endpoint products. For rejected windows
            volume and work are None; still report exact coverage.

            A window value is {id,coverage,accepted,volume,work}. Numeric outputs are reduced fraction
            strings, or integer strings when denominator is 1 (fractions.Fraction representation).
            For each query return {windows:[values sorted by id],changes:[events]}. On the first
            query emit {op:'upsert',value:window_value} for each window. On later queries, compare
            derived values: for each changed window emit {op:'retract',value:previous_value} followed
            by its upsert. Unchanged values emit nothing, including equal-value source revisions.
            Process changed windows in id order; rejected values also participate in this protocol.
            Windows are fixed across queries. Return results in query order, without changing input.
            At most 100 versions per source list, 20 windows and 20 queries are supplied. Full
            recomputation is permitted; no unmentioned persistence or performance requirement applies.
        """),
        files,
        faults,
        mutants,
        tuple(hydraulic_cases()),
        ("zema-hydraulic", "nist-sms"),
        difficulty_reason="Five interacting modules require reconstruction of revision visibility, affine clock/epoch adjacency, calibration-partitioned support, exact products on joint multirate intervals, and compensating publication deltas. Eight independent realistic fault sites include whole visibility, calibration and interval-integration algorithms. The baseline resamples window endpoints and cannot retain internal support gaps or quadratic signal products; nine mutants include a partial restoration that still uses endpoint-product trapezoids. Hidden cases combine corrections, discontinuities and clock/gap decisions. This is substantially broader than a static four-line hydraulic integration repair and the discrete A12 join.",
        version="2.0",
    )


def hydraulic_cases():
    def sample(
        key,
        channel,
        t,
        raw,
        revision=1,
        recorded=0,
        epoch="e",
        valid=True,
        deleted=False,
    ):
        return {
            "id": key,
            "channel": channel,
            "t": str(t),
            "raw": str(raw),
            "revision": revision,
            "recorded": recorded,
            "epoch": epoch,
            "valid": valid,
            "deleted": deleted,
        }

    def cal(
        channel,
        key=None,
        start="-100",
        end="100",
        gain="1",
        offset="0",
        revision=1,
        recorded=0,
        deleted=False,
    ):
        return {
            "id": key or channel,
            "channel": channel,
            "start": str(start),
            "end": str(end),
            "gain": str(gain),
            "offset": str(offset),
            "revision": revision,
            "recorded": recorded,
            "deleted": deleted,
        }

    def clock(channel, epoch="e", local="0", global_time="0", rate="1"):
        return {
            "channel": channel,
            "epoch": epoch,
            "local_origin": str(local),
            "global_origin": str(global_time),
            "rate": str(rate),
        }

    def window(key="w", start="0", end="2"):
        return {"id": key, "start": str(start), "end": str(end)}

    def metric(coverage="1", volume="2", work="120", key="w", accepted=True):
        return {
            "id": key,
            "coverage": coverage,
            "accepted": accepted,
            "volume": volume if accepted else None,
            "work": work if accepted else None,
        }

    def expected(*snapshots):
        # Only format explicitly supplied expected values; no signal algorithm is called here.
        output, previous = [], {}
        for snapshot in snapshots:
            events = []
            for value in snapshot:
                key = value["id"]
                if previous.get(key) != value:
                    if key in previous:
                        events.append({"op": "retract", "value": previous[key]})
                    events.append({"op": "upsert", "value": value})
            output.append({"windows": list(snapshot), "changes": events})
            previous = {value["id"]: value for value in snapshot}
        return output

    p = [sample("p0", "pressure", 0, 600), sample("p2", "pressure", 2, 600)]
    q = [sample("q0", "flow", 0, 60), sample("q2", "flow", 2, 60)]

    def request(
        samples=None,
        calibrations=None,
        clocks=None,
        windows=None,
        queries=(1,),
        gap="3",
        minimum="1",
    ):
        return {
            "samples": p + q if samples is None else samples,
            "calibrations": [cal("pressure"), cal("flow")]
            if calibrations is None
            else calibrations,
            "clocks": [clock("pressure"), clock("flow")] if clocks is None else clocks,
            "windows": [window()] if windows is None else windows,
            "queries": list(queries),
            "max_gap": {"pressure": gap, "flow": gap},
            "min_coverage": minimum,
        }

    yes, no = metric(), metric("0", accepted=False)
    rows = [
        ("constant_units_and_publication", request(), expected([yes])),
        (
            "joint_linear_product",
            request(
                [
                    sample("p0", "pressure", 0, 0),
                    sample("p2", "pressure", 2, 600),
                    sample("q0", "flow", 0, 0),
                    sample("q2", "flow", 2, 60),
                ]
            ),
            expected([metric(volume="1", work="40")]),
        ),
        (
            "late_raw_correction_retracts",
            request(
                p + q + [sample("q2", "flow", 2, 120, revision=2, recorded=5)],
                queries=(1, 5),
            ),
            expected([yes], [metric(volume="3", work="180")]),
        ),
        (
            "calibration_step_inside_support",
            request(
                calibrations=[
                    cal("pressure", "a", end="1"),
                    cal("pressure", "b", start="1", gain="2"),
                    cal("flow"),
                ]
            ),
            expected([metric(work="180")]),
        ),
        (
            "future_version_retains_known_support",
            request(
                p + q + [sample("p2", "pressure", 2, 1200, revision=2, recorded=8)]
            ),
            expected([yes]),
        ),
        (
            "offset_not_scaled_by_clock_rate",
            request(
                [
                    sample("p0", "pressure", 0, 600),
                    sample("p1", "pressure", 1, 600),
                    sample("q0", "flow", 0, 60),
                    sample("q1", "flow", 1, 60),
                ],
                clocks=[
                    clock("pressure", global_time="10", rate="2"),
                    clock("flow", global_time="10", rate="2"),
                ],
                windows=[window(start="10", end="12")],
            ),
            expected([yes]),
        ),
        (
            "invalid_knot_blocks_both_neighbors",
            request(p + q + [sample("bad", "pressure", 1, 600, valid=False)]),
            expected([no]),
        ),
        (
            "factory_gap_exceeds_limit",
            request(
                [sample("p0", "pressure", 0, 600), sample("p1", "pressure", 1, 600)]
                + q,
                clocks=[clock("pressure", rate="2"), clock("flow")],
                gap="3/2",
            ),
            expected([no]),
        ),
        (
            "compressed_clock_gap_is_supported",
            request(
                [sample("p0", "pressure", 0, 600), sample("p4", "pressure", 4, 600)]
                + q,
                clocks=[clock("pressure", rate="1/2"), clock("flow")],
                gap="2",
            ),
            expected([yes]),
        ),
        (
            "different_marginals_joint_half",
            request(
                [
                    sample("p0", "pressure", 0, 600),
                    sample("p2", "pressure", 2, 600),
                    sample("q1", "flow", 1, 60),
                    sample("q3", "flow", 3, 60),
                ],
                windows=[window(end="3")],
                minimum="1/3",
            ),
            expected([metric("1/3", "1", "60")]),
        ),
        (
            "disjoint_support_is_not_coverage",
            request(
                [
                    sample("p0", "pressure", 0, 600),
                    sample("p1", "pressure", 1, 600),
                    sample("q1", "flow", 1, 60),
                    sample("q2", "flow", 2, 60),
                ],
                minimum="0",
            ),
            expected([no]),
        ),
        (
            "accepted_correction_retracts_old_value",
            request(
                p
                + q
                + [
                    sample("q0", "flow", 0, 120, revision=2, recorded=5),
                    sample("q2", "flow", 2, 120, revision=2, recorded=5),
                ],
                queries=(1, 5),
            ),
            expected([yes], [metric(volume="4", work="240")]),
        ),
        (
            "calibration_gap_is_unsupported",
            request(
                calibrations=[
                    cal("pressure", "a", end="1/2"),
                    cal("pressure", "b", start="3/2"),
                    cal("flow"),
                ],
                minimum="1/2",
            ),
            expected([metric("1/2", "1", "60")]),
        ),
        (
            "linear_raw_split_before_calibration",
            request(
                [sample("p0", "pressure", 0, 0), sample("p2", "pressure", 2, 1200)] + q,
                calibrations=[
                    cal("pressure", "a", end="1"),
                    cal("pressure", "b", start="1", gain="2"),
                    cal("flow"),
                ],
            ),
            expected([metric(work="210")]),
        ),
        (
            "revised_calibration_retracts",
            request(
                calibrations=[
                    cal("pressure"),
                    cal("pressure", revision=2, recorded=5, gain="2"),
                    cal("flow"),
                ],
                queries=(1, 5),
            ),
            expected([yes], [metric(work="240")]),
        ),
        (
            "equal_value_revision_has_no_delta",
            request(
                p + q + [sample("p2", "pressure", 2, 600, revision=2, recorded=5)],
                queries=(1, 5, 5),
            ),
            expected([yes], [yes], [yes]),
        ),
        (
            "deleted_invalid_knot_restores_adjacency",
            request(
                p
                + q
                + [
                    sample("bad", "pressure", 1, 600, valid=False),
                    sample(
                        "bad",
                        "pressure",
                        1,
                        600,
                        valid=False,
                        deleted=True,
                        revision=2,
                        recorded=5,
                    ),
                ],
                queries=(1, 5),
            ),
            expected([no], [yes]),
        ),
        (
            "deleted_endpoint_revokes_result",
            request(
                p
                + q
                + [
                    sample(
                        "p2", "pressure", 2, 600, deleted=True, revision=2, recorded=5
                    )
                ],
                queries=(1, 5),
            ),
            expected([yes], [no]),
        ),
        (
            "epochs_are_not_joined",
            request(
                [
                    sample("p0", "pressure", 0, 600, epoch="a"),
                    sample("p2", "pressure", 2, 600, epoch="b"),
                ]
                + q,
                clocks=[clock("pressure", "a"), clock("pressure", "b"), clock("flow")],
            ),
            expected([no]),
        ),
        (
            "local_origin_and_multirate_knots",
            request(
                [sample("p4", "pressure", 4, 600), sample("p5", "pressure", 5, 600)]
                + q
                + [sample("q1", "flow", 1, 60)],
                clocks=[clock("pressure", local="4", rate="2"), clock("flow")],
            ),
            expected([yes]),
        ),
        (
            "no_extrapolation_clipped_window",
            request(windows=[window(start="-1", end="3")], minimum="1/2"),
            expected([metric("1/2", "2", "120")]),
        ),
        (
            "coverage_threshold_rejects_partial",
            request(windows=[window(start="-1", end="3")], minimum="3/4"),
            expected([metric("1/2", accepted=False)]),
        ),
        (
            "overlapping_windows_sorted_and_independent",
            request(windows=[window("z", "1", "2"), window("a", "0", "3/2")]),
            expected(
                [
                    metric(volume="3/2", work="90", key="a"),
                    metric(volume="1", work="60", key="z"),
                ]
            ),
        ),
        (
            "offset_applied_after_gain",
            request(
                calibrations=[cal("pressure", gain="1/2", offset="300"), cal("flow")]
            ),
            expected([yes]),
        ),
        (
            "zero_flow_remains_accepted",
            request(p + [sample("q0", "flow", 0, 0), sample("q2", "flow", 2, 0)]),
            expected([metric(volume="0", work="0")]),
        ),
        (
            "calibration_deletion_removes_support",
            request(
                calibrations=[
                    cal("pressure"),
                    cal("pressure", revision=2, recorded=5, deleted=True),
                    cal("flow"),
                ],
                queries=(1, 5),
            ),
            expected([yes], [no]),
        ),
        (
            "future_calibration_does_not_erase_old",
            request(
                calibrations=[
                    cal("pressure"),
                    cal("pressure", revision=2, recorded=5, gain="2"),
                    cal("flow"),
                ]
            ),
            expected([yes]),
        ),
        (
            "revision_priority_over_arrival_order",
            request(
                p
                + [
                    sample("q0", "flow", 0, 60),
                    sample("q2", "flow", 2, 120, revision=3, recorded=1),
                    sample("q2", "flow", 2, 180, revision=2, recorded=3),
                ],
                queries=(4,),
            ),
            expected([metric(volume="3", work="180")]),
        ),
        (
            "clock_step_and_two_late_corrections",
            request(
                [
                    sample("p0", "pressure", 0, 0),
                    sample("p1", "pressure", 1, 1200),
                    sample("q0", "flow", 0, 60),
                    sample("q1", "flow", 1, 60),
                    sample("q1", "flow", 1, 120, revision=2, recorded=5),
                ],
                calibrations=[
                    cal("pressure", "a", start="10", end="11"),
                    cal("pressure", "b", start="11", end="12", gain="2"),
                    cal(
                        "pressure",
                        "b",
                        start="11",
                        end="12",
                        gain="1",
                        revision=2,
                        recorded=7,
                    ),
                    cal("flow"),
                ],
                clocks=[
                    clock("pressure", global_time="10", rate="2"),
                    clock("flow", global_time="10", rate="2"),
                ],
                windows=[window(start="10", end="12")],
                queries=(1, 5, 7),
                gap="2",
            ),
            expected(
                [metric(work="210")],
                [metric(volume="3", work="360")],
                [metric(volume="3", work="200")],
            ),
        ),
        (
            "corrected_timestamp_moves_joint_support",
            request(
                p + q + [sample("q0", "flow", 1, 60, revision=2, recorded=5)],
                queries=(1, 5),
                minimum="1/2",
            ),
            expected([yes], [metric("1/2", "1", "60")]),
        ),
        (
            "multiple_window_retractions_are_ordered",
            request(
                p + q + [sample("q2", "flow", 2, 120, revision=2, recorded=5)],
                windows=[window("z", "1", "2"), window("a", "0", "1")],
                queries=(1, 5),
            ),
            expected(
                [
                    metric(volume="1", work="60", key="a"),
                    metric(volume="1", work="60", key="z"),
                ],
                [
                    metric(volume="5/4", work="75", key="a"),
                    metric(volume="7/4", work="105", key="z"),
                ],
            ),
        ),
        (
            "fractional_multirate_product_clipping",
            request(
                [
                    sample("p0", "pressure", 0, 0),
                    sample("p2", "pressure", 2, 600),
                    sample("q0", "flow", 0, 0),
                    sample("q1", "flow", 1, 30),
                    sample("q2", "flow", 2, 60),
                ],
                windows=[window(start="1/2", end="3/2")],
            ),
            expected([metric(volume="1/2", work="65/4")]),
        ),
        ("empty_channels", request(samples=[]), expected([no])),
        ("empty_window_set", request(windows=[], queries=(1, 2)), expected([], [])),
    ]
    for index, (name, data, result) in enumerate(rows):
        yield Case(name, data, result, public=index < 4)
