import copy
import pytest
from fabops.domain import run


def test_empty():
    request = {'commands': []}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {}, 'calls': [], 'cancellations': [], 'active': 0}
    assert request == before

def test_same_identity_shares():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'p', 'value': 7}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'value', 'value': 7}, 'b': {'status': 'value', 'value': 7}}, 'calls': [['p', 'cell', 'sensor', 0]], 'cancellations': [], 'active': 0}
    assert request == before

def test_distinct_keys():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'a', 'resistant': False}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'cell', 'key': 'b', 'resistant': False}, {'op': 'finish', 'job': 'p', 'value': 1}, {'op': 'finish', 'job': 'q', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'value', 'value': 1}, 'b': {'status': 'value', 'value': 2}}, 'calls': [['p', 'cell', 'a', 0], ['q', 'cell', 'b', 0]], 'cancellations': [], 'active': 0}
    assert request == before

def test_last_cancel_reclaims():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'cancel', 'waiter': 'a'}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'cancelled'}}, 'calls': [['p', 'cell', 'sensor', 0]], 'cancellations': ['p'], 'active': 0}
    assert request == before

def test_all_cancel_then_retry():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'cancel', 'waiter': 'a'}, {'op': 'cancel', 'waiter': 'b'}, {'op': 'join', 'waiter': 'c', 'job': 'r', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'r', 'value': 8}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'cancelled'}, 'b': {'status': 'cancelled'}, 'c': {'status': 'value', 'value': 8}}, 'calls': [['p', 'cell', 'sensor', 0], ['r', 'cell', 'sensor', 0]], 'cancellations': ['p'], 'active': 0}
    assert request == before

def test_failure_not_cached():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'p', 'error': 'offline'}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'q', 'value': 8}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'error', 'error': 'offline'}, 'b': {'status': 'value', 'value': 8}}, 'calls': [['p', 'cell', 'sensor', 0], ['q', 'cell', 'sensor', 0]], 'cancellations': [], 'active': 0}
    assert request == before

def test_success_not_cached():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'p', 'value': 1}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'q', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'value', 'value': 1}, 'b': {'status': 'value', 'value': 2}}, 'calls': [['p', 'cell', 'sensor', 0], ['q', 'cell', 'sensor', 0]], 'cancellations': [], 'active': 0}
    assert request == before

def test_invalidate_other_scope():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'x', 'key': 'sensor', 'resistant': False}, {'op': 'invalidate', 'scope': 'y'}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'x', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'p', 'value': 4}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'value', 'value': 4}, 'b': {'status': 'value', 'value': 4}}, 'calls': [['p', 'x', 'sensor', 0]], 'cancellations': [], 'active': 0}
    assert request == before

def test_double_invalidation():
    request = {'commands': [{'op': 'invalidate', 'scope': 'cell'}, {'op': 'invalidate', 'scope': 'cell'}, {'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'p', 'value': 0}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'value', 'value': 0}}, 'calls': [['p', 'cell', 'sensor', 2]], 'cancellations': [], 'active': 0}
    assert request == before

def test_stale_resistant_completion_cannot_retire_replacement():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': True}, {'op': 'cancel', 'waiter': 'a'}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'p', 'value': 1}, {'op': 'join', 'waiter': 'c', 'job': 'r', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'q', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'cancelled'}, 'b': {'status': 'value', 'value': 2}, 'c': {'status': 'value', 'value': 2}}, 'calls': [['p', 'cell', 'sensor', 0], ['q', 'cell', 'sensor', 0]], 'cancellations': ['p'], 'active': 0}
    assert request == before

def test_stale_resistant_failure_cannot_retire_replacement():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': True}, {'op': 'cancel', 'waiter': 'a'}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'p', 'error': 'stale'}, {'op': 'join', 'waiter': 'c', 'job': 'r', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'finish', 'job': 'q', 'value': 2}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'cancelled'}, 'b': {'status': 'value', 'value': 2}, 'c': {'status': 'value', 'value': 2}}, 'calls': [['p', 'cell', 'sensor', 0], ['q', 'cell', 'sensor', 0]], 'cancellations': ['p'], 'active': 0}
    assert request == before

def test_pending_producer_retained():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'cell', 'key': 'sensor', 'resistant': False}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'pending'}, 'b': {'status': 'pending'}}, 'calls': [['p', 'cell', 'sensor', 0]], 'cancellations': [], 'active': 1}
    assert request == before

def test_old_generation_cancel_does_not_touch_new():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'invalidate', 'scope': 'cell'}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'cancel', 'waiter': 'a'}, {'op': 'finish', 'job': 'q', 'value': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'cancelled'}, 'b': {'status': 'value', 'value': 5}}, 'calls': [['p', 'cell', 'sensor', 0], ['q', 'cell', 'sensor', 1]], 'cancellations': ['p'], 'active': 0}
    assert request == before

def test_cancel_follower_in_new_generation():
    request = {'commands': [{'op': 'invalidate', 'scope': 'cell'}, {'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'cancel', 'waiter': 'b'}, {'op': 'finish', 'job': 'p', 'value': 5}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'value', 'value': 5}, 'b': {'status': 'cancelled'}}, 'calls': [['p', 'cell', 'sensor', 1]], 'cancellations': [], 'active': 0}
    assert request == before

def test_scope_isolation_with_cancellation():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'x', 'key': 'sensor', 'resistant': False}, {'op': 'join', 'waiter': 'b', 'job': 'q', 'scope': 'y', 'key': 'sensor', 'resistant': False}, {'op': 'cancel', 'waiter': 'a'}, {'op': 'finish', 'job': 'q', 'value': 6}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'cancelled'}, 'b': {'status': 'value', 'value': 6}}, 'calls': [['p', 'x', 'sensor', 0], ['q', 'y', 'sensor', 0]], 'cancellations': ['p'], 'active': 0}
    assert request == before

def test_invalidate_preserves_old_waiter():
    request = {'commands': [{'op': 'join', 'waiter': 'a', 'job': 'p', 'scope': 'cell', 'key': 'sensor', 'resistant': False}, {'op': 'invalidate', 'scope': 'cell'}, {'op': 'finish', 'job': 'p', 'value': 9}]}
    before = copy.deepcopy(request)
    assert run(request) == {'results': {'a': {'status': 'value', 'value': 9}}, 'calls': [['p', 'cell', 'sensor', 0]], 'cancellations': [], 'active': 0}
    assert request == before

def test_direct_generation_owner_handoff():
    import asyncio
    from fabops.flight import SingleFlight
    async def exercise():
        flight = SingleFlight()
        old_started, old_cancelled, old_finish = asyncio.Event(), asyncio.Event(), asyncio.Event()
        new_started, new_finish = asyncio.Event(), asyncio.Event()
        old_done = asyncio.Event()
        calls = []
        async def old_loader(scope, key, generation):
            calls.append((scope,key,generation,"old"))
            old_started.set()
            try:
                await old_finish.wait()
            except asyncio.CancelledError:
                old_cancelled.set()
                await old_finish.wait()
            old_done.set()
            return "old"
        async def new_loader(scope,key,generation):
            calls.append((scope,key,generation,"new"))
            new_started.set()
            await new_finish.wait()
            return "new"
        async def unused_loader(*args):
            raise AssertionError("Replacement follower started another producer")
        try:
            old = asyncio.create_task(flight.get("fab","sensor",old_loader))
            await old_started.wait()
            old.cancel()
            await asyncio.gather(old,return_exceptions=True)
            await old_cancelled.wait()
            current = asyncio.create_task(flight.get("fab","sensor",new_loader))
            await new_started.wait()
            old_finish.set()
            await old_done.wait()
            follower = asyncio.create_task(flight.get("fab","sensor",unused_loader))
            new_finish.set()
            assert await asyncio.gather(current,follower) == ["new","new"]
            assert calls == [("fab","sensor",0,"old"),("fab","sensor",0,"new")]
        finally:
            old_finish.set()
            new_finish.set()

    asyncio.run(asyncio.wait_for(exercise(), timeout=1))

def test_direct_scope_generation_invalidation():
    import asyncio
    from fabops.flight import SingleFlight
    async def exercise():
        flight = SingleFlight()
        starts = [asyncio.Event(),asyncio.Event()]
        gates = [asyncio.Event(),asyncio.Event()]
        calls = []
        async def loader(scope,key,generation):
            calls.append((scope,key,generation))
            starts[generation].set()
            await gates[generation].wait()
            return generation
        first = asyncio.create_task(flight.get("fab","sensor",loader))
        await starts[0].wait()
        flight.invalidate("fab")
        second = asyncio.create_task(flight.get("fab","sensor",loader))
        await starts[1].wait()
        gates[1].set()
        assert await second == 1
        assert not first.done()
        gates[0].set()
        assert await first == 0
        assert calls == [("fab","sensor",0),("fab","sensor",1)]
    asyncio.run(asyncio.wait_for(exercise(), timeout=1))
