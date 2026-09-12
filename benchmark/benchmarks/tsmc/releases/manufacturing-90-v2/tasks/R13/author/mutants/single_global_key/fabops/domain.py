import asyncio
class SingleFlight:
    def __init__(self):
        self.pending = {}
    def discard(self, key, task):
        if self.pending.get(key) is task:
            self.pending.pop(key)
    async def get(self, key, loader):
        key = "shared"
        if key not in self.pending:
            self.pending[key] = asyncio.create_task(loader(key))
            self.pending[key].add_done_callback(lambda done: self.discard(key, done))
        task = self.pending[key]
        try:
            return await asyncio.shield(task)
        finally:
            if task.done() and self.pending.get(key) is task:
                del self.pending[key]
async def exercise(request):
    flight, calls, output = SingleFlight(), {}, []
    for round in request["rounds"]:
        gate = asyncio.Event()
        async def loader(key):
            calls[key] = calls.get(key, 0) + 1
            await gate.wait()
            return key
        waiters = [asyncio.create_task(flight.get(key, loader)) for key in round["keys"]]
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        for index in round["cancel"]:
            waiters[index].cancel()
        await asyncio.sleep(0)
        gate.set()
        results = await asyncio.gather(*waiters, return_exceptions=True)
        output.append(["cancelled" if isinstance(r, asyncio.CancelledError) else r for r in results])
        for key, task in list(flight.pending.items()):
            await asyncio.gather(task, return_exceptions=True)
            if task.done():
                flight.pending.pop(key, None)
    return dict(results=output, calls=calls)
def run(request):
    return asyncio.run(exercise(request))
