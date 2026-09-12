"""One caller's cancellation does not own a shared producer."""
import asyncio
from .registry import Registry

class SingleFlight:
    def __init__(self):
        self.registry = Registry()

    def invalidate(self, scope):
        self.registry.invalidate(scope)

    async def get(self, scope, key, loader):
        identity, entry = self.registry.acquire(scope, key, loader)
        try:
            return await asyncio.shield(entry["task"])
        finally:
            self.registry.release(identity, entry)
