import copy
import pytest
from fabops.domain import run


def test_cancel_second():
    request = {'rounds': [{'keys': ['a', 'a'], 'cancel': [1]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [['a', 'cancelled']], 'calls': {'a': 1}}
    assert request == before

def test_three():
    request = {'rounds': [{'keys': ['a', 'a', 'a'], 'cancel': [1]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [['a', 'cancelled', 'a']], 'calls': {'a': 1}}
    assert request == before

def test_distinct():
    request = {'rounds': [{'keys': ['a', 'b'], 'cancel': []}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [['a', 'b']], 'calls': {'a': 1, 'b': 1}}
    assert request == before

def test_new_round():
    request = {'rounds': [{'keys': ['a'], 'cancel': []}, {'keys': ['a'], 'cancel': []}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [['a'], ['a']], 'calls': {'a': 2}}
    assert request == before

def test_cancel_all():
    request = {'rounds': [{'keys': ['a', 'a'], 'cancel': [0, 1]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [['cancelled', 'cancelled']], 'calls': {'a': 1}}
    assert request == before

def test_mixed():
    request = {'rounds': [{'keys': ['a', 'b', 'a'], 'cancel': [0]}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': [['cancelled', 'b', 'a']], 'calls': {'a': 1, 'b': 1}}
    assert request == before

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
