"""Track producer ownership across independently invalidated scopes."""
import asyncio

class Registry:
    def __init__(self):
        self.generations = {}
        self.entries = {}
        self.tasks = set()

    def identity(self, scope, key):
        return (scope, key, self.generations.get(scope, 0))

    def invalidate(self, scope):
        self.generations[scope] = self.generations.get(scope, 0) + 1

    def retire(self, identity, entry):
        if self.entries.get(identity) is entry:
            self.entries.pop(identity, None)

    def acquire(self, scope, key, loader):
        identity = self.identity(scope, key)
        entry = self.entries.get(identity)
        if entry is None or entry["task"].done():
            task = asyncio.create_task(loader(scope, key, identity[2]))
            entry = {"task": task, "waiters": 0}
            self.entries[identity] = entry
            self.tasks.add(task)
            def done(task):
                self.retire(identity, entry)
                self.tasks.discard(task)
                if not task.cancelled():
                    task.exception()
            task.add_done_callback(done)
        entry["waiters"] += 1
        return identity, entry

    def release(self, identity, entry):
        entry["waiters"] -= 1
        if entry["waiters"] == 0:
            self.retire(identity, entry)
            if not entry["task"].done():
                entry["task"].cancel()
