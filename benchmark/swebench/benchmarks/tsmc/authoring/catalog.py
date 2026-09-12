"""Author task registry, with each causal bug family assigned to one split."""

from . import (
    analysis_medium,
    easy,
    expansion_analysis,
    expansion_easy,
    expansion_factory,
    expansion_reliability,
    factory_medium,
    hard,
    hard_infrastructure,
    hard_process,
    hard_sensors,
    hard_revision_factory,
    hard_revision_ingestion,
    hard_revision_leases,
    hard_revision_packages,
    hard_revision_sensors,
    hard_revision_streams,
    reliability_medium,
    revision_analysis,
    revision_process,
    revision_reliability,
)
from dataclasses import replace
from .schema import Case, code


def tasks():
    revisions = {
        task.task_id: task
        for module in (
            revision_analysis,
            revision_process,
            revision_reliability,
            hard_revision_factory,
            hard_revision_ingestion,
            hard_revision_leases,
            hard_revision_packages,
            hard_revision_sensors,
            hard_revision_streams,
        )
        for task in module.tasks()
    }
    modules = [
        easy,
        factory_medium,
        analysis_medium,
        reliability_medium,
        expansion_easy,
        expansion_factory,
        expansion_analysis,
        expansion_reliability,
        hard,
        hard_infrastructure,
        hard_process,
        hard_sensors,
    ]
    result = []
    for module in modules:
        for task in module.tasks():
            task = revisions.get(task.task_id, task)
            if task.task_id == "F23":
                task = replace(
                    task,
                    cases=(
                        *task.cases,
                        Case(
                            "cyclic_graph",
                            {
                                "jobs": [
                                    {
                                        "id": "a",
                                        "resource": "m",
                                        "duration": 1,
                                        "release": 0,
                                        "depends": ["b"],
                                    },
                                    {
                                        "id": "b",
                                        "resource": "n",
                                        "duration": 1,
                                        "release": 0,
                                        "depends": ["a"],
                                    },
                                ]
                            },
                            error="ValueError",
                        ),
                    ),
                )
            if task.task_id == "R13" and task.version == "1.0":
                task = replace(task, extra_hidden_tests=SINGLEFLIGHT_LIFECYCLE)
            result.append(task)
    if set(revisions) - {task.task_id for task in result}:
        raise ValueError("A revision must replace an existing task")
    return sorted(result, key=lambda task: task.task_id)


SINGLEFLIGHT_LIFECYCLE = code("""
    def test_all_waiters_cancel_then_new_request():
        import asyncio
        from fabops.domain import SingleFlight
        async def scenario():
            flight, gate, calls = SingleFlight(), asyncio.Event(), []
            async def loader(key):
                calls.append(key)
                await gate.wait()
                return len(calls)
            waiter = asyncio.create_task(flight.get("a", loader))
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            shared = flight.pending["a"]
            waiter.cancel()
            await asyncio.gather(waiter, return_exceptions=True)
            gate.set()
            await asyncio.gather(shared, return_exceptions=True)
            assert await flight.get("a", loader) == 2
            assert calls == ["a", "a"]
        asyncio.run(scenario())

    def test_failed_loader_does_not_poison_the_key():
        import asyncio
        from fabops.domain import SingleFlight
        async def scenario():
            flight, calls = SingleFlight(), []
            async def loader(key):
                calls.append(key)
                if len(calls) == 1:
                    raise ValueError("temporary failure")
                return "ok"
            with pytest.raises(ValueError):
                await flight.get("a", loader)
            assert await flight.get("a", loader) == "ok"
            assert calls == ["a", "a"]
        asyncio.run(scenario())
""")
