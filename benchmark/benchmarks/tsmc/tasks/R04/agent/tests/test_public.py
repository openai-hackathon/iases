import json, subprocess, sys
from pathlib import Path

def test_public_cli_fixture():
    p=subprocess.run([sys.executable,"-m","fabops","--input","data/request.json"],capture_output=True,text=True,timeout=10,check=True)
    assert json.loads(p.stdout)==json.loads(Path("data/expected.json").read_text())

import asyncio,pytest
from fabops.worker_pool import WorkerPool

def scenario(coro):return asyncio.run(asyncio.wait_for(coro,timeout=4))

async def ok():return 7
async def boom():raise RuntimeError('error')

def test_error_releases_slot():
    async def case():
        p=WorkerPool(1)
        with pytest.raises(RuntimeError):await p.execute(boom)
        assert p.active==0 and p.free_slots==1
    scenario(case())

def test_normal_result():
    async def case():
        p=WorkerPool(1);assert await p.execute(ok)==7;assert p.active==0
    scenario(case())

def test_invalid_limit():
    with pytest.raises(ValueError):WorkerPool(0)
