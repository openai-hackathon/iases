"""Temporal dispatch and globally constrained production reconstruction."""

from dataclasses import replace
from .schema import Case, Change, Task, code
from .hard_process import lifecycle_task, lifecycle_event, quantity_task, receipt


def tasks():
    return [dispatch_task(), constrained_lifecycle(), bundled_receipts()]


def dispatch_task():
    files = {
        "fabops/resources.py": code('''
            """Half-open temporal reservations shared by alternative dispatch choices."""
            def feasible(request, rows):
                by_id = {lot["id"]: lot for lot in request["lots"]}
                assigned = {row[0]: row for row in rows}
                for identifier, tool, start, end in rows:
                    lot = by_id[identifier]
                    if any(start < right and left < end
                           for left, right in request.get("maintenance", {}).get(tool, [])):
                        return False
                    for predecessor in lot.get("after", []):
                        if predecessor in assigned and assigned[predecessor][3] > start:
                            return False
                for tick in range(request["horizon"]):
                    tools, reticles = set(), {}
                    for identifier, tool, start, end in rows:
                        lot = by_id[identifier]
                        if start <= tick < end:
                            if tool in tools:
                                return False
                            tools.add(tool)
                        if start <= tick < end + lot.get("cooldown", 0):
                            reticle = lot["reticle"]
                            reticles[reticle] = reticles.get(reticle, 0) + lot.get("units", 1)
                    if any(count > request["stock"].get(key, 0) for key, count in reticles.items()):
                        return False
                return True
        '''),
        "fabops/planner.py": code('''
            """Search complete temporal assignments, including deliberate idle periods."""
            from .resources import feasible

            def plan(request):
                lots = sorted(request["lots"], key=lambda lot: lot["id"])
                best, best_score = [], None
                def visit(index, rows):
                    nonlocal best, best_score
                    if best_score is not None:
                        count_bound = len(rows) + len(lots) - index
                        if count_bound < -best_score[0]:
                            return
                        if count_bound == -best_score[0]:
                            priority_bound = sum(lots_by_id[row[0]]["priority"] for row in rows) + sum(lot["priority"] for lot in lots[index:])
                            if priority_bound < -best_score[1]:
                                return
                            if priority_bound == -best_score[1]:
                                cost_bound = sum(lots_by_id[row[0]]["costs"][row[1]] for row in rows) + sum(min(lot["costs"].values(), default=0) for lot in lots[index:])
                                finish_bound = sum(row[3] for row in rows) + sum(lot["release"] + min(lot["durations"].values(), default=0) for lot in lots[index:])
                                if cost_bound > best_score[2] or (cost_bound == best_score[2] and finish_bound > best_score[3]):
                                    return
                    if index == len(lots):
                        selected = {row[0] for row in rows}
                        if any(not set(lot.get("after", [])) <= selected
                               for lot in lots if lot["id"] in selected):
                            return
                        priority = sum(lot["priority"] for lot in lots if lot["id"] in selected)
                        cost = sum(lots_by_id[row[0]]["costs"][row[1]] for row in rows)
                        finish = sum(row[3] for row in rows)
                        score = (-len(rows), -priority, cost, finish, tuple(map(tuple, rows)))
                        if best_score is None or score < best_score:
                            best, best_score = list(rows), score
                        return
                    lot = lots[index]
                    for tool in sorted(set(request["tools"]) & lot["costs"].keys()):
                        duration = lot["durations"][tool]
                        for start in range(lot["release"], min(lot["deadline"], request["horizon"]) - duration + 1):
                            candidate = rows + [[lot["id"], tool, start, start + duration]]
                            if feasible(request, candidate):
                                visit(index + 1, candidate)
                    visit(index + 1, rows)
                lots_by_id = {lot["id"]: lot for lot in lots}
                visit(0, [])
                return best
        '''),
        "fabops/store.py": code('''
            """Publish complete reservations against a full revision vector."""
            import json
            import sqlite3

            def commit(path, request, rows):
                db = sqlite3.connect(path)
                try:
                    db.execute("CREATE TABLE IF NOT EXISTS reservations (id TEXT PRIMARY KEY, body TEXT)")
                    db.commit()
                    db.execute("BEGIN IMMEDIATE")
                    if request["observed"] != request["current"]:
                        db.rollback()
                        return "stale", []
                    for row in rows:
                        db.execute("INSERT INTO reservations VALUES (?,?)", (row[0], json.dumps(row)))
                    if request.get("crash", False):
                        db.rollback()
                        status = "crashed"
                    else:
                        db.commit()
                        status = "committed"
                finally:
                    db.close()
                # Read through a fresh connection: only committed reservations are visible.
                with sqlite3.connect(path) as reader:
                    published = [json.loads(row[0]) for row in reader.execute("SELECT body FROM reservations ORDER BY id")]
                return status, published
        '''),
        "fabops/domain.py": code("""
            import tempfile
            from pathlib import Path
            from .planner import plan
            from .store import commit

            def run(request):
                rows = plan(request)
                with tempfile.TemporaryDirectory() as directory:
                    status, published = commit(Path(directory) / "dispatch.sqlite", request, rows)
                return dict(plan=rows, status=status, reservations=published)
        """),
    }
    faults = (
        Change(
            "fabops/planner.py",
            'for start in range(lot["release"], min(lot["deadline"], request["horizon"]) - duration + 1):',
            'for start in [lot["release"]] if lot["release"] + duration <= min(lot["deadline"], request["horizon"]) else []:',
        ),
        Change("fabops/resources.py", 'end + lot.get("cooldown", 0)', "end"),
        Change(
            "fabops/resources.py",
            "if predecessor in assigned and assigned[predecessor][3] > start:",
            "if False:",
        ),
        Change(
            "fabops/store.py",
            'if request["observed"] != request["current"]:',
            'if request["observed"].get("dispatch") != request["current"].get("dispatch"):',
        ),
        Change(
            "fabops/store.py",
            'if request.get("crash", False):\n            db.rollback()',
            'if request.get("crash", False):\n            db.commit()',
        ),
    )
    mutants = {
        name: (fault,)
        for name, fault in zip(
            [
                "release_only_search",
                "reticle_cooldown_ignored",
                "precedence_ignored",
                "partial_revision_vector",
                "crash_commits_reservations",
            ],
            faults,
        )
    }
    mutants["priority_before_throughput"] = (
        Change(
            "fabops/planner.py",
            "(-len(rows), -priority, cost, finish,",
            "(-priority, -len(rows), cost, finish,",
        ),
    )
    mutants["unit_reticle_demand"] = (
        Change("fabops/resources.py", 'lot.get("units", 1)', "1"),
    )
    mutants["maintenance_ignored"] = (
        Change(
            "fabops/resources.py", 'request.get("maintenance", {}).get(tool, [])', "[]"
        ),
    )
    mutants["missing_predecessor_allowed"] = (
        Change(
            "fabops/planner.py",
            'if any(not set(lot.get("after", [])) <= selected',
            "if any(False",
        ),
    )
    contract = code("""
        Plan a bounded nonpreemptive dispatch and atomically publish its reservations.
        There are at most six unique lots, three tools, and an integer horizon 1..8.
        Each lot has id, nonnegative priority, reticle, nonnegative costs by eligible
        tool, positive integer durations for those same tools, integer release>=0,
        deadline<=horizon, optional units>=1 (default 1), cooldown>=0 (default 0),
        and after (default []), listing existing predecessor lot ids in an acyclic graph.
        Release may exceed the latest feasible start. Stock maps reticles to nonnegative
        concurrent capacity; absent reticles have zero capacity. Tools is a unique list.
        Maintenance maps tools to arbitrary, possibly overlapping half-open integer intervals.

        A selected lot occupies one eligible tool during [start,end), end=start+duration.
        Start is an integer >=release, end<=deadline and horizon. It cannot overlap
        maintenance or another reservation on the same tool. It reserves units of its
        reticle during [start,end+cooldown); reticles are reusable after this interval,
        not consumed permanently. Concurrent demand cannot exceed stock. A selected
        lot requires ALL its predecessors selected and finished by its start. Cooldown
        delays reuse of the reticle, not precedence completion or tool reuse.

        Optimize globally: maximize selected count, then priority sum, then minimize
        total tool cost, then sum of completion times, then the lexicographic list of
        [lot id,tool id,start,end] rows sorted by lot id. Deliberate idle time and
        non-earliest placements may be necessary. Return the complete optimal plan.

        Commit checks exact equality of observed and current revision objects, including
        missing/extra keys. Mismatch takes precedence over crash and returns status=stale.
        Otherwise atomically insert all reservations into a real SQLite file. crash=true
        interrupts after insertion and before commit: status=crashed and no published
        reservations, including after reopen. Success returns status=committed. Empty
        plans follow the same commit rules. Return plan,status,reservations; the latter
        is the entire published plan on success and [] otherwise. Do not mutate inputs.
    """)
    return Task(
        "F19",
        "Temporal dispatch greedily fixes start times and publishes partial reservations",
        "hard",
        "temporal_reticle_dispatch_commit",
        contract,
        files,
        faults,
        mutants,
        tuple(dispatch_cases()),
        ("production-log", "nist-sms"),
        version="2.0",
        difficulty_reason="Replace static bipartite allocation and earliest-only placement with globally optimal temporal selection across reticle reuse, weighted demand, cooldown, maintenance and precedence, then preserve a complete reservation transaction across failure and reopen.",
    )


def dispatch_cases():
    def lot(
        name,
        *,
        duration=1,
        priority=1,
        reticle="r",
        release=0,
        deadline=4,
        costs=None,
        **kw,
    ):
        costs = costs or {"x": 0}
        return dict(
            id=name,
            priority=priority,
            reticle=reticle,
            costs=costs,
            durations={tool: duration for tool in costs},
            release=release,
            deadline=deadline,
            **kw,
        )

    def case(name, lots, plan, *, public=False, status="committed", **kw):
        request = dict(
            lots=lots,
            tools=["x", "y"],
            stock={"r": 1, "s": 1},
            horizon=4,
            observed={"dispatch": 1, "calendar": 1},
            current={"dispatch": 1, "calendar": 1},
        )
        request.update(kw)
        return Case(
            name,
            request,
            dict(
                plan=plan,
                status=status,
                reservations=plan if status == "committed" else [],
            ),
            public=public,
        )

    yield case("empty", [], [], public=True)
    yield case("one", [lot("a")], [["a", "x", 0, 1]], public=True)
    yield case(
        "reusable_reticle",
        [lot("b"), lot("a")],
        [["a", "x", 0, 1], ["b", "x", 1, 2]],
        public=True,
    )
    yield case(
        "cooldown",
        [lot("a", cooldown=2), lot("b")],
        [["a", "x", 1, 2], ["b", "x", 0, 1]],
        public=True,
    )
    yield case(
        "later_id_precedes",
        [lot("a", after=["z"]), lot("z")],
        [["a", "x", 1, 2], ["z", "x", 0, 1]],
        public=True,
    )
    yield case(
        "maintenance_split",
        [lot("a", duration=2)],
        [["a", "x", 2, 4]],
        maintenance={"x": [[1, 2]]},
    )
    yield case(
        "precedence_and_cooldown_across_tools",
        [lot("a", after=["z"], costs={"y": 0}), lot("z", cooldown=2)],
        [["a", "y", 3, 4], ["z", "x", 0, 1]],
    )
    yield case(
        "maintenance_union",
        [lot("a", duration=2)],
        [],
        maintenance={"x": [[0, 2], [1, 3]]},
    )
    yield case("release", [lot("a", release=2)], [["a", "x", 2, 3]])
    yield case("deadline", [lot("a", duration=2, deadline=1)], [])
    yield case("weighted_stock", [lot("a", units=2)], [], stock={"r": 1})
    yield case(
        "parallel_capacity",
        [lot("a", costs={"x": 0}), lot("b", costs={"y": 0})],
        [["a", "x", 0, 1], ["b", "y", 0, 1]],
        stock={"r": 2},
    )
    yield case(
        "reticle_blocks_parallel",
        [lot("a", costs={"x": 0}), lot("b", costs={"y": 0})],
        [["a", "x", 0, 1], ["b", "y", 1, 2]],
    )
    yield case(
        "cost_before_finish",
        [lot("a", costs={"x": 4, "y": 0})],
        [["a", "y", 2, 3]],
        maintenance={"y": [[0, 2]]},
    )
    yield case(
        "throughput_before_priority",
        [lot("a", duration=4, priority=99), lot("b", duration=2), lot("c", duration=2)],
        [["b", "x", 0, 2], ["c", "x", 2, 4]],
    )
    yield case(
        "unavailable_predecessor",
        [lot("a", after=["z"]), lot("z", reticle="missing")],
        [],
    )
    yield case(
        "stale_calendar",
        [lot("a")],
        [["a", "x", 0, 1]],
        current={"dispatch": 1, "calendar": 2},
        status="stale",
    )
    yield case(
        "extra_revision_key",
        [lot("a")],
        [["a", "x", 0, 1]],
        current={"dispatch": 1, "calendar": 1, "stock": 0},
        status="stale",
    )
    yield case(
        "crash_after_insert",
        [lot("a"), lot("b")],
        [["a", "x", 0, 1], ["b", "x", 1, 2]],
        crash=True,
        status="crashed",
    )
    yield case("stale_before_crash", [], [], current={}, crash=True, status="stale")
    yield case(
        "short_deadline_forces_idle",
        [lot("a", duration=2), lot("b", deadline=1)],
        [["a", "x", 1, 3], ["b", "x", 0, 1]],
    )
    yield case(
        "full_six_lot_search",
        [lot(name, deadline=8, costs={"x": 0, "y": 0, "z": 0}) for name in "abcdef"],
        [
            ["a", "x", 0, 1],
            ["b", "x", 1, 2],
            ["c", "y", 0, 1],
            ["d", "y", 1, 2],
            ["e", "z", 0, 1],
            ["f", "z", 1, 2],
        ],
        tools=["x", "y", "z"],
        stock={"r": 6},
        horizon=8,
    )


def constrained_lifecycle():
    original = lifecycle_task()
    files = dict(original.files)
    files["fabops/constraints.py"] = code('''
        """Global physical and routing feasibility of an event interpretation."""
        def admissible(events, pairs, request):
            by_id = {event["id"]: event for event in events}
            intervals = [(by_id[start], by_id[end]) for start, end in pairs]
            for start, end in intervals:
                low, high = request.get("duration_limits", {}).get(start["activity"], [0, float("inf")])
                if not low <= end["time"] - start["time"] <= high:
                    return False
            for resource, capacity in request.get("capacities", {}).items():
                points = sorted({event["time"] for pair in intervals for event in pair})
                for tick in points:
                    usage = sum(start.get("units", 1) for start, end in intervals
                                if start["resource"] == resource and start["time"] <= tick < end["time"])
                    if usage > capacity:
                        return False
            for earlier, later in request.get("route", []):
                for a, b in intervals:
                    for c, d in intervals:
                        if a["case"] == c["case"] and a["activity"] == earlier and c["activity"] == later:
                            if b["time"] > c["time"]:
                                return False
            # Pairs of event IDs express coupled audit evidence, not transport duplicates.
            chosen = {identifier for pair in pairs for identifier in pair}
            for left, right in request.get("coupled", []):
                if (left in chosen) != (right in chosen):
                    return False
            return True
    ''')
    files["fabops/correlation.py"] = files["fabops/correlation.py"].replace(
        "def matchings(events):",
        "def matchings(events, request):\n    from .constraints import admissible",
    )
    files["fabops/correlation.py"] = files["fabops/correlation.py"].replace(
        "if index == len(starts):",
        "if index == len(starts):\n            if not admissible(events, pairs, request):\n                return",
    )
    files["fabops/domain.py"] = files["fabops/domain.py"].replace(
        "matchings(events)", "matchings(events, request)"
    )
    global_fault = Change(
        "fabops/constraints.py",
        files["fabops/constraints.py"],
        code('''
        """Legacy per-operation validation misses competing lifecycle explanations."""
        def admissible(events, pairs, request):
            by_id = {event["id"]: event for event in events}
            for start_id, end_id in pairs:
                start, end = by_id[start_id], by_id[end_id]
                low, high = request.get("duration_limits", {}).get(start["activity"], [0, float("inf")])
                if not low <= end["time"] - start["time"] <= high:
                    return False
            return True
    '''),
    )
    faults = (*original.faults, global_fault)
    mutants = dict(original.mutants)
    mutants.update(
        {
            "local_checks_only": (global_fault,),
            "capacity_counts_pairs": (
                Change("fabops/constraints.py", 'start.get("units", 1)', "1"),
            ),
            "route_ignores_case": (
                Change("fabops/constraints.py", 'a["case"] == c["case"] and ', ""),
            ),
            "inclusive_resource_end": (
                Change(
                    "fabops/constraints.py", 'tick < end["time"]', 'tick <= end["time"]'
                ),
            ),
            "coupled_audit_ignored": (
                Change("fabops/constraints.py", 'request.get("coupled", [])', "[]"),
            ),
            "prune_incomplete_coupling": (
                Change(
                    "fabops/correlation.py",
                    "start = starts[index]",
                    "if not admissible(events, pairs, request):\n            return\n        start = starts[index]",
                ),
            ),
        }
    )
    contract = original.contract + code("""

        Additional global evidence changes WHICH interpretations are eligible before
        maximizing cardinality. capacities optionally maps resources to nonnegative
        integer capacities (unlisted resources are unconstrained). Each start may have
        integer units>=1, default 1. A selected lifecycle reserves its start's units
        on [start.time,complete.time); zero-duration pairs use no capacity. Unmatched
        events reserve nothing. All simultaneous selected lifecycles share this capacity.
        duration_limits optionally maps an activity to inclusive [minimum,maximum]
        nonnegative integer duration bounds. Unlisted activities have no extra bound.

        route is a list of [earlier activity,later activity] edges in an acyclic graph.
        For every selected earlier/later pair of lifecycles in the SAME case, the earlier
        completion must be <= the later start, even on different resources. An absent
        activity is allowed. coupled is a list of pairs of existing event ids: either
        both events must be paired somewhere in an interpretation, or both unmatched.
        These constraints may require choosing a SMALLER matching than unconstrained
        bipartite maximum matching. Optimize only among globally feasible interpretations;
        filtering an already maximal set or pruning unfinished coupled evidence is wrong.
        All omitted new fields default to {} or []. The empty interpretation is feasible.
        Return the same five result fields, counting distinct pair sets, not schedules.
    """)
    return replace(
        original,
        title="Lifecycle certainty ignores globally competing resources and coupled evidence",
        family="capacity_route_constrained_lifecycle_interpretations",
        files=files,
        faults=faults,
        mutants=mutants,
        contract=contract,
        version="2.0",
        cases=(*original.cases, *lifecycle_constraint_cases()),
        difficulty_reason="Reconstruct all maximum interpretations under nonlocal weighted interval capacity, cross-resource route order, duration limits and coupled event evidence; local matching or filtering only unconstrained maxima loses valid lower-cardinality solutions and certainty bounds.",
    )


def lifecycle_constraint_cases():
    def pair(name, start, end, *, activity="work", resource="m", case="c", units=1):
        return [
            dict(
                lifecycle_event(
                    name + "s",
                    "start",
                    start,
                    activity=activity,
                    resource=resource,
                    case=case,
                    run=name,
                ),
                units=units,
            ),
            lifecycle_event(
                name + "e",
                "complete",
                end,
                activity=activity,
                resource=resource,
                case=case,
                run=name,
            ),
        ]

    def result(matched, alternatives, pairs=(), unmatched=(), bounds=(0, 0)):
        return dict(
            matched=matched,
            alternatives=alternatives,
            certain_pairs=[list(p) for p in sorted(pairs)],
            certain_unmatched=sorted(unmatched),
            duration_bounds=list(bounds),
        )

    a, b = pair("a", 0, 3), pair("b", 1, 2)
    yield Case(
        "capacity_reduces_maximum",
        dict(events=a + b, capacities={"m": 1}),
        result(1, 2, bounds=(1, 3)),
        public=True,
    )
    yield Case(
        "coupled_excludes_all",
        dict(events=a + b, capacities={"m": 1}, coupled=[["as", "bs"]]),
        result(0, 1, unmatched=["as", "ae", "bs", "be"]),
        public=True,
    )
    yield Case(
        "coupled_requires_complete_search",
        dict(events=a + b, capacities={"m": 2}, coupled=[["as", "bs"]]),
        result(2, 1, [("as", "ae"), ("bs", "be")], bounds=(4, 4)),
        public=True,
    )
    yield Case(
        "weighted_capacity",
        dict(events=pair("a", 0, 3, units=2) + b, capacities={"m": 1}),
        result(1, 1, [("bs", "be")], ["as", "ae"], (1, 1)),
    )
    yield Case(
        "coupling_at_weighted_capacity",
        dict(
            events=pair("a", 0, 3, units=2) + b,
            capacities={"m": 3},
            coupled=[["as", "bs"]],
        ),
        result(2, 1, [("as", "ae"), ("bs", "be")], bounds=(4, 4)),
    )
    yield Case(
        "touching_capacity",
        dict(events=pair("a", 0, 1) + pair("b", 1, 2), capacities={"m": 1}),
        result(2, 1, [("as", "ae"), ("bs", "be")], bounds=(2, 2)),
    )
    yield Case(
        "zero_duration_capacity_zero",
        dict(events=pair("a", 1, 1), capacities={"m": 0}),
        result(1, 1, [("as", "ae")]),
    )
    route_events = pair("a", 0, 3, activity="etch") + pair(
        "b", 2, 4, activity="inspect", resource="q"
    )
    yield Case(
        "cross_resource_route",
        dict(events=route_events, route=[["etch", "inspect"]]),
        result(1, 2, bounds=(2, 3)),
    )
    yield Case(
        "route_other_case",
        dict(
            events=pair("a", 0, 3, activity="etch")
            + pair("b", 2, 4, activity="inspect", case="other"),
            route=[["etch", "inspect"]],
        ),
        result(2, 1, [("as", "ae"), ("bs", "be")], bounds=(5, 5)),
    )
    yield Case(
        "route_and_coupling",
        dict(events=route_events, route=[["etch", "inspect"]], coupled=[["ae", "be"]]),
        result(0, 1, unmatched=["as", "ae", "bs", "be"]),
    )
    yield Case(
        "duration_before_global_max",
        dict(events=a + b, duration_limits={"work": [2, 4]}),
        result(1, 1, [("as", "ae")], ["bs", "be"], (3, 3)),
    )
    yield Case(
        "resource_capacity_two",
        dict(events=a + b + pair("c", 2, 4), capacities={"m": 2}),
        result(3, 1, [("as", "ae"), ("bs", "be"), ("cs", "ce")], bounds=(6, 6)),
    )
    yield Case(
        "coupled_unpairable_evidence",
        dict(
            events=a + [lifecycle_event("orphan", "complete", -1)],
            coupled=[["as", "orphan"]],
        ),
        result(0, 1, unmatched=["as", "ae", "orphan"]),
    )


def bundled_receipts():
    original = quantity_task()
    files = dict(original.files)
    files["fabops/revisions.py"] = (
        files["fabops/revisions.py"]
        .replace("def active_events(records):", "def active_events(records, as_of):")
        .replace(
            'current = latest.get(record["id"])',
            'if record.get("known_at", 0) > as_of:\n            continue\n        current = latest.get(record["id"])',
        )
    )
    files["fabops/bundles.py"] = code('''
        """Find a complete feasible internal ordering before committing a material bundle."""
        from .ledger import apply

        def groups(events):
            grouped = {}
            for event in events:
                key = ("bundle", event["bundle"]) if "bundle" in event else ("event", event["id"])
                grouped.setdefault(key, []).append(event)
            return sorted(grouped.values(), key=lambda group: min((e["order"], e["id"]) for e in group))

        def settle(events, inventory, capacities, recipes, accepted):
            events = sorted(events, key=lambda e: e["id"])
            def search(remaining, state, done, loss, witness):
                if not remaining:
                    return state, loss, witness
                for index, event in enumerate(remaining):
                    if not set(event.get("after", [])) <= done:
                        continue
                    ok, candidate, scrap = apply(state, capacities, recipes[event["recipe"]], event["batches"])
                    if not ok:
                        continue
                    result = search(remaining[:index] + remaining[index+1:], candidate,
                                    done | {event["id"]}, loss + scrap, witness + [event["id"]])
                    if result is not None:
                        return result
                return None
            return search(events, dict(inventory), set(accepted), 0, [])
    ''')
    files["fabops/domain.py"] = code("""
        from .revisions import active_events
        from .bundles import groups, settle

        def run(request):
            inventory = {place: request["initial"].get(place, 0) for place in request["capacities"]}
            accepted, rejected, scrap = [], [], 0
            events = active_events(request["events"], request.get("as_of", float("inf")))
            for bundle in groups(events):
                result = settle(bundle, inventory, request["capacities"], request["recipes"], accepted)
                if result is None:
                    rejected.extend(sorted(event["id"] for event in bundle))
                else:
                    inventory, loss, witness = result
                    scrap += loss
                    accepted.extend(witness)
            return dict(inventory=inventory, accepted=accepted, rejected=rejected, scrap=scrap)
    """)
    greedy = Change(
        "fabops/bundles.py",
        files["fabops/bundles.py"].split("def settle", 1)[1],
        code("""
        (events, inventory, capacities, recipes, accepted):
            state, loss, witness = dict(inventory), 0, []
            for event in sorted(events, key=lambda e: e["id"]):
                ok, state, scrap = apply(state, capacities, recipes[event["recipe"]], event["batches"])
                if not ok:
                    return None
                loss += scrap
                witness.append(event["id"])
            return state, loss, witness
    """),
    )
    visibility = Change(
        "fabops/revisions.py", 'if record.get("known_at", 0) > as_of:', "if False:"
    )
    unit_order = Change(
        "fabops/bundles.py",
        'min((e["order"], e["id"]) for e in group)',
        'min((e["id"], e["order"]) for e in group)',
    )
    faults = (original.faults[0], unit_order, *original.faults[2:], greedy, visibility)
    mutants = dict(original.mutants)
    mutants["unfixed_causal_order"] = (unit_order,)
    mutants.update(
        {
            "greedy_bundle": (greedy,),
            "future_knowledge": (visibility,),
            "bundle_dependencies_ignored": (
                Change(
                    "fabops/bundles.py",
                    'if not set(event.get("after", [])) <= done:',
                    "if False:",
                ),
            ),
            "partial_bundle_publication": (
                Change(
                    "fabops/bundles.py",
                    "if not remaining:",
                    "if not remaining or witness:",
                ),
            ),
            "reject_without_backtracking": (
                Change(
                    "fabops/bundles.py",
                    "if not ok:\n                continue",
                    "if not ok:\n                return None",
                ),
            ),
            "bundle_partition_lost": (
                Change(
                    "fabops/bundles.py",
                    'key = ("bundle", event["bundle"]) if "bundle" in event else ("event", event["id"])',
                    'key = ("event", event["id"])',
                ),
            ),
        }
    )
    contract = original.contract + code("""

        Version 2 adds historical knowledge and atomic material bundles. known_at is an
        optional nonnegative integer on each revision, default 0. as_of is an optional
        nonnegative query time; omission sees all records. Validate duplicate revision
        conflicts across ALL supplied records first, including invisible records. Then
        exclude records with known_at>as_of BEFORE choosing the greatest visible revision.
        A future correction or deletion cannot erase the historical version known then.

        Active records may carry bundle (string) and after (list of logical event ids).
        All selected active events with the same explicit bundle form one atomic unit;
        unbundled events are independent singleton units, even if an id equals a bundle
        name. Form groups AFTER visible revision selection. Process units by the minimum
        (order,id) among their members. An earlier version supplies no bundle membership.

        For each unit find a complete execution permutation satisfying all per-step
        availability/capacity rules and dependencies: every after id must already have
        been accepted in an earlier unit or earlier in this permutation. Missing, deleted,
        rejected and future-unit dependencies are unsatisfied. Cyclic after constraints
        make the unit infeasible. Intermediate inventory must respect limits at EVERY
        step; a feasible aggregate net movement does not suffice. Try alternative orderings
        when a currently feasible action would strand the remaining bundle. Choose the
        lexicographically smallest complete feasible sequence of event ids.

        Publish the ENTIRE unit's inventory, scrap and acceptance list only if a complete
        ordering exists. Otherwise reject all its ids in sorted order, changing neither
        inventory nor scrap. Never retry a rejected unit later. A tombstone removes only
        its event, not the remaining members. Return the original four fields; accepted
        concatenates each unit's chosen witness, rejected concatenates rejected sorted
        member lists. At most six members per unit. Earlier per-event replay rules apply
        to singleton units. These bundle rules supersede the original global event order.
    """)
    return replace(
        original,
        title="Historical MES bundles publish infeasible prefixes after revision replay",
        family="historical_atomic_material_bundle_search",
        version="2.0",
        contract=contract,
        files=files,
        faults=faults,
        mutants=mutants,
        cases=(*original.cases, *bundle_cases()),
        difficulty_reason="Couple knowledge-time revision selection with regrouping, dependency-aware permutation search, per-step material feasibility and all-or-nothing bundle publication; globally net-feasible movements and a greedy feasible prefix may both be invalid.",
    )


def bundle_cases():
    recipes = {
        "forward": dict(consume={"raw": 1}, produce={"mid": 1}, scrap=0),
        "finish": dict(consume={"mid": 1}, produce={"done": 1}, scrap=0),
        "back": dict(consume={"mid": 1}, produce={"raw": 1}, scrap=0),
        "loss": dict(consume={"raw": 1}, produce={}, scrap=1),
    }

    def event(name, recipe="forward", **kw):
        return dict(receipt(name, recipe=recipe), **kw)

    def case(
        name, events, accepted, rejected, inventory, *, scrap=0, public=False, **kw
    ):
        request = dict(
            events=events,
            initial={"raw": 1},
            capacities={"raw": 2, "mid": 2, "done": 2},
            recipes=recipes,
        )
        request.update(kw)
        return Case(
            name,
            request,
            dict(
                inventory=dict(zip(["raw", "mid", "done"], inventory)),
                accepted=accepted,
                rejected=rejected,
                scrap=scrap,
            ),
            public=public,
        )

    yield case(
        "bundle_reorders_supply",
        [event("a", "finish", bundle="u"), event("z", bundle="u")],
        ["z", "a"],
        [],
        [0, 0, 1],
        public=True,
    )
    yield case(
        "bundle_rejects_partial_supply",
        [event("a", bundle="u"), event("b", bundle="u")],
        [],
        ["a", "b"],
        [1, 0, 0],
        public=True,
    )
    yield case(
        "bundle_after_changes_witness",
        [event("a", "loss", bundle="u", after=["z"]), event("z", bundle="u")],
        ["z", "a"],
        [],
        [0, 1, 0],
        scrap=1,
        initial={"raw": 2},
        public=True,
    )
    yield case(
        "historical_future_delete",
        [event("a"), dict(id="a", revision=2, known_at=5, deleted=True)],
        ["a"],
        [],
        [0, 1, 0],
        as_of=4,
    )
    yield case(
        "historical_delete_boundary",
        [event("a"), dict(id="a", revision=2, known_at=5, deleted=True)],
        [],
        [],
        [1, 0, 0],
        as_of=5,
    )
    yield case("missing_after", [event("a", after=["missing"])], [], ["a"], [1, 0, 0])
    yield case(
        "dependency_cycle",
        [
            event("a", bundle="u", after=["b"]),
            event("b", "back", bundle="u", after=["a"]),
        ],
        [],
        ["a", "b"],
        [1, 0, 0],
    )
    yield case(
        "rollback_scrap",
        [event("a", "loss", bundle="u"), event("b", bundle="u")],
        [],
        ["a", "b"],
        [1, 0, 0],
    )
    yield case(
        "no_retry_after_supply",
        [event("a", "finish"), event("b")],
        ["b"],
        ["a"],
        [0, 1, 0],
    )
    yield case(
        "search_backtracks_feasible_prefix",
        [
            event("a", "finish", bundle="u"),
            event("b", "back", bundle="u"),
            event("c", bundle="u"),
        ],
        ["b", "c", "a"],
        [],
        [0, 0, 1],
        initial={"mid": 1},
    )
    yield case(
        "aggregate_feasible_without_first_step",
        [event("a", bundle="u"), event("b", "back", bundle="u")],
        [],
        ["a", "b"],
        [0, 0, 1],
        initial={"done": 1},
    )
    yield case(
        "accepted_external_dependency",
        [event("a"), event("b", "finish", after=["a"])],
        ["a", "b"],
        [],
        [0, 0, 1],
    )
    yield case(
        "future_bundle_dependency",
        [event("a", after=["z"]), event("z", "loss")],
        ["z"],
        ["a"],
        [0, 0, 0],
        scrap=1,
    )
    yield case(
        "deleted_member_leaves_rest",
        [
            event("a", "finish", bundle="u"),
            event("z", bundle="u"),
            dict(id="a", revision=2, deleted=True),
        ],
        ["z"],
        [],
        [0, 1, 0],
    )
    yield case(
        "unit_identity_namespaces",
        [event("a", bundle="b"), event("b")],
        ["a"],
        ["b"],
        [0, 1, 0],
    )
    conflict = [event("a", known_at=9), dict(event("a", known_at=9), batches=2)]
    yield Case(
        "invisible_duplicate_conflict",
        dict(
            events=conflict,
            initial={"raw": 1},
            capacities={"raw": 2, "mid": 2, "done": 2},
            recipes=recipes,
            as_of=0,
        ),
        error="ValueError",
    )
