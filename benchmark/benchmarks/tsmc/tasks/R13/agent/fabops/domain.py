import asyncio
from .flight import SingleFlight

async def exercise(request):
    flight = SingleFlight()
    gates, answers, waiters, calls, cancellations = {}, {}, {}, [], []
    async def settle():
        for _ in range(8):
            await asyncio.sleep(0)
    for command in request["commands"]:
        op = command["op"]
        if op == "join":
            job = command["job"]
            gates.setdefault(job, asyncio.Event())
            async def loader(scope, key, generation, job=job, resistant=command.get("resistant", False)):
                calls.append([job, scope, key, generation])
                try:
                    await gates[job].wait()
                except asyncio.CancelledError:
                    cancellations.append(job)
                    if not resistant:
                        raise
                    await gates[job].wait()
                answer = answers[job]
                if answer.get("error"):
                    raise ValueError(answer["error"])
                return answer.get("value")
            waiters[command["waiter"]] = asyncio.create_task(
                flight.get(command["scope"], command["key"], loader))
        elif op == "cancel":
            waiters[command["waiter"]].cancel()
        elif op == "invalidate":
            flight.invalidate(command["scope"])
        else:
            answers[command["job"]] = command
            gates.setdefault(command["job"], asyncio.Event()).set()
        await settle()
    results = {}
    for name, waiter in waiters.items():
        if waiter.cancelled():
            results[name] = {"status": "cancelled"}
        elif not waiter.done():
            results[name] = {"status": "pending"}
        elif waiter.exception() is not None:
            results[name] = {"status": "error", "error": str(waiter.exception())}
        else:
            results[name] = {"status": "value", "value": waiter.result()}
    active = len(flight.registry.entries)
    for job, gate in gates.items():
        answers.setdefault(job, {"value": None})
        gate.set()
    await settle()
    for waiter in waiters.values():
        if not waiter.done():
            waiter.cancel()
    await asyncio.gather(*waiters.values(), return_exceptions=True)
    await asyncio.gather(*list(flight.registry.tasks), return_exceptions=True)
    return dict(results=results, calls=calls, cancellations=cancellations, active=active)

def run(request):
    return asyncio.run(exercise(request))
