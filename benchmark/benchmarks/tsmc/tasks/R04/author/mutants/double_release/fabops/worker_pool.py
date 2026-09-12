"""Bounded slots for local analysis jobs; unrelated to the inference router."""
import asyncio

class WorkerPool:
    def __init__(self,limit):
        if type(limit) is not int or limit<=0:raise ValueError('positive integer limit required')
        self.limit=limit
        self.active=0
        self.peak=0
        self._slots=asyncio.BoundedSemaphore(limit)

    async def execute(self,job):
        await self._slots.acquire()
        self.active+=1
        self.peak=max(self.peak,self.active)
        try:
            return await job()
        finally:
            self.active-=1
            self._slots.release()
            self._slots.release()

    @property
    def free_slots(self):return self.limit-self.active

def run(data):
    async def scenario():
        pool=WorkerPool(data['limit']);out=[]
        for spec in data['jobs']:
            async def job():
                if spec['outcome']=='error':raise RuntimeError('analysis error')
                if spec['outcome']=='cancel':raise asyncio.CancelledError()
                return sum(spec.get('values',[]))
            try:out.append({'ok':await pool.execute(job)})
            except asyncio.CancelledError:out.append({'status':'cancelled'})
            except RuntimeError:out.append({'status':'error'})
        return {'results':out,'active':pool.active,'free_slots':pool.free_slots,'peak':pool.peak}
    return asyncio.run(scenario())
