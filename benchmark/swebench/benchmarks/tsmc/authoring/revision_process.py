"""Revised development tasks with coupled calendar and conformance repairs.

Fixtures and faults are authored, not extracted incidents or dataset records.
"""

from .schema import Case, Change, Task, code


def tasks():
    yield calendar_task()
    yield alignment_task()


CALENDAR = code('''
    """Translate operating windows and reservations to available capacity."""
    def capacity_profile(request):
        start, end = request["horizon"]
        intervals = request["open"] + request["maintenance"]
        boundaries = {start, end}
        for left, right in intervals:
            boundaries.update((max(start, min(end, left)), max(start, min(end, right))))
        for job in request["jobs"]:
            boundaries.update((max(start, min(end, job["start"])),
                               max(start, min(end, job["end"]))))
        ordered = sorted(boundaries)
        result = []
        for left, right in zip(ordered, ordered[1:]):
            opened = any(a <= left < b for a, b in request["open"])
            closed = any(a <= left < b for a, b in request["maintenance"])
            used = sum(job["units"] for job in request["jobs"]
                       if job["start"] <= left < job["end"])
            free = max(0, request["capacity"] - used) if opened and not closed else 0
            if result and result[-1][2] == free:
                result[-1][1] = right
            else:
                result.append([left, right, free])
        return result
''')

BAD_CALENDAR = code('''
    """Translate operating windows and reservations to available capacity."""
    def capacity_profile(request):
        start, end = request["horizon"]
        result = []
        for a, b in sorted(request["open"]):
            left, right = max(start, a), min(end, b)
            if left >= right:
                continue
            unavailable = sum(max(0, min(right, y) - max(left, x))
                              for x, y in request["maintenance"])
            used = sum(job["units"] for job in request["jobs"]
                       if job["start"] < right and job["end"] > left)
            effective_end = max(left, right - unavailable)
            result.append([left, effective_end, max(0, request["capacity"] - used)])
        return result
''')

BOOKING = code('''
    """Find a continuous booking inside a capacity profile."""
    def earliest(profile, ready, duration, units):
        run_start = None
        run_end = None
        for left, right, free in profile:
            left = max(left, ready)
            if left >= right:
                continue
            if free < units:
                run_start = run_end = None
                continue
            if run_end != left:
                run_start = left
            run_end = right
            if run_end - run_start >= duration:
                return [run_start, run_start + duration]
        return None
''')

BAD_BOOKING = code('''
    """Find a continuous booking inside a capacity profile."""
    def earliest(profile, ready, duration, units):
        remaining = duration
        started = None
        for left, right, free in profile:
            left = max(left, ready)
            if free < units or right <= left:
                continue
            if started is None:
                started = left
            take = min(remaining, right - left)
            remaining -= take
            if remaining == 0:
                return [started, left + take]
        return None
''')


def calendar_task():
    files = {
        "fabops/calendar.py": CALENDAR,
        "fabops/booking.py": BOOKING,
        "fabops/domain.py": code("""
            from .calendar import capacity_profile
            from .booking import earliest

            def run(request):
                profile = capacity_profile(request)
                query = request["query"]
                booking = earliest(profile, query["ready"], query["duration"], query["units"])
                unit_minutes = sum((right - left) * free for left, right, free in profile)
                return dict(profile=profile, available_unit_minutes=unit_minutes, booking=booking)
        """),
    }
    faults = (
        Change("fabops/calendar.py", CALENDAR, BAD_CALENDAR),
        Change("fabops/booking.py", BOOKING, BAD_BOOKING),
    )
    mutants = {
        "window_level_capacity": (faults[0],),
        "preemptive_booking": (faults[1],),
        "count_jobs_instead_of_units": (
            Change("fabops/calendar.py", 'sum(job["units"] for job', "sum(1 for job"),
        ),
        "closed_right_endpoint": (
            Change(
                "fabops/calendar.py",
                'job["start"] <= left < job["end"]',
                'job["start"] <= left <= job["end"]',
            ),
        ),
        "one_open_window": (
            Change(
                "fabops/calendar.py",
                'for a, b in request["open"]',
                'for a, b in request["open"][:1]',
            ),
        ),
        "one_maintenance_window": (
            Change(
                "fabops/calendar.py",
                'for a, b in request["maintenance"]',
                'for a, b in request["maintenance"][:1]',
            ),
        ),
        "reset_at_capacity_change": (
            Change(
                "fabops/booking.py",
                "if run_end != left:",
                "if run_end != left or run_start is not None:",
            ),
        ),
        "ignore_ready": (
            Change("fabops/booking.py", "left = max(left, ready)", "left = left"),
        ),
    }
    return Task(
        "F11",
        "Capacity planning invents continuous availability across downtime",
        "medium",
        "capacity_calendar_continuous_booking",
        code("""
            Plan one nonpreemptive operation on a workstation. Times are integer minutes in a
            shared absolute clock, not local dates. horizon=[start,end] has start<end. All
            intervals are half-open [start,end); all supplied intervals have positive length.
            open lists operating windows. Their UNION defines when the workstation operates;
            overlapping or duplicate windows never add capacity. maintenance lists complete
            closures whose UNION overrides operating windows. Windows may extend outside horizon.
            capacity is a positive integer. jobs lists committed reservations with start, end
            and positive integer units. Each job independently occupies its units; intersecting
            reservations add, including identical records. Overbooked intervals have zero free
            capacity. Jobs outside operating hours still exist but cannot make a closed interval
            usable. Input order has no meaning.

            Return profile as sorted maximal [start,end,free_units] segments covering the entire
            horizon, including closed periods. Adjacent segments with equal free_units must be
            combined. available_unit_minutes is the integral of free_units over the horizon.
            query has ready (integer), duration (positive integer minutes), and units (positive
            integer). booking is the earliest [start,start+duration] wholly within the horizon
            at or after ready with free_units >= units at EVERY instant. An operation can span
            adjacent segments with different adequate capacities but cannot pause across a gap.
            Return booking=null if no continuous feasible slot exists. Report the pre-booking
            profile and integral; this query does not reserve or alter capacity.

            At most 100 intervals and jobs combined, capacity and job/query units <=20. The
            horizon may span 10^9 minutes: running time must depend on the number of intervals,
            not on every minute in the horizon. Do not mutate any input lists or dictionaries.
        """),
        files,
        faults,
        mutants,
        tuple(calendar_cases()),
        ("production-log", "nist-sms"),
        extra_hidden_tests=CALENDAR_ORACLE,
        version="2.0",
        difficulty_reason="Replaces the earlier one-dimensional maintenance-union repair with coupled operating-calendar normalization, weighted occupancy segmentation, maximal-profile reporting and nonpreemptive booking across changing capacity. Whole flawed calendar and booking algorithms must be reconciled; changing one overlap operator is insufficient.",
    )


def calendar_cases():
    def c(
        name,
        profile,
        booking,
        *,
        horizon=(0, 20),
        opens=None,
        maintenance=(),
        jobs=(),
        capacity=2,
        ready=0,
        duration=4,
        units=1,
        public=False,
    ):
        request = {
            "horizon": list(horizon),
            "open": [list(v) for v in (opens if opens is not None else [horizon])],
            "maintenance": [list(v) for v in maintenance],
            "jobs": [{"start": a, "end": b, "units": u} for a, b, u in jobs],
            "capacity": capacity,
            "query": {"ready": ready, "duration": duration, "units": units},
        }
        # The profile is a literal independent expectation; the integral is elementary arithmetic.
        expected = {
            "profile": profile,
            "available_unit_minutes": sum((b - a) * u for a, b, u in profile),
            "booking": booking,
        }
        return Case(name, request, expected, public=public)

    yield c("control", [[0, 20, 2]], [0, 4], public=True)
    yield c(
        "closures_cannot_be_compressed",
        [[0, 3, 2], [3, 8, 0], [8, 20, 2]],
        [8, 14],
        maintenance=[(3, 8)],
        duration=6,
        public=True,
    )
    yield c(
        "weighted_peak",
        [[0, 4, 3], [4, 8, 1], [8, 12, 0], [12, 16, 1], [16, 20, 3]],
        [0, 4],
        capacity=3,
        jobs=[(4, 12, 2), (8, 16, 2)],
        units=3,
        public=True,
    )
    yield c(
        "capacity_change_is_continuous",
        [[0, 3, 2], [3, 9, 1], [9, 20, 2]],
        [0, 8],
        jobs=[(3, 9, 1)],
        duration=8,
        public=True,
    )
    yield c(
        "overlapping_open_union",
        [[0, 15, 2], [15, 20, 0]],
        [0, 14],
        opens=[(5, 15), (0, 10), (0, 10)],
        duration=14,
    )
    yield c(
        "nested_closure_union",
        [[0, 2, 2], [2, 12, 0], [12, 20, 2]],
        [12, 16],
        maintenance=[(2, 8), (4, 12), (5, 6)],
    )
    yield c(
        "disjoint_closures",
        [[0, 2, 2], [2, 4, 0], [4, 7, 2], [7, 10, 0], [10, 20, 2]],
        [10, 14],
        maintenance=[(2, 4), (7, 10)],
    )
    yield c("ready_inside_segment", [[0, 20, 2]], [7, 11], ready=7)
    yield c(
        "ready_in_downtime",
        [[0, 4, 2], [4, 10, 0], [10, 20, 2]],
        [10, 14],
        maintenance=[(4, 10)],
        ready=6,
    )
    yield c(
        "touching_reservations",
        [[0, 12, 1], [12, 20, 2]],
        [12, 16],
        jobs=[(0, 6, 1), (6, 12, 1)],
        units=2,
    )
    yield c(
        "duplicate_jobs_are_distinct",
        [[0, 5, 2], [5, 10, 0], [10, 20, 2]],
        [10, 18],
        jobs=[(5, 10, 1), (5, 10, 1)],
        duration=8,
    )
    yield c("overbook_clamped", [[0, 10, 0], [10, 20, 2]], [10, 14], jobs=[(-1, 10, 3)])
    yield c(
        "outside_horizon",
        [[0, 5, 2], [5, 15, 0], [15, 20, 2]],
        [0, 4],
        opens=[(-10, 5), (15, 40)],
        maintenance=[(-20, -10), (30, 40)],
        jobs=[(-9, -5, 3), (30, 40, 4)],
    )
    yield c("no_operating_hours", [[0, 20, 0]], None, opens=[])
    yield c("full_closure", [[0, 20, 0]], None, maintenance=[(-1, 21)])
    yield c("insufficient_total_capacity", [[0, 20, 2]], None, units=3)
    yield c("right_boundary_exact", [[0, 20, 2]], [16, 20], ready=16)
    yield c("right_boundary_too_late", [[0, 20, 2]], None, ready=17)
    yield c(
        "separate_short_windows",
        [[0, 3, 2], [3, 10, 0], [10, 13, 2], [13, 20, 0]],
        None,
        opens=[(0, 3), (10, 13)],
        duration=5,
    )
    yield c(
        "negative_absolute_time",
        [[-20, -10, 2], [-10, -5, 0], [-5, 0, 2]],
        [-20, -16],
        horizon=(-20, 0),
        maintenance=[(-10, -5)],
        ready=-30,
    )
    yield c(
        "billion_minute_horizon",
        [[0, 500000000, 2], [500000000, 500000001, 0], [500000001, 1000000000, 2]],
        [500000001, 500000006],
        horizon=(0, 1000000000),
        maintenance=[(500000000, 500000001)],
        ready=499999998,
        duration=5,
    )
    yield c(
        "maximal_segments_despite_boundaries",
        [[0, 20, 0]],
        None,
        opens=[],
        jobs=[(2, 8, 1), (4, 12, 2)],
        maintenance=[(7, 9)],
    )
    yield c(
        "continuous_booking_across_several_capacity_levels",
        [[0, 2, 3], [2, 5, 2], [5, 8, 1], [8, 10, 2], [10, 20, 3]],
        [1, 15],
        capacity=3,
        jobs=[(2, 10, 1), (5, 8, 1)],
        ready=1,
        duration=14,
    )


NET = code('''
    """Atomic bounded token movement."""
    def fire(marking, transition, places, capacities):
        current = dict(zip(places, marking))
        if any(current[p] < n for p, n in transition["consume"].items()):
            return None
        result = tuple(current[p] - transition["consume"].get(p, 0)
                       + transition["produce"].get(p, 0) for p in places)
        if any(n > capacities[p] for p, n in zip(places, result)):
            return None
        return result
''')

OBSERVATIONS = code('''
    """Address events without assigning an order inside an observation group."""
    def available(groups, group, mask):
        if group == len(groups):
            return []
        return [(i, event) for i, event in enumerate(groups[group]) if not mask & (1 << i)]

    def consume(groups, group, mask, index):
        updated = mask | (1 << index)
        if updated == (1 << len(groups[group])) - 1:
            return group + 1, 0
        return group, updated
''')

ALIGNMENT = code('''
    """Compute an auditable least-cost explanation of production observations."""
    import heapq
    from .net import fire
    from .observations import available, consume

    def search(request):
        places = sorted(request["capacities"])
        initial = tuple(request["initial"].get(p, 0) for p in places)
        final = tuple(request["final"].get(p, 0) for p in places)
        groups = request["groups"]
        initial_state = (0, 0, initial)
        best = {initial_state: (0, 0, ())}
        queue = [(0, 0, (), initial_state)]
        while queue:
            cost, length, path, state = heapq.heappop(queue)
            if best.get(state) != (cost, length, path):
                continue
            group, mask, marking = state
            if group == len(groups) and marking == final:
                return cost, path
            edges = []
            events = available(groups, group, mask)
            for index, event in events:
                next_group, next_mask = consume(groups, group, mask, index)
                edges.append(((next_group, next_mask, marking), event["skip_cost"],
                              ("log", event["id"], "")))
            for transition in request["transitions"]:
                changed = fire(marking, transition, places, request["capacities"])
                if changed is None:
                    continue
                edges.append(((group, mask, changed), transition["model_cost"],
                              ("model", "", transition["id"])))
                if transition["label"] is not None:
                    for index, event in events:
                        if event["label"] == transition["label"]:
                            next_group, next_mask = consume(groups, group, mask, index)
                            edges.append(((next_group, next_mask, changed), 0,
                                          ("sync", event["id"], transition["id"])))
            for target, price, move in edges:
                score = (cost + price, length + 1, path + (move,))
                if target not in best or score < best[target]:
                    best[target] = score
                    heapq.heappush(queue, (*score, target))
        return None, ()
''')

GREEDY_ALIGNMENT = code('''
    """Compute an auditable least-cost explanation of production observations."""
    from .net import fire
    from .observations import available, consume

    def search(request):
        places = sorted(request["capacities"])
        marking = tuple(request["initial"].get(p, 0) for p in places)
        final = tuple(request["final"].get(p, 0) for p in places)
        group, mask, cost, path = 0, 0, 0, ()
        seen = set()
        while (group, mask, marking) not in seen:
            seen.add((group, mask, marking))
            if group == len(request["groups"]) and marking == final:
                return cost, path
            choices = []
            events = available(request["groups"], group, mask)
            for transition in request["transitions"]:
                changed = fire(marking, transition, places, request["capacities"])
                if changed is None:
                    continue
                choices.append((transition["model_cost"], ("model", "", transition["id"]),
                                group, mask, changed))
                for index, event in events:
                    if transition["label"] is not None and event["label"] == transition["label"]:
                        g, m = consume(request["groups"], group, mask, index)
                        choices.append((0, ("sync", event["id"], transition["id"]), g, m, changed))
            for index, event in events:
                g, m = consume(request["groups"], group, mask, index)
                choices.append((event["skip_cost"], ("log", event["id"], ""), g, m, marking))
            if not choices:
                break
            price, move, group, mask, marking = min(choices)
            cost += price
            path += (move,)
        return None, ()
''')


def alignment_task():
    files = {
        "fabops/net.py": NET,
        "fabops/observations.py": OBSERVATIONS,
        "fabops/alignment.py": ALIGNMENT,
        "fabops/domain.py": code("""
            from .alignment import search

            def run(request):
                cost, path = search(request)
                return dict(accepted=cost is not None, cost=cost,
                            alignment=[dict(kind=k, event=e or None, transition=t or None)
                                       for k, e, t in path],
                            log_moves=sum(k == "log" for k, _, _ in path),
                            model_moves=sum(k == "model" for k, _, _ in path),
                            synchronous_moves=sum(k == "sync" for k, _, _ in path))
        """),
    }
    faults = (
        Change("fabops/alignment.py", ALIGNMENT, GREEDY_ALIGNMENT),
        Change(
            "fabops/observations.py",
            "return [(i, event) for i, event in enumerate(groups[group]) if not mask & (1 << i)]",
            "return [(i, event) for i, event in enumerate(groups[group]) if not mask & (1 << i)][:1]",
        ),
        Change(
            "fabops/net.py",
            'result = tuple(current[p] - transition["consume"].get(p, 0)\n                   + transition["produce"].get(p, 0) for p in places)',
            'result = tuple(current[p] - int(p in transition["consume"])\n                   + int(p in transition["produce"]) for p in places)',
        ),
    )
    mutants = {
        "greedy_local_alignment": (faults[0],),
        "serialized_observation_group": (faults[1],),
        "unweighted_token_firing": (faults[2],),
        "discard_log_moves": (
            Change(
                "fabops/alignment.py",
                'edges.append(((next_group, next_mask, marking), event["skip_cost"],\n                          ("log", event["id"], "")))',
                "pass",
            ),
        ),
        "discard_model_moves": (
            Change(
                "fabops/alignment.py",
                'edges.append(((group, mask, changed), transition["model_cost"],\n                          ("model", "", transition["id"])))',
                "pass",
            ),
        ),
        "accept_incomplete_marking": (
            Change(
                "fabops/alignment.py",
                "if group == len(groups) and marking == final:",
                "if group == len(groups):",
            ),
        ),
        "first_discovered_state": (
            Change(
                "fabops/alignment.py",
                "if target not in best or score < best[target]:",
                "if target not in best:",
            ),
        ),
        "ignore_tie_improvement": (
            Change(
                "fabops/alignment.py",
                "score < best[target]",
                "score[0] < best[target][0]",
            ),
        ),
        "unit_deviation_costs": (
            Change("fabops/alignment.py", 'event["skip_cost"],', "1,"),
            Change("fabops/alignment.py", 'transition["model_cost"],', "1,"),
        ),
        "premature_group_advance": (
            Change(
                "fabops/observations.py",
                "if updated == (1 << len(groups[group])) - 1:",
                "if updated:",
            ),
        ),
        "preconsumption_capacity": (
            Change(
                "fabops/net.py",
                "if any(n > capacities[p] for p, n in zip(places, result)):",
                'if any(current[p] + transition["produce"].get(p, 0) > capacities[p] for p in places):',
            ),
        ),
    }
    for name, key in (
        ("cache_ignores_marking", lambda item: f"{item}[:2]"),
        ("cache_ignores_event_mask", lambda item: f"({item}[0], {item}[2])"),
    ):
        mutants[name] = (
            Change(
                "fabops/alignment.py",
                "best = {initial_state: (0, 0, ())}",
                f"best = {{{key('initial_state')}: (0, 0, ())}}",
            ),
            Change(
                "fabops/alignment.py", "best.get(state)", f"best.get({key('state')})"
            ),
            Change(
                "fabops/alignment.py",
                "if target not in best or score < best[target]:\n                best[target] = score",
                f"if {key('target')} not in best or score < best[{key('target')}]:\n                best[{key('target')}] = score",
            ),
        )
    return Task(
        "F25",
        "Conformance diagnosis chooses locally cheap moves and loses event ambiguity",
        "hard",
        "optimal_partial_order_process_alignment",
        code("""
            Diagnose a production event log against a finite, weighted, capacity-bounded Petri
            net. capacities maps named places to positive limits. initial and final are token
            mappings; absent places have zero tokens. Each transition has unique nonempty id,
            label (nonempty activity string or null), consume and produce maps of positive
            integer weights, and positive integer model_cost. A firing requires all consumed
            tokens and must respect capacities AFTER atomic consumption and production.

            groups is a list of nonempty observation groups. Each event has a globally unique
            nonempty id, nonempty activity label, and positive integer skip_cost. Groups must
            be consumed in listed order, but events WITHIN a group have no known order and may
            be consumed in any permutation. Array order inside groups is only serialization.
            A synchronous move consumes one currently available event and fires a transition
            with the same non-null label, at zero cost. A log move consumes an available event
            without firing anything, at that event's skip_cost. A model move fires any enabled
            transition, including one with a visible label, without consuming an event, at its
            model_cost. Model moves can occur before, inside, between and after groups.

            A complete alignment consumes every event exactly once and reaches exactly final,
            including all leftover places. Minimize total cost globally, then number of moves,
            then the lexicographic sequence of move keys (kind,event_id,transition_id), where
            kinds are the literal strings log/model/sync and a missing identifier is the empty
            string. Return accepted, cost, alignment, log_moves, model_moves and synchronous_moves.
            Each alignment row has kind, event and transition; missing identifiers are null in
            the output. An impossible alignment returns accepted=false, cost=null, alignment=[],
            and all three counts zero. An already complete empty alignment is accepted at cost 0.
            Cycles, duplicate activity labels, parallel tokens, weighted self loops and globally
            cheaper explanations requiring a locally more expensive step are valid.

            At most six places, each capacity <=3; at most twelve transitions; at most ten
            events total and four per group. The reachable marking set has at most 256 members.
            Costs are integers 1..1000. Runtime must handle this bounded domain without enumerating
            arbitrarily long firing histories or all interleavings of repeated cycles. A valid
            input need not have a solution. Do not mutate the request while exploring alternatives.
        """),
        files,
        faults,
        mutants,
        tuple(alignment_cases()),
        ("production-log", "nist-sms"),
        extra_hidden_tests=ALIGNMENT_ORACLE,
        version="2.0",
        difficulty_reason="The prior F25 exact witness problem becomes an optimal deviation diagnosis over full token markings and partially ordered observations. Repair spans weighted atomic firing, event-consumption identity, global cost dominance, cycle-safe search and deterministic audit reconstruction. The faulty implementation is a local greedy algorithm, so correcting comparisons in the old exact-replay search cannot implement the new semantics.",
    )


def alignment_cases():
    def t(identifier, label, before, after, price=2):
        return {
            "id": identifier,
            "label": label,
            "consume": before,
            "produce": after,
            "model_cost": price,
        }

    def e(identifier, label, price=5):
        return {"id": identifier, "label": label, "skip_cost": price}

    def c(
        name,
        transitions,
        groups,
        moves,
        cost,
        *,
        initial=None,
        final=None,
        capacities=None,
        public=False,
    ):
        initial = initial if initial is not None else {"raw": 1}
        final = final if final is not None else {"done": 1}
        places = set(initial) | set(final)
        for item in transitions:
            places.update(item["consume"])
            places.update(item["produce"])
        request = {
            "initial": initial,
            "final": final,
            "capacities": capacities or {p: 3 for p in sorted(places)},
            "transitions": transitions,
            "groups": groups,
        }
        expected = {
            "accepted": cost is not None,
            "cost": cost,
            "alignment": [
                {"kind": k, "event": ev or None, "transition": tr or None}
                for k, ev, tr in moves
            ],
            "log_moves": sum(k == "log" for k, _, _ in moves),
            "model_moves": sum(k == "model" for k, _, _ in moves),
            "synchronous_moves": sum(k == "sync" for k, _, _ in moves),
        }
        return Case(name, request, expected, public=public)

    def s(event, transition):
        return "sync", event, transition

    def m(transition):
        return "model", "", transition

    def log_move(event):
        return "log", event, ""

    linear = [t("work", "work", {"raw": 1}, {"done": 1})]
    yield c(
        "exact_control", linear, [[e("w", "work")]], [s("w", "work")], 0, public=True
    )
    yield c("missing_event", linear, [], [m("work")], 2, public=True)
    yield c(
        "extra_observation",
        linear,
        [[e("x", "noise", 3)], [e("w", "work")]],
        [log_move("x"), s("w", "work")],
        3,
        public=True,
    )
    chain = [
        t("first", "a", {"raw": 1}, {"mid": 1}),
        t("second", "b", {"mid": 1}, {"done": 1}),
    ]
    yield c(
        "unordered_group",
        chain,
        [[e("b", "b"), e("a", "a")]],
        [s("a", "first"), s("b", "second")],
        0,
        public=True,
    )
    branches = [
        t("a_dead", "x", {"raw": 1}, {"dead": 1}, 1),
        t("z_live", "x", {"raw": 1}, {"mid": 1}, 4),
        t("finish", "y", {"mid": 1}, {"done": 1}, 1),
    ]
    yield c(
        "matching_label_dead_end",
        branches,
        [[e("x", "x")], [e("y", "y")]],
        [s("x", "z_live"), s("y", "finish")],
        0,
        public=True,
    )
    yield c(
        "weighted_self_loop",
        [t("batch", "b", {"p": 2}, {"p": 2})],
        [[e("b", "b")]],
        [s("b", "batch")],
        0,
        initial={"p": 2},
        final={"p": 2},
        capacities={"p": 2},
    )
    yield c(
        "weighted_consumption",
        [t("batch", "b", {"raw": 2}, {"done": 1})],
        [[e("b", "b")]],
        [s("b", "batch")],
        0,
        initial={"raw": 2},
    )
    yield c(
        "weighted_production",
        [t("split", "s", {"raw": 1}, {"done": 2})],
        [[e("s", "s")]],
        [s("s", "split")],
        0,
        final={"done": 2},
    )
    yield c(
        "unavailable_weight",
        [t("batch", "b", {"raw": 2}, {"done": 1})],
        [[e("b", "b")]],
        [],
        None,
    )
    yield c(
        "leftover_forbidden",
        linear,
        [[e("w", "work")]],
        [],
        None,
        initial={"raw": 1, "hold": 1},
    )
    yield c(
        "trailing_silent_cleanup",
        [
            t("work", "w", {"raw": 1}, {"mid": 1}),
            t("clean", None, {"mid": 1}, {"done": 1}, 3),
        ],
        [[e("w", "w")]],
        [s("w", "work"), m("clean")],
        3,
    )
    yield c(
        "leading_silent_route",
        [
            t("route", None, {"raw": 1}, {"mid": 1}, 3),
            t("work", "w", {"mid": 1}, {"done": 1}),
        ],
        [[e("w", "w")]],
        [m("route"), s("w", "work")],
        3,
    )
    yield c(
        "visible_model_step", chain, [[e("b", "b")]], [m("first"), s("b", "second")], 2
    )
    yield c(
        "skip_only",
        [],
        [[e("noise", "n", 7)]],
        [log_move("noise")],
        7,
        initial={"p": 1},
        final={"p": 1},
    )
    yield c("empty_complete", [], [], [], 0, initial={"p": 1}, final={"p": 1})
    yield c("empty_unreachable", [], [], [], None)
    yield c(
        "skip_after_completion",
        linear,
        [[e("w", "work")], [e("z", "noise", 4)]],
        [s("w", "work"), log_move("z")],
        4,
    )
    yield c(
        "ordered_groups_cannot_reverse",
        chain,
        [[e("b", "b", 1)], [e("a", "a", 7)]],
        [log_move("b"), s("a", "first"), m("second")],
        3,
    )
    yield c(
        "same_group_extra_event",
        chain,
        [[e("b", "b"), e("noise", "n", 3), e("a", "a")]],
        [log_move("noise"), s("a", "first"), s("b", "second")],
        3,
    )
    yield c(
        "duplicate_activity_occurrences",
        [t("a", "x", {"raw": 1}, {"mid": 1}), t("b", "x", {"mid": 1}, {"done": 1})],
        [[e("z", "x"), e("a", "x")]],
        [s("a", "a"), s("z", "b")],
        0,
    )
    yield c(
        "transition_tie_by_id",
        [
            t("z", "work", {"raw": 1}, {"done": 1}),
            t("a", "work", {"raw": 1}, {"done": 1}),
        ],
        [[e("w", "work")]],
        [s("w", "a")],
        0,
    )
    yield c(
        "globally_cheaper_model_route",
        [
            t("cheap", None, {"raw": 1}, {"mid": 1}, 1),
            t("expensive", None, {"mid": 1}, {"done": 1}, 9),
            t("direct", None, {"raw": 1}, {"done": 1}, 4),
        ],
        [],
        [m("direct")],
        4,
    )
    yield c(
        "same_cost_shortest_witness",
        [
            t("a", None, {"raw": 1}, {"mid": 1}, 1),
            t("b", None, {"mid": 1}, {"done": 1}, 1),
            t("z", None, {"raw": 1}, {"done": 1}, 2),
        ],
        [],
        [m("z")],
        2,
    )
    yield c(
        "relax_previously_discovered_state",
        [
            t("direct", None, {"raw": 1}, {"done": 1}, 8),
            t("a", None, {"raw": 1}, {"mid": 1}, 1),
            t("b", None, {"mid": 1}, {"done": 1}, 1),
        ],
        [],
        [m("a"), m("b")],
        2,
    )
    yield c(
        "positive_silent_cycle",
        [
            t("a_cycle", None, {"raw": 1}, {"raw": 1}, 1),
            t("finish", None, {"raw": 1}, {"done": 1}, 3),
        ],
        [],
        [m("finish")],
        3,
    )
    yield c(
        "parallel_join",
        [
            t("split", None, {"raw": 1}, {"a": 1, "b": 1}, 2),
            t("a", "a", {"a": 1}, {"a_done": 1}),
            t("b", "b", {"b": 1}, {"b_done": 1}),
            t("join", None, {"a_done": 1, "b_done": 1}, {"done": 1}, 3),
        ],
        [[e("eb", "b"), e("ea", "a")]],
        [m("split"), s("ea", "a"), s("eb", "b"), m("join")],
        5,
    )
    yield c(
        "skip_cheaper_than_wrong_matching_path",
        [
            t("wrong", "x", {"raw": 1}, {"mid": 1}),
            t("cleanup", None, {"mid": 1}, {"done": 1}, 20),
            t("direct", None, {"raw": 1}, {"done": 1}, 2),
        ],
        [[e("x", "x", 1)]],
        [log_move("x"), m("direct")],
        3,
    )
    yield c(
        "group_identity_changes_future_cost",
        [t("a", "x", {"raw": 1}, {"done": 1})],
        [[e("cheap", "x", 1), e("costly", "x", 9)]],
        [log_move("cheap"), s("costly", "a")],
        1,
    )
    yield c(
        "full_group_consumption",
        linear,
        [[e("w", "work"), e("a", "noise", 2), e("b", "noise", 3), e("c", "noise", 4)]],
        [log_move("a"), log_move("b"), log_move("c"), s("w", "work")],
        9,
    )
    yield c(
        "capacity_blocks_route",
        [t("work", "w", {"raw": 1}, {"done": 2})],
        [[e("w", "w")]],
        [],
        None,
        capacities={"raw": 1, "done": 1},
    )
    loops = [
        t("work", "w", {"p": 1}, {"p": 1}, 2),
        t("cycle", None, {"p": 1}, {"p": 1}, 1),
    ]
    groups = [
        [e(f"e{i}", "w") for i in (3, 2, 1, 0)],
        [e(f"e{i}", "w") for i in (7, 6, 5, 4)],
        [e("e9", "w"), e("e8", "w")],
    ]
    yield c(
        "bounded_ambiguous_repetition",
        loops,
        groups,
        [s(f"e{i}", "work") for i in range(10)],
        0,
        initial={"p": 1},
        final={"p": 1},
        capacities={"p": 1},
    )
    reservoir = [t(place, "fill", {}, {place: 1}, 1) for place in ("a", "b", "c", "d")]
    reservoir += [
        t(f"drain_{place}", None, {place: 1}, {}, 1) for place in ("a", "b", "c", "d")
    ]
    yield c(
        "full_256_marking_domain_with_event_ambiguity",
        reservoir,
        [
            [e(f"e{i}", "fill") for i in group]
            for group in ((3, 1, 0, 2), (7, 5, 4, 6), (9, 8))
        ],
        [m("a"), m("a")] + [s(f"e{i}", place) for i, place in enumerate("abbbcccddd")],
        2,
        initial={},
        final={"a": 3, "b": 3, "c": 3, "d": 3},
        capacities={"a": 3, "b": 3, "c": 3, "d": 3},
    )


CALENDAR_ORACLE = code("""
    def test_small_calendar_against_minute_occupancy():
        import random
        rng = random.Random(1102)
        for _ in range(80):
            def interval():
                return sorted(rng.sample(range(-2, 15), 2))
            request = dict(horizon=[0, 12], capacity=rng.randint(1, 4),
                           open=[interval() for _ in range(3)],
                           maintenance=[interval() for _ in range(2)],
                           jobs=[dict(zip(("start", "end", "units"), [*interval(), rng.randint(1, 3)]))
                                 for _ in range(3)],
                           query=dict(ready=rng.randint(-1, 12), duration=rng.randint(1, 6),
                                      units=rng.randint(1, 4)))
            before = copy.deepcopy(request)
            cells = []
            for minute in range(12):
                opened = sum(minute in range(a, b) for a, b in request["open"]) > 0
                closed = sum(minute in range(a, b) for a, b in request["maintenance"]) > 0
                busy = sum(j["units"] for j in request["jobs"] if minute in range(j["start"], j["end"]))
                cells.append(max(0, request["capacity"] - busy) if opened and not closed else 0)
            profile = []
            for minute, free in enumerate(cells):
                if profile and profile[-1][2] == free:
                    profile[-1][1] += 1
                else:
                    profile.append([minute, minute + 1, free])
            q = request["query"]
            starts = [start for start in range(max(0, q["ready"]), 13-q["duration"])
                      if min(cells[start:start+q["duration"]]) >= q["units"]]
            booking = [starts[0], starts[0]+q["duration"]] if starts else None
            assert run(request) == dict(profile=profile, available_unit_minutes=sum(cells), booking=booking)
            assert request == before
""")


ALIGNMENT_ORACLE = code("""
    def test_small_acyclic_alignments_against_exhaustive_histories():
        import random
        rng = random.Random(2502)
        for trial in range(60):
            # Acyclic one-token processes make exhaustive history enumeration finite;
            # this oracle has no priority queue, marking cache or production helpers.
            transitions = [dict(id=name, label=rng.choice([None, "a", "b"]),
                                consume={start:1}, produce={end:1}, model_cost=rng.randint(1,6))
                           for name,start,end in [("left","p0","p1"),("right","p1","p2"),("direct","p0","p2")]]
            events = [dict(id=f"e{i}",label=rng.choice(["a","b"]),skip_cost=rng.randint(1,6))
                      for i in range(3)]
            groups = [events] if trial % 2 else [events[:1],events[1:]]
            request = dict(capacities={"p0":1,"p1":1,"p2":1}, initial={"p0":1}, final={"p2":1},
                           transitions=transitions, groups=groups)
            before = copy.deepcopy(request)
            candidates = []
            all_ids = {e["id"] for e in events}
            def visit(place, consumed, cost, moves):
                if consumed == all_ids and place == "p2":
                    candidates.append((cost,len(moves),moves))
                    return
                active = []
                for group in groups:
                    active = [e for e in group if e["id"] not in consumed]
                    if active:
                        break
                for event in active:
                    visit(place, consumed | {event["id"]}, cost+event["skip_cost"],
                          moves+(("log",event["id"],""),))
                for t in transitions:
                    if place not in t["consume"]:
                        continue
                    target = next(iter(t["produce"]))
                    visit(target, consumed, cost+t["model_cost"], moves+(("model","",t["id"]),))
                    for event in active:
                        if event["label"] == t["label"]:
                            visit(target, consumed | {event["id"]}, cost,
                                  moves+(("sync",event["id"],t["id"]),))
            visit("p0",set(),0,())
            cost, _, moves = min(candidates)
            expected = dict(accepted=True,cost=cost,
                            alignment=[dict(kind=k,event=e or None,transition=t or None) for k,e,t in moves],
                            log_moves=sum(k=="log" for k,_,_ in moves),
                            model_moves=sum(k=="model" for k,_,_ in moves),
                            synchronous_moves=sum(k=="sync" for k,_,_ in moves))
            assert run(request) == expected
            assert request == before
""")
