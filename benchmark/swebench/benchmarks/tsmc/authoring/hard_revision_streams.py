"""Causal closure of durable multi-source telemetry prefixes."""

from dataclasses import replace
from .hard_infrastructure import snapshot_task
from .schema import Case, Change, code


def tasks():
    original = snapshot_task()
    files = dict(original.files)
    files["fabops/causal.py"] = code('''
        """Compute the greatest dependency-closed vector under certified source cuts."""
        def close(states, cut):
            prefixes = {name:max([0]+[event["sequence"] for event in state["events"].values()
                                     if event["sequence"] < state["next"] and event["time"] <= cut])
                        for name,state in states.items()}
            while True:
                candidate=dict(prefixes)
                for source,state in states.items():
                    for sequence in range(1,prefixes[source]+1):
                        event=state["events"][str(sequence)]
                        for dependency,epoch,required in event.get("depends",[]):
                            if states[dependency]["epoch"] != epoch or prefixes[dependency] < required:
                                candidate[source]=min(candidate[source],sequence-1)
                if candidate == prefixes:
                    return prefixes
                prefixes=candidate
    ''')
    files["fabops/snapshot.py"] = code('''
        """Publish a watermark-bounded causal cut only after all dependency retreats."""
        from .causal import close

        def materialize(states, required=None):
            if any(state["watermark"] < 0 for state in states.values()):
                return None
            cut=min(state["watermark"] for state in states.values())
            prefixes=close(states,cut)
            for source,(epoch,sequence) in (required or {}).items():
                if states[source]["epoch"] != epoch or prefixes[source] < sequence:
                    return None
            values={name:state["events"][str(prefixes[name])]["value"] if prefixes[name] else None
                    for name,state in states.items()}
            return dict(cut=cut,epochs={name:state["epoch"] for name,state in states.items()},values=values)
    ''')
    files["fabops/domain.py"] = files["fabops/domain.py"].replace(
        "snapshot = materialize(states)",
        'snapshot = materialize(states, command.get("required"))',
    )
    causal_fault = Change(
        "fabops/causal.py",
        files["fabops/causal.py"],
        code('''
        """Legacy event-time filtering assumes arrival progress implies causal completeness."""
        def close(states,cut):
            return {name:max([0]+[event["sequence"] for event in state["events"].values()
                                 if event["sequence"] < state["next"] and event["time"] <= cut])
                    for name,state in states.items()}
    '''),
    )
    # Preserve applicable delivery/checkpoint faults; the old materializer is replaced.
    applicable = tuple(f for f in original.faults if f.path != "fabops/snapshot.py")
    mutants = {
        name: changes
        for name, changes in original.mutants.items()
        if all(f.path != "fabops/snapshot.py" for f in changes)
    }
    mutants.update(
        {
            "watermark_only_cut": (causal_fault,),
            "single_retreat_pass": (
                Change("fabops/causal.py", "prefixes=candidate", "return candidate"),
            ),
            "latest_dependency_only": (
                Change(
                    "fabops/causal.py",
                    "range(1,prefixes[source]+1)",
                    "[prefixes[source]] if prefixes[source] else []",
                ),
            ),
            "dependency_epoch_ignored": (
                Change(
                    "fabops/causal.py", 'states[dependency]["epoch"] != epoch or ', ""
                ),
            ),
            "required_floor_ignored": (
                Change("fabops/snapshot.py", "(required or {}).items()", "{}.items()"),
            ),
        }
    )
    contract = original.contract + code("""

        Version 2 adds causal dependencies. Each event may include depends, a list of
        [source,epoch,positive sequence] references, default []. Sources are known, epochs
        are nonnegative; a referenced event need not yet be delivered. Every included
        source contributes a PREFIX, never a sparse set. A snapshot first computes the
        original cut=min(watermarks), then each source's maximum contiguous sequence
        with event.time<=cut. This is only an upper bound: find the componentwise greatest
        prefix vector at or below it whose EVERY included event's dependencies are also
        included in the referenced source's CURRENT epoch. If a dependency is unavailable,
        drop that event and its entire source suffix. Such retreat may invalidate earlier
        choices on other sources, requiring further retreat until all references hold.
        Mutual dependencies are allowed when both events are included. A mismatched old
        or future dependency epoch cannot be satisfied by a numerically larger sequence.

        snapshot may specify required={source:[epoch,minimum_sequence]}, default {}.
        These are lower bounds, not overrides of completeness or causality. If the greatest
        closed vector cannot meet any requested current-epoch floor, snapshot returns
        blocked and preserves the prior publication, even with crash=true. A zero prefix
        contributes value=None. Otherwise publish each source's latest value within its
        closed prefix; cut remains the common watermark-derived TIME UPPER BOUND, not a
        promise to include all events through that time. Return the original output shape.
        Page frontiers remain receipt/watermark progress and are not reduced by causal
        pruning. A later dependency page can make previously pruned events eligible again.
        Dependency fields participate in identical-retry comparison and persist across
        checkpoint/restart. At most 64 distinct events per source epoch and 50 commands.
    """)
    return [
        replace(
            original,
            version="2.0",
            title="Telemetry snapshots publish causally impossible cuts after buffered epoch recovery",
            family="durable_causal_prefix_fixed_point",
            files=files,
            faults=(*applicable, causal_fault),
            mutants=mutants,
            contract=contract,
            cases=(*original.cases, *cases()),
            difficulty_reason="Compute greatest dependency-closed prefix vectors across epoch-sensitive sources; repeated causal retreat interacts with durable out-of-order buffers, delayed watermark barriers, lower-bound publication requests and failed checkpoints.",
        )
    ]


def cases():
    def event(sequence, time, value, depends=()):
        return dict(
            sequence=sequence,
            time=time,
            value=value,
            depends=[list(d) for d in depends],
        )

    def page(source, events=(), epoch=0, through=None, watermark=10, **kw):
        return dict(
            op="page",
            source=source,
            epoch=epoch,
            events=list(events),
            through=through
            if through is not None
            else max([0] + [e["sequence"] for e in events]),
            watermark=watermark,
            **kw,
        )

    snap = dict(op="snapshot")
    restart = dict(op="restart")

    def case(
        name, commands, results, values, frontiers, epochs=None, public=False, cut=10
    ):
        snapshot = (
            None
            if values is None
            else dict(
                cut=cut, epochs=epochs or {k: 0 for k in frontiers}, values=values
            )
        )
        return Case(
            name,
            dict(sources=list(frontiers), commands=commands),
            dict(results=results, snapshot=snapshot, frontiers=frontiers),
            public=public,
        )

    a = page("a", [event(1, 1, 10, [("b", 0, 1)])])
    b = page("b", [])
    yield case(
        "missing_dependency_retreats",
        [a, b, snap],
        ["accepted", "accepted", "published"],
        {"a": None, "b": None},
        {"a": [0, 2, 10], "b": [0, 1, 10]},
        public=True,
    )
    yield case(
        "dependency_recovers_after_restart",
        [
            a,
            b,
            snap,
            restart,
            page("b", [event(1, 11, 20)], watermark=20),
            page("a", [], through=1, watermark=20),
            snap,
        ],
        [
            "accepted",
            "accepted",
            "published",
            "restarted",
            "accepted",
            "accepted",
            "published",
        ],
        {"a": 10, "b": 20},
        {"a": [0, 2, 20], "b": [0, 2, 20]},
        public=True,
        cut=20,
    )
    chain = [
        page("a", [event(1, 1, 1, [("b", 0, 1)])]),
        page("b", [event(1, 1, 2, [("c", 0, 1)])]),
        page("c", []),
    ]
    yield case(
        "fixed_point_cascade",
        chain + [snap],
        ["accepted"] * 3 + ["published"],
        {"a": None, "b": None, "c": None},
        {"a": [0, 2, 10], "b": [0, 2, 10], "c": [0, 1, 10]},
        public=True,
    )
    yield case(
        "earlier_event_dependency_poison",
        [page("a", [event(1, 1, 1, [("b", 0, 1)]), event(2, 2, 99)]), b, snap],
        ["accepted", "accepted", "published"],
        {"a": None, "b": None},
        {"a": [0, 3, 10], "b": [0, 1, 10]},
    )
    yield case(
        "causal_cascade_after_checkpoint_restart",
        chain + [restart, snap],
        ["accepted"] * 3 + ["restarted", "published"],
        {"a": None, "b": None, "c": None},
        {"a": [0, 2, 10], "b": [0, 2, 10], "c": [0, 1, 10]},
    )
    yield case(
        "retain_safe_prefix",
        [
            page("a", [event(1, 1, 1), event(2, 2, 2, [("b", 0, 1)]), event(3, 3, 3)]),
            b,
            snap,
        ],
        ["accepted", "accepted", "published"],
        {"a": 1, "b": None},
        {"a": [0, 4, 10], "b": [0, 1, 10]},
    )
    yield case(
        "mutual_dependencies_are_closed",
        [a, page("b", [event(1, 1, 20, [("a", 0, 1)])]), snap],
        ["accepted", "accepted", "published"],
        {"a": 10, "b": 20},
        {"a": [0, 2, 10], "b": [0, 2, 10]},
    )
    yield case(
        "wrong_dependency_epoch",
        [a, page("b", [event(1, 1, 20)], epoch=1), snap],
        ["accepted", "accepted", "published"],
        {"a": None, "b": 20},
        {"a": [0, 2, 10], "b": [1, 2, 10]},
        epochs={"a": 0, "b": 1},
    )
    yield case(
        "required_floor_blocks",
        [a, b, dict(op="snapshot", required={"a": [0, 1]})],
        ["accepted", "accepted", "blocked"],
        None,
        {"a": [0, 2, 10], "b": [0, 1, 10]},
    )
    yield case(
        "required_epoch_blocks",
        [page("a", [event(1, 1, 10)]), dict(op="snapshot", required={"a": [1, 1]})],
        ["accepted", "blocked"],
        None,
        {"a": [0, 2, 10]},
    )
    yield case(
        "future_event_outside_cut",
        [a, page("b", [event(1, 12, 20)], watermark=20), snap],
        ["accepted", "accepted", "published"],
        {"a": None, "b": None},
        {"a": [0, 2, 10], "b": [0, 2, 20]},
    )
    yield case(
        "gapped_dependency_prefix",
        [a, page("b", [event(2, 12, 20)], through=0), snap, restart],
        ["accepted", "accepted", "published", "restarted"],
        {"a": None, "b": None},
        {"a": [0, 2, 10], "b": [0, 1, 10]},
    )
    yield case(
        "crashed_causal_publication",
        [a, page("b", [event(1, 1, 20)]), dict(op="snapshot", crash=True), restart],
        ["accepted", "accepted", "crashed", "restarted"],
        None,
        {"a": [0, 2, 10], "b": [0, 2, 10]},
    )
    yield case(
        "zero_floor_does_not_require_event",
        [a, b, dict(op="snapshot", required={"a": [0, 0]})],
        ["accepted", "accepted", "published"],
        {"a": None, "b": None},
        {"a": [0, 2, 10], "b": [0, 1, 10]},
    )
