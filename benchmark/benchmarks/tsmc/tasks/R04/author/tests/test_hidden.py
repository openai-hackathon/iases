import json, subprocess, sys
from pathlib import Path

def test_hidden_cli_fixture():
    root=Path(__file__).parent.parent / "data"
    p=subprocess.run([sys.executable,"-m","fabops","--input",str(root/"request.json")],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads((root/"expected.json").read_text())

import asyncio,pytest
from fabops.worker_pool import WorkerPool

def scenario(coro):return asyncio.run(asyncio.wait_for(coro,timeout=4))

async def ok():return 7
async def boom():raise RuntimeError('error')

def test_running_task_cancellation_cleanup():
    async def case():
        p=WorkerPool(1);started=asyncio.Event();gate=asyncio.Event()
        async def job():started.set();await gate.wait()
        t=asyncio.create_task(p.execute(job));await started.wait();t.cancel()
        with pytest.raises(asyncio.CancelledError):await t
        assert p.active==0 and p.free_slots==1
        assert await asyncio.wait_for(p.execute(ok),1)==7
    scenario(case())

def test_waiter_cancellation_does_not_release_owner_slot():
    async def case():
        p=WorkerPool(1);started=asyncio.Event();gate=asyncio.Event()
        async def job():started.set();await gate.wait();return 9
        owner=asyncio.create_task(p.execute(job));await started.wait()
        waiter=asyncio.create_task(p.execute(ok));await asyncio.sleep(0);waiter.cancel()
        with pytest.raises(asyncio.CancelledError):await waiter
        assert p.active==1 and p.free_slots==0
        gate.set();assert await owner==9;assert p.active==0
    scenario(case())

def test_exception_then_next_job():
    async def case():
        p=WorkerPool(1)
        with pytest.raises(RuntimeError):await p.execute(boom)
        assert await asyncio.wait_for(p.execute(ok),1)==7
    scenario(case())

def test_internal_cancelled_error():
    async def case():
        p=WorkerPool(1)
        async def cancelled():raise asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):await p.execute(cancelled)
        assert p.free_slots==1
    scenario(case())

def test_concurrency_ceiling():
    async def case():
        p=WorkerPool(2);both=asyncio.Event();release=asyncio.Event();entered=0
        async def job():
            nonlocal entered
            entered+=1
            if entered==2:both.set()
            await release.wait();return 1
        ts=[asyncio.create_task(p.execute(job)) for _ in range(3)]
        await both.wait();await asyncio.sleep(0);assert p.active==2 and entered==2
        release.set();assert await asyncio.gather(*ts)==[1,1,1];assert p.active==0 and p.peak==2
    scenario(case())

def test_many_successes_no_double_release():
    async def case():
        p=WorkerPool(1)
        for _ in range(10):assert await p.execute(ok)==7;assert p.active==0 and p.free_slots==1
        assert p.peak==1
    scenario(case())

def test_callback_type_error_cleanup():
    async def case():
        p=WorkerPool(1)
        with pytest.raises(TypeError):await p.execute(lambda:123)
        assert p.active==0
    scenario(case())

def test_cancel_before_start():
    async def case():
        p=WorkerPool(1);t=asyncio.create_task(p.execute(ok));t.cancel()
        with pytest.raises(asyncio.CancelledError):await t
        assert p.active==0
    scenario(case())

def test_success_result_preserved():
    async def case():
        p=WorkerPool(2)
        async def result():return {'sum':42}
        assert await p.execute(result)=={'sum':42}
    scenario(case())

def test_limits_reject_bool_negative_float():
    for x in [True,-1,1.5]:
        with pytest.raises(ValueError):WorkerPool(x)
