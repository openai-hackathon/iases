"""Hard process-log repairs inspired by production lifecycle and quantity fields.

All networks, lifecycle events, quantities and expected results are authored
synthetic fixtures. The source event log is neither bundled nor copied.
"""

from .schema import Case, Change, Task, code


def tasks():
    yield conformance_task()
    yield lifecycle_task()
    yield quantity_task()


def transition(identifier, label, consume, produce):
    return dict(id=identifier, label=label, consume=consume, produce=produce)


def net_request(initial, final, transitions, trace, capacities=None):
    places = sorted(
        set(initial)
        | set(final)
        | {
            place
            for item in transitions
            for field in ("consume", "produce")
            for place in item[field]
        }
    )
    return dict(
        capacities=capacities or {place: 3 for place in places},
        initial=initial,
        final=final,
        transitions=transitions,
        trace=trace,
    )


def conformance_task():
    files = {
        "fabops/net.py": code('''
            """Fire a weighted transition against a bounded marking atomically."""
            def fire(marking, transition, places, capacities):
                current = dict(zip(places, marking))
                if any(current[p] < count for p, count in transition["consume"].items()):
                    return None
                result = dict(current)
                for p, count in transition["consume"].items():
                    result[p] -= count
                for p, count in transition["produce"].items():
                    result[p] += count
                if any(result[p] > capacities[p] for p in places):
                    return None
                return tuple(result[p] for p in places)
        '''),
        "fabops/replay.py": code('''
            """Search full markings, retaining globally minimal conformance witnesses."""
            import heapq
            from .net import fire

            def replay(request):
                places = sorted(request["capacities"])
                initial = tuple(request["initial"].get(p, 0) for p in places)
                final = tuple(request["final"].get(p, 0) for p in places)
                trace = request["trace"]
                queue = [(0, (), 0, initial)]
                best = {(0, initial): (0, ())}
                while queue:
                    silent, path, index, marking = heapq.heappop(queue)
                    if best.get((index, marking)) != (silent, path):
                        continue
                    if index == len(trace) and marking == final:
                        return dict(accepted=True, witness=list(path), silent=silent,
                                    marking=dict(zip(places, marking)))
                    for item in sorted(request["transitions"], key=lambda item: item["id"]):
                        hidden = item["label"] is None
                        if not hidden and (index == len(trace) or item["label"] != trace[index]):
                            continue
                        changed = fire(marking, item, places, request["capacities"])
                        if changed is None:
                            continue
                        target = (index + int(not hidden), changed)
                        score = (silent + int(hidden), path + (item["id"],))
                        if target not in best or score < best[target]:
                            best[target] = score
                            heapq.heappush(queue, (*score, *target))
                return dict(accepted=False, witness=[], silent=None,
                            marking=dict(zip(places, initial)))
        '''),
        "fabops/domain.py": code("""
            from .replay import replay
            def run(request):
                return replay(request)
        """),
    }
    faults = (
        Change("fabops/net.py", "current[p] < count", "current[p] < 1"),
        Change(
            "fabops/net.py",
            "if any(result[p] > capacities[p] for p in places):",
            'if any(current[p] + transition["produce"].get(p, 0) > capacities[p] for p in places):',
        ),
        Change(
            "fabops/replay.py",
            "if index == len(trace) and marking == final:",
            "if index == len(trace):",
        ),
        Change(
            "fabops/replay.py",
            "if target not in best or score < best[target]:",
            "if all(position != target[0] for position, _ in best):",
        ),
    )
    mutants = {
        f"unfixed_{name}": (fault,)
        for name, fault in zip(
            ("arc_multiplicity", "capacity", "final_marking", "silent_closure"), faults
        )
    }
    mutants["first_label_only"] = (
        Change(
            "fabops/replay.py",
            "heapq.heappush(queue, (*score, *target))",
            "heapq.heappush(queue, (*score, *target))\n                if not hidden:\n                    break",
        ),
    )
    return Task(
        "F25",
        "Production conformance replay loses parallel tokens and silent routing choices",
        "hard",
        "bounded_weighted_workflow_conformance",
        code("""
            Reconstruct a firing witness for one production trace in a bounded weighted Petri net.
            capacities maps up to six named places to positive integer limits at most three.
            initial and final map places to nonnegative token counts within those limits; omitted
            places mean zero. Each of at most ten transitions has a unique string id, label (a
            string activity or null for an unobserved routing transition), and consume/produce
            mappings with positive integer arc weights. Every mentioned place has a capacity.
            A firing is allowed only when all input multiplicities are available and the marking
            AFTER atomic consumption and production respects every capacity. Self loops consume
            before producing. Silent cycles, parallel branches, repeated labels and repeated
            activity occurrences are valid. trace contains at most eight observed activity labels.

            Find a sequence whose non-null labels equal trace exactly and whose complete final
            marking equals final, including zero and leftover places. Silent firings can occur
            before, between or after observations. Among all witnesses minimize the number of
            silent firings, then lexicographically minimize the full sequence of transition ids.
            Return accepted=true, witness as that sequence, silent as its number of silent firings,
            and marking containing every place. If no witness exists, return accepted=false,
            witness=[], silent=null and the original marking with missing places filled by zero.
            Rejected branches must not consume tokens from other branches or the request. Search
            must terminate for silent cycles; tracking only activity position cannot distinguish
            parallel markings. All input lists may arrive in arbitrary order except trace.
        """),
        files,
        faults,
        mutants,
        tuple(conformance_cases()),
        ("production-log",),
        difficulty_reason="Requires finite-state shortest-witness search across silent cycles and nondeterministic repeated labels while preserving weighted atomic firing, capacities and complete parallel markings in separate modules.",
    )


def conformance_cases():
    t = transition

    def case(name, request, witness, silent, marking, public=False):
        return Case(
            name,
            request,
            dict(
                accepted=witness is not None,
                witness=witness or [],
                silent=silent,
                marking=marking,
            ),
            public=public,
        )

    linear = [t("etch", "etch", {"raw": 1}, {"done": 1})]
    yield case(
        "linear_control",
        net_request({"raw": 1}, {"done": 1}, linear, ["etch"]),
        ["etch"],
        0,
        {"done": 1, "raw": 0},
        True,
    )
    parallel = [
        t("split", None, {"raw": 1}, {"a": 1, "b": 1}),
        t("measure", "measure", {"a": 1}, {"a_done": 1}),
        t("clean", "clean", {"b": 1}, {"b_done": 1}),
        t("join", None, {"a_done": 1, "b_done": 1}, {"done": 1}),
    ]
    yield case(
        "parallel_join",
        net_request({"raw": 1}, {"done": 1}, parallel, ["clean", "measure"]),
        ["split", "clean", "measure", "join"],
        2,
        {"a": 0, "a_done": 0, "b": 0, "b_done": 0, "done": 1, "raw": 0},
        True,
    )
    weighted = [t("batch", "inspect", {"p": 2}, {"p": 2})]
    yield case(
        "weighted_self_loop_unavailable",
        net_request({"p": 1}, {"p": 1}, weighted, ["inspect"]),
        None,
        None,
        {"p": 1},
        True,
    )
    yield case(
        "leftover_parallel_token",
        net_request({"raw": 1, "hold": 1}, {"done": 1}, linear, ["etch"]),
        None,
        None,
        {"done": 0, "hold": 1, "raw": 1},
        True,
    )
    yield case(
        "empty_trace_exact_marking",
        net_request({"p": 1}, {"p": 1}, [], []),
        [],
        0,
        {"p": 1},
    )
    yield case(
        "empty_trace_mismatch", net_request({"p": 1}, {}, [], []), None, None, {"p": 1}
    )
    yield case(
        "unmatched_activity",
        net_request({"raw": 1}, {"done": 1}, linear, ["polish"]),
        None,
        None,
        {"done": 0, "raw": 1},
    )
    yield case(
        "weighted_self_loop_available",
        net_request({"p": 2}, {"p": 2}, weighted, ["inspect", "inspect"]),
        ["batch", "batch"],
        0,
        {"p": 2},
    )
    overflow = [
        t("grow", None, {"p": 1}, {"q": 2}),
        t("trim", "trim", {"q": 2}, {"done": 1}),
    ]
    yield case(
        "transient_capacity_overflow",
        net_request(
            {"p": 1}, {"done": 1}, overflow, ["trim"], {"p": 1, "q": 1, "done": 1}
        ),
        None,
        None,
        {"done": 0, "p": 1, "q": 0},
    )
    yield case(
        "capacity_after_consumption",
        net_request({"p": 2}, {"p": 2}, weighted, ["inspect"], {"p": 2}),
        ["batch"],
        0,
        {"p": 2},
    )
    choices = [
        t("a_dead", "work", {"p": 1}, {"dead": 1}),
        t("z_live", "work", {"p": 1}, {"q": 1}),
        t("finish", "finish", {"q": 1}, {"done": 1}),
    ]
    yield case(
        "same_label_requires_lookahead",
        net_request({"p": 1}, {"done": 1}, choices, ["work", "finish"]),
        ["z_live", "finish"],
        0,
        {"dead": 0, "done": 1, "p": 0, "q": 0},
    )
    alternatives = [
        t("a_detour", None, {"p": 1}, {"q": 1}),
        t("b_work", "work", {"q": 1}, {"done": 1}),
        t("z_direct", "work", {"p": 1}, {"done": 1}),
    ]
    yield case(
        "silent_cost_before_lexical_tie",
        net_request({"p": 1}, {"done": 1}, alternatives, ["work"]),
        ["z_direct"],
        0,
        {"done": 1, "p": 0, "q": 0},
    )
    equal = [
        t("z_route", None, {"p": 1}, {"q": 1}),
        t("a_route", None, {"p": 1}, {"q": 1}),
        t("work", "work", {"q": 1}, {"done": 1}),
    ]
    yield case(
        "lexical_witness_tie",
        net_request({"p": 1}, {"done": 1}, equal, ["work"]),
        ["a_route", "work"],
        1,
        {"done": 1, "p": 0, "q": 0},
    )
    cycle = [
        t("cycle", None, {"p": 1}, {"p": 1}),
        t("work", "work", {"p": 1}, {"done": 1}),
    ]
    yield case(
        "silent_cycle_terminates",
        net_request({"p": 1}, {"done": 1}, cycle, ["work"]),
        ["work"],
        0,
        {"done": 1, "p": 0},
    )
    yield case(
        "silent_only_completion",
        net_request({"p": 1}, {"q": 1}, [t("move", None, {"p": 1}, {"q": 1})], []),
        ["move"],
        1,
        {"p": 0, "q": 1},
    )
    yield case(
        "join_missing_branch",
        net_request({"raw": 1}, {"done": 1}, parallel, ["clean"]),
        None,
        None,
        {"a": 0, "a_done": 0, "b": 0, "b_done": 0, "done": 0, "raw": 1},
    )
    rework = [
        t("visit", "work", {"p": 1}, {"q": 1}),
        t("loop", None, {"q": 1}, {"p": 1}),
        t("exit", "release", {"q": 1}, {"done": 1}),
    ]
    yield case(
        "repeated_occurrences_with_loop",
        net_request({"p": 1}, {"done": 1}, rework, ["work", "work", "release"]),
        ["visit", "loop", "visit", "exit"],
        1,
        {"done": 1, "p": 0, "q": 0},
    )

    weighted_join = [
        t("split", None, {"raw": 1}, {"p": 1, "q": 1}),
        t("inspect", "inspect", {"p": 2, "q": 1}, {"p": 2, "tested": 1}),
        t("release", "release", {"tested": 1}, {"done": 1}),
    ]
    yield case(
        "silent_split_does_not_satisfy_weighted_join",
        net_request(
            {"raw": 1}, {"p": 1, "done": 1}, weighted_join, ["inspect", "release"]
        ),
        None,
        None,
        {"raw": 1, "p": 0, "q": 0, "tested": 0, "done": 0},
    )


def lifecycle_task():
    files = {
        "fabops/events.py": code('''
            """Deduplicate transport retries without collapsing simultaneous operations."""
            def normalize(events):
                seen = {}
                for event in events:
                    identifier = event["id"]
                    if identifier in seen and seen[identifier] != event:
                        raise ValueError("Conflicting event id")
                    seen[identifier] = dict(event)
                return [seen[key] for key in sorted(seen)]
        '''),
        "fabops/correlation.py": code('''
            """Retain every maximum-cardinality lifecycle interpretation."""
            def compatible(start, end):
                return (all(start[key] == end[key] for key in ("case", "activity", "resource"))
                        and start["time"] <= end["time"]
                        and (start.get("run") is None or end.get("run") is None
                             or start["run"] == end["run"]))

            def matchings(events):
                starts = [event for event in events if event["kind"] == "start"]
                ends = [event for event in events if event["kind"] == "complete"]
                best, results = -1, []
                def visit(index, used, pairs):
                    nonlocal best, results
                    if index == len(starts):
                        if len(pairs) > best:
                            best, results = len(pairs), []
                        if len(pairs) == best:
                            results.append(tuple(sorted(pairs)))
                        return
                    start = starts[index]
                    visit(index + 1, used, pairs)
                    for end in ends:
                        if end["id"] in used or not compatible(start, end):
                            continue
                        visit(index + 1, used | {end["id"]}, pairs + [(start["id"], end["id"])])
                visit(0, set(), [])
                return results
        '''),
        "fabops/domain.py": code("""
            from .events import normalize
            from .correlation import matchings

            def run(request):
                events = normalize(request["events"])
                interpretations = matchings(events)
                certain = set(interpretations[0])
                for pairs in interpretations[1:]:
                    certain.intersection_update(pairs)
                ever_used = {identifier for pairs in interpretations for pair in pairs for identifier in pair}
                by_id = {event["id"]: event for event in events}
                durations = [sum(by_id[end]["time"] - by_id[start]["time"]
                                 for start, end in pairs) for pairs in interpretations]
                return dict(matched=len(interpretations[0]), alternatives=len(interpretations),
                            certain_pairs=[list(pair) for pair in sorted(certain)],
                            certain_unmatched=sorted(set(by_id) - ever_used),
                            duration_bounds=[min(durations), max(durations)])
        """),
    }
    faults = (
        Change(
            "fabops/events.py",
            "return [seen[key] for key in sorted(seen)]",
            'return sorted(events, key=lambda event: event["id"])',
        ),
        Change(
            "fabops/correlation.py",
            'or start["run"] == end["run"]',
            'or start["case"] == end["case"]',
        ),
        Change(
            "fabops/correlation.py",
            'visit(index + 1, used | {end["id"]}, pairs + [(start["id"], end["id"])])',
            'visit(index + 1, used | {end["id"]}, pairs + [(start["id"], end["id"])])\n            break',
        ),
        Change(
            "fabops/domain.py",
            "certain.intersection_update(pairs)",
            "certain.update(pairs)",
        ),
    )
    mutants = {
        f"unfixed_{name}": (fault,)
        for name, fault in zip(
            (
                "retry_deduplication",
                "run_correlation",
                "greedy_matching",
                "certainty_intersection",
            ),
            faults,
        )
    }
    mutants["strict_positive_duration"] = (
        Change(
            "fabops/correlation.py",
            'start["time"] <= end["time"]',
            'start["time"] < end["time"]',
        ),
    )
    return Task(
        "F26",
        "Overlapping production lifecycles are reported as certain after greedy correlation",
        "hard",
        "ambiguous_lifecycle_maximum_matching",
        code("""
            Reconstruct production operation lifecycles from out-of-order events. Each event has
            id, kind (start or complete), case, activity, resource, integer time, and optionally
            run (a string operation correlation id or null). Transport retries with identical id
            and complete identical content are one event. Reusing an id with different content
            raises ValueError. Distinct ids at the same timestamp remain distinct operations.
            There are at most six distinct starts and six distinct completions after deduplication.

            A start can pair with a completion exactly when case, activity and resource all match,
            start.time <= complete.time, and the run ids agree if both are non-null. A missing or
            null run id is unknown and compatible with any run id. Each event occurs in at most
            one pair. Consider ALL globally maximum-cardinality matchings, without imposing FIFO,
            nearest-time, duration minimization, or an arbitrary greedy tie break. Unmatched events
            are allowed. Every matching is a set of (start id,completion id) pairs; duplicates from
            transport retries do not count as separate interpretations.

            Return matched (maximum pair count), alternatives (number of distinct maximum matchings),
            certain_pairs (intersection across every maximum matching, sorted lexicographically,
            encoded as two-element lists), certain_unmatched (sorted event ids unmatched in EVERY
            maximum matching), and duration_bounds [minimum,maximum] of the total paired durations
            across those matchings. An event that is unmatched in some interpretations but paired
            in others is not certainly unmatched. With no possible pairs there is one empty
            matching, and total duration is zero. Different resources or cases never correlate.
            Inputs must remain unchanged, including when duplicate-id conflicts are rejected.
        """),
        files,
        faults,
        mutants,
        tuple(lifecycle_cases()),
        ("production-log",),
        difficulty_reason="Must reconstruct all globally maximal lifecycle pairings instead of a greedy operation order, combining idempotent ingestion, partial correlation ids, ambiguity intersections and independently bounded duration aggregates across modules.",
    )


def lifecycle_event(
    identifier, kind, time, case="lot", activity="etch", resource="tool", run=None
):
    event = dict(
        id=identifier,
        kind=kind,
        time=time,
        case=case,
        activity=activity,
        resource=resource,
    )
    if run is not None:
        event["run"] = run
    return event


def lifecycle_cases():
    e = lifecycle_event

    def case(
        name, events, matched, alternatives, certain, unmatched, duration, public=False
    ):
        return Case(
            name,
            dict(events=events),
            dict(
                matched=matched,
                alternatives=alternatives,
                certain_pairs=certain,
                certain_unmatched=unmatched,
                duration_bounds=duration,
            ),
            public=public,
        )

    yield case(
        "single_lifecycle",
        [e("s", "start", 1), e("c", "complete", 4)],
        1,
        1,
        [["s", "c"]],
        [],
        [3, 3],
        True,
    )
    yield case(
        "overlapping_runs_are_ambiguous",
        [
            e("s1", "start", 0),
            e("s2", "start", 1),
            e("c1", "complete", 3),
            e("c2", "complete", 4),
        ],
        2,
        2,
        [],
        [],
        [6, 6],
        True,
    )
    yield case(
        "known_run_ids_force_cross_order",
        [
            e("s1", "start", 0, run="b"),
            e("s2", "start", 1, run="a"),
            e("c1", "complete", 3, run="a"),
            e("c2", "complete", 5, run="b"),
        ],
        2,
        1,
        [["s1", "c2"], ["s2", "c1"]],
        [],
        [7, 7],
        True,
    )
    yield case(
        "transport_retries_are_not_operations",
        [
            e("s", "start", 1),
            e("s", "start", 1),
            e("c", "complete", 4),
            e("c", "complete", 4),
        ],
        1,
        1,
        [["s", "c"]],
        [],
        [3, 3],
        True,
    )
    yield case("empty_log", [], 0, 1, [], [], [0, 0])
    yield case("orphan_completion", [e("c", "complete", 8)], 0, 1, [], ["c"], [0, 0])
    yield case(
        "negative_duration_forbidden",
        [e("s", "start", 5), e("c", "complete", 4)],
        0,
        1,
        [],
        ["c", "s"],
        [0, 0],
    )
    yield case(
        "zero_duration_allowed",
        [e("s", "start", 5), e("c", "complete", 5)],
        1,
        1,
        [["s", "c"]],
        [],
        [0, 0],
    )
    yield case(
        "case_boundary",
        [e("s", "start", 1, case="a"), e("c", "complete", 3, case="b")],
        0,
        1,
        [],
        ["c", "s"],
        [0, 0],
    )
    yield case(
        "resource_boundary",
        [e("s", "start", 1, resource="a"), e("c", "complete", 3, resource="b")],
        0,
        1,
        [],
        ["c", "s"],
        [0, 0],
    )
    yield case(
        "activity_boundary",
        [e("s", "start", 1, activity="clean"), e("c", "complete", 3)],
        0,
        1,
        [],
        ["c", "s"],
        [0, 0],
    )
    yield case(
        "unknown_correlation_requires_global_choice",
        [
            e("s1", "start", 0),
            e("s2", "start", 1, run="a"),
            e("c1", "complete", 3, run="a"),
            e("c2", "complete", 4, run="b"),
        ],
        2,
        1,
        [["s1", "c2"], ["s2", "c1"]],
        [],
        [6, 6],
    )
    yield case(
        "possible_unmatched_is_not_certain",
        [e("s1", "start", 1), e("s2", "start", 4), e("c", "complete", 7)],
        1,
        2,
        [],
        [],
        [3, 6],
    )
    yield case(
        "surplus_completions_duration_range",
        [e("s", "start", 1), e("c1", "complete", 4), e("c2", "complete", 8)],
        1,
        2,
        [],
        [],
        [3, 7],
    )
    yield case(
        "mixed_forced_ambiguous_and_orphan",
        [
            e("s1", "start", 0),
            e("s2", "start", 1),
            e("c1", "complete", 2),
            e("c2", "complete", 3),
            e("s3", "start", 4, resource="other"),
            e("c3", "complete", 6, resource="other"),
            e("orphan", "complete", 9, case="other"),
        ],
        3,
        2,
        [["s3", "c3"]],
        ["orphan"],
        [6, 6],
    )
    yield case(
        "simultaneous_distinct_ids",
        [
            e("s1", "start", 1),
            e("s2", "start", 1),
            e("c1", "complete", 2),
            e("c2", "complete", 2),
        ],
        2,
        2,
        [],
        [],
        [2, 2],
    )
    yield Case(
        "conflicting_retry_rejected",
        dict(events=[e("s", "start", 1), e("s", "start", 2)]),
        error="ValueError",
    )
    yield case(
        "out_of_order_transport",
        [
            e("c2", "complete", 8, run="b"),
            e("s1", "start", 1, run="a"),
            e("c1", "complete", 4, run="a"),
            e("s2", "start", 2, run="b"),
        ],
        2,
        1,
        [["s1", "c1"], ["s2", "c2"]],
        [],
        [9, 9],
    )
    unknown = e("s", "start", 1)
    unknown["run"] = None
    yield case(
        "explicit_null_correlation",
        [unknown, e("c", "complete", 4, run="a")],
        1,
        1,
        [["s", "c"]],
        [],
        [3, 3],
    )

    yield case(
        "retry_does_not_multiply_ambiguous_interpretations",
        [
            e("s1", "start", 1),
            e("s2", "start", 4),
            e("s1", "start", 1),
            e("c", "complete", 7),
        ],
        1,
        2,
        [],
        [],
        [3, 6],
    )


def quantity_task():
    files = {
        "fabops/revisions.py": code('''
            """Select logical event versions before reconstructing material causality."""
            def active_events(records):
                seen, latest = {}, {}
                for record in records:
                    key = (record["id"], record["revision"])
                    if key in seen and seen[key] != record:
                        raise ValueError("Conflicting event revision")
                    seen[key] = dict(record)
                    current = latest.get(record["id"])
                    if current is None or record["revision"] > current["revision"]:
                        latest[record["id"]] = dict(record)
                active = [event for event in latest.values() if not event.get("deleted", False)]
                return sorted(active, key=lambda event: (event["order"], event["id"]))
        '''),
        "fabops/ledger.py": code('''
            """Apply synchronized recipe quantities with per-event rollback."""
            def apply(inventory, capacities, recipe, batches):
                consumed = {place: count * batches for place, count in recipe["consume"].items()}
                produced = {place: count * batches for place, count in recipe["produce"].items()}
                if any(inventory[place] < count for place, count in consumed.items()):
                    return False, inventory, 0
                candidate = dict(inventory)
                for place, count in consumed.items():
                    candidate[place] -= count
                for place, count in produced.items():
                    candidate[place] += count
                if any(candidate[place] > capacities[place] for place in candidate):
                    return False, inventory, 0
                return True, candidate, recipe["scrap"] * batches
        '''),
        "fabops/domain.py": code("""
            from .revisions import active_events
            from .ledger import apply

            def run(request):
                inventory = {place: request["initial"].get(place, 0) for place in request["capacities"]}
                accepted, rejected, scrap = [], [], 0
                for event in active_events(request["events"]):
                    ok, inventory, loss = apply(inventory, request["capacities"],
                                                request["recipes"][event["recipe"]], event["batches"])
                    (accepted if ok else rejected).append(event["id"])
                    scrap += loss
                return dict(inventory=inventory, accepted=accepted, rejected=rejected, scrap=scrap)
        """),
    }
    faults = (
        Change(
            "fabops/revisions.py",
            'if current is None or record["revision"] > current["revision"]:',
            'if current is None or record["revision"] != current["revision"]:',
        ),
        Change(
            "fabops/revisions.py",
            'key=lambda event: (event["order"], event["id"])',
            'key=lambda event: (event["id"], event["order"])',
        ),
        Change(
            "fabops/ledger.py", "candidate = dict(inventory)", "candidate = inventory"
        ),
        Change("fabops/ledger.py", 'recipe["scrap"] * batches', 'recipe["scrap"]'),
    )
    mutants = {
        f"unfixed_{name}": (fault,)
        for name, fault in zip(
            ("latest_revision", "causal_order", "capacity_rollback", "scaled_scrap"),
            faults,
        )
    }
    mutants["partial_gate_availability"] = (
        Change(
            "fabops/ledger.py",
            "if any(inventory[place] < count for place, count in consumed.items()):",
            "if all(inventory[place] < count for place, count in consumed.items()):",
        ),
    )
    mutants["capacity_before_consumption"] = (
        Change(
            "fabops/ledger.py",
            "if any(candidate[place] > capacities[place] for place in candidate):",
            "if any(inventory[place] + produced.get(place, 0) > capacities[place] for place in candidate):",
        ),
    )
    return Task(
        "F27",
        "Corrected MES gate receipts corrupt downstream WIP and rejected-batch balances",
        "hard",
        "revisioned_synchronized_quantity_replay",
        code("""
            Reconstruct WIP from a revisioned MES recipe-receipt log; do not apply corrections as
            additive inventory deltas. capacities maps all stage names to positive integer limits.
            initial maps stages to nonnegative quantities within those limits; absent stages are
            zero. recipes maps ids to consume and produce mappings of positive integer quantities
            per batch, plus nonnegative integer scrap per batch. Every recipe consumes a nonempty
            input mapping and conserves material: sum(consume) = sum(produce) + scrap. A stage may
            appear in both sides. All recipe stages occur in capacities. A recipe can represent a
            synchronized multi-input gate, rework, material review, or partial-yield completion.

            Each logical event has a string id and positive integer revision. An active version
            additionally has integer order, recipe id, and positive integer batches. A tombstone
            has deleted=true and needs only id/revision. Duplicate (id,revision) rows must have
            identical complete content and count once; conflicting rows raise ValueError. For
            each logical id choose its numerically greatest revision, independent of arrival order;
            discard it if that latest version is a tombstone. Earlier tombstones can be superseded
            by higher active versions. Sort selected active events by (order,id), then replay ONCE
            from initial inventory. Corrections can change recipe, batches or order and therefore
            change whether every later gate is feasible. Never use earlier versions as supply.

            For each event multiply every recipe quantity and scrap by batches. Accept only if
            all consumed quantities are simultaneously available and every post-consumption,
            post-production inventory quantity respects capacity. Consume and produce atomically;
            rejection changes neither inventory nor accumulated scrap, even when only the output
            capacity fails after all inputs were available. Continue replay after rejection; rejected
            events are not retried if a later event adds material. Return inventory with every stage,
            accepted and rejected lists of active ids in replay order, and total accepted scrap.
            Tombstoned ids appear in neither list. Material in final inventory plus scrap must equal
            material in initial inventory. Do not mutate input data, even on rejected operations.
            There are at most twelve logical ids, four revisions each, six stages and six recipes.
        """),
        files,
        faults,
        mutants,
        tuple(quantity_cases()),
        ("production-log",),
        difficulty_reason="Corrections reorder and remove causal material receipts, so latest-version selection must precede full deterministic replay; multi-input gate availability, net capacity checks, rollback and scaled yield loss interact across separate modules.",
    )


def receipt(identifier, order=0, recipe="move", batches=1, revision=1, deleted=False):
    if deleted:
        return dict(id=identifier, revision=revision, deleted=True)
    return dict(
        id=identifier, revision=revision, order=order, recipe=recipe, batches=batches
    )


def quantity_request(initial, recipes, events, capacities=None):
    places = set(initial) | {
        place
        for recipe in recipes.values()
        for field in ("consume", "produce")
        for place in recipe[field]
    }
    return dict(
        initial=initial,
        recipes=recipes,
        events=events,
        capacities=capacities or {place: 20 for place in sorted(places)},
    )


def quantity_cases():
    def recipe(consume, produce, scrap=0):
        return dict(consume=consume, produce=produce, scrap=scrap)

    def case(name, request, inventory, accepted, rejected, scrap=0, public=False):
        return Case(
            name,
            request,
            dict(
                inventory=inventory, accepted=accepted, rejected=rejected, scrap=scrap
            ),
            public=public,
        )

    r = receipt
    pipeline = {
        "move": recipe({"raw": 1}, {"wip": 1}),
        "finish": recipe({"wip": 1}, {"done": 1}),
    }
    yield case(
        "receipt_order_drives_downstream_supply",
        quantity_request(
            {"raw": 2},
            pipeline,
            [r("a_finish", 2, "finish", 2), r("z_move", 1, "move", 2)],
        ),
        {"raw": 0, "wip": 0, "done": 2},
        ["z_move", "a_finish"],
        [],
        public=True,
    )
    joint = {"join": recipe({"a": 1, "b": 1}, {"done": 2})}
    yield case(
        "partial_gate_shortage_preserves_all_inputs",
        quantity_request({"a": 2, "b": 0}, joint, [r("join", 1, "join")]),
        {"a": 2, "b": 0, "done": 0},
        [],
        ["join"],
        public=True,
    )
    yield case(
        "late_correction_removes_downstream_supply",
        quantity_request(
            {"raw": 2},
            pipeline,
            [
                r("a_move", 1, "move", 1, 2),
                r("a_move", 1, "move", 2, 1),
                r("b_finish", 2, "finish", 2),
            ],
        ),
        {"raw": 1, "wip": 1, "done": 0},
        ["a_move"],
        ["b_finish"],
        public=True,
    )
    yield case(
        "capacity_rejection_rolls_back_consumption",
        quantity_request(
            {"raw": 2},
            pipeline,
            [r("a_block", 0, "move", 2), r("b_retry", 1, "move", 1)],
            {"raw": 2, "wip": 1, "done": 1},
        ),
        {"raw": 1, "wip": 1, "done": 0},
        ["b_retry"],
        ["a_block"],
        public=True,
    )
    yield case(
        "empty_receipts",
        quantity_request({"raw": 2}, pipeline, []),
        {"raw": 2, "wip": 0, "done": 0},
        [],
        [],
    )
    yield case(
        "single_receipt_control",
        quantity_request({"raw": 2}, pipeline, [r("move", 1, "move", 2)]),
        {"raw": 0, "wip": 2, "done": 0},
        ["move"],
        [],
    )
    yield case(
        "missing_all_inputs",
        quantity_request({}, joint, [r("join", 1, "join")]),
        {"a": 0, "b": 0, "done": 0},
        [],
        ["join"],
    )
    yield case(
        "complete_gate_consumes_both_branches",
        quantity_request({"a": 3, "b": 2}, joint, [r("join", 1, "join", 2)]),
        {"a": 1, "b": 0, "done": 4},
        ["join"],
        [],
    )
    yield case(
        "tombstone_invalidates_dependent_gate",
        quantity_request(
            {"raw": 2},
            pipeline,
            [
                r("a_move", 0, "move", 2),
                r("a_move", revision=2, deleted=True),
                r("b_finish", 1, "finish", 2),
            ],
        ),
        {"raw": 2, "wip": 0, "done": 0},
        [],
        ["b_finish"],
    )
    yield case(
        "older_tombstone_cannot_delete_latest",
        quantity_request(
            {"raw": 2},
            pipeline,
            [r("a_move", 0, "move", 2, 3), r("a_move", revision=2, deleted=True)],
        ),
        {"raw": 0, "wip": 2, "done": 0},
        ["a_move"],
        [],
    )
    yield case(
        "duplicate_revision_is_idempotent",
        quantity_request({"raw": 2}, pipeline, [r("move", 1), r("move", 1)]),
        {"raw": 1, "wip": 1, "done": 0},
        ["move"],
        [],
    )
    yield Case(
        "conflicting_revision_rejected",
        quantity_request({"raw": 2}, pipeline, [r("move", 1), r("move", 2)]),
        error="ValueError",
    )
    yield case(
        "correction_reorders_causal_chain",
        quantity_request(
            {"raw": 2},
            pipeline,
            [
                r("a_move", 0, "move", 2),
                r("b_finish", 1, "finish", 2),
                r("a_move", 2, "move", 2, 2),
            ],
        ),
        {"raw": 0, "wip": 2, "done": 0},
        ["a_move"],
        ["b_finish"],
    )
    yield case(
        "equal_order_uses_logical_id",
        quantity_request(
            {"raw": 1}, pipeline, [r("z_finish", 1, "finish"), r("a_move", 1)]
        ),
        {"raw": 0, "wip": 0, "done": 1},
        ["a_move", "z_finish"],
        [],
    )
    loss = {"yield": recipe({"raw": 3}, {"good": 2}, 1)}
    yield case(
        "batch_scaled_scrap",
        quantity_request({"raw": 9}, loss, [r("yield", 0, "yield", 3)]),
        {"raw": 0, "good": 6},
        ["yield"],
        [],
        3,
    )
    yield case(
        "rejected_batch_has_no_scrap",
        quantity_request(
            {"raw": 6}, loss, [r("bad", 0, "yield", 2)], {"raw": 6, "good": 3}
        ),
        {"raw": 6, "good": 0},
        [],
        ["bad"],
    )
    reuse = {"rework": recipe({"wip": 2}, {"wip": 1, "done": 1})}
    yield case(
        "net_capacity_for_self_consuming_gate",
        quantity_request(
            {"wip": 2}, reuse, [r("rework", 0, "rework")], {"wip": 2, "done": 1}
        ),
        {"wip": 1, "done": 1},
        ["rework"],
        [],
    )
    yield case(
        "rejected_event_is_not_retried",
        quantity_request(
            {"raw": 1}, pipeline, [r("a_finish", 0, "finish"), r("b_move", 1)]
        ),
        {"raw": 0, "wip": 1, "done": 0},
        ["b_move"],
        ["a_finish"],
    )
    recipes = {**pipeline, "scrap": recipe({"raw": 1}, {}, 1)}
    yield case(
        "recipe_correction_changes_yield_and_dependencies",
        quantity_request(
            {"raw": 2},
            recipes,
            [
                r("a_move", 0, "move", 2),
                r("a_move", 0, "scrap", 2, 2),
                r("b_finish", 1, "finish", 2),
            ],
        ),
        {"raw": 0, "wip": 0, "done": 0},
        ["a_move"],
        ["b_finish"],
        2,
    )
    gates = {
        "feed": recipe({"raw": 1}, {"a": 1}),
        "join": recipe({"a": 1, "b": 1}, {"done": 2}),
    }
    yield case(
        "partial_join_cannot_borrow_from_missing_branch",
        quantity_request(
            {"raw": 2},
            gates,
            [r("a_feed", 1, "feed"), r("b_join", 2, "join"), r("c_feed", 3, "feed")],
        ),
        {"raw": 0, "a": 2, "b": 0, "done": 0},
        ["a_feed", "c_feed"],
        ["b_join"],
    )
