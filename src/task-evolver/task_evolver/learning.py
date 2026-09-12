import threading
import time
from dataclasses import asdict

from .active import select_question
from .expansion import OpenAIExpander, normalize_key
from .semantic import lookup_details
from .store import PairStore
from .table import ImportanceTable
from .validation import validate_pair_values
from .workflow import TaskEvolver


def ask_score(first, second):
    while True:
        try:
            value = float(
                input(f"A: {first}\nB: {second}\nScore 0–1 (1=A, 0=B, 0.5=equal): ")
            )
            return validate_pair_values(value, 1.0)[0]
        except ValueError:
            print("Enter a finite number from 0 to 1.", flush=True)


def ensure_key(evolver, key, ask=ask_score):
    key = normalize_key(key)
    if evolver.lookup(key) is not None:
        return None
    if key == evolver.ref_key:
        evolver.refit()
        return None
    return evolver.answer(key, evolver.ref_key, ask(key, evolver.ref_key))


class LearningQueue:
    def __init__(self, db, reference, snapshot, bindings, updated):
        self.jobs = {}
        self.waiting = {}
        self.asked = {}
        self.remaining = 10
        self.pending = set()
        self.lock = threading.Condition()
        self.closed = False
        self.thread = threading.Thread(
            target=self.run,
            args=(db, reference, snapshot, bindings, updated),
            daemon=True,
        )
        self.thread.start()

    def request(self, key):
        try:
            key = normalize_key(key)
        except (TypeError, ValueError):
            return
        with self.lock:
            if self.closed or key in self.pending or len(self.pending) >= 4096:
                return
            self.jobs[key] = False
            self.pending.add(key)
            self.lock.notify()

    def observe(self, waiting):
        with self.lock:
            self.waiting = dict(list(waiting.items())[:64])
            for key, queued in list(self.jobs.items()):
                if queued and key not in self.waiting:
                    self.jobs.pop(key)
                    self.pending.discard(key)
            for key in self.waiting:
                if (
                    not self.closed
                    and key not in self.pending
                    and len(self.pending) < 4096
                ):
                    self.jobs[key] = True
                    self.pending.add(key)
            self.lock.notify()

    def run(self, db, reference, snapshot, bindings, updated):
        store = None
        table = None
        try:
            store = PairStore(db)
            table = ImportanceTable(db, snapshot_path=snapshot, bindings=bindings)
            evolver = TaskEvolver(store, table, OpenAIExpander(), reference)
            while self.remaining:
                with self.lock:
                    self.lock.wait_for(lambda: self.jobs)
                    self.lock.wait(timeout=0.05)
                    keys = list(self.jobs)[:64]
                    waiting = self.waiting.copy()
                question = select_question(
                    evolver, keys, waiting, self.asked, time.monotonic()
                )
                key = question.first if question else keys[0] if keys else None
                if key is None:
                    continue
                with self.lock:
                    if key not in self.jobs:
                        continue
                    was_queued = self.jobs.pop(key)
                try:
                    if question:
                        details = lookup_details(evolver, key)
                        with self.lock:
                            if was_queued and key not in self.waiting:
                                continue
                            current = select_question(
                                evolver,
                                [key],
                                self.waiting,
                                self.asked,
                                time.monotonic(),
                            )
                        if current is None:
                            continue
                        question = current
                        self.asked[tuple(sorted((key, question.second)))] = (
                            time.monotonic()
                        )
                        self.remaining -= 1
                        print(
                            {"question": asdict(question), "lookup": details},
                            flush=True,
                        )
                        result = evolver.answer(
                            key, question.second, ask_score(key, question.second)
                        )
                        print(asdict(result), flush=True)
                    elif key == reference:
                        ensure_key(evolver, key)
                        print({"known": key}, flush=True)
                    updated()
                except EOFError:
                    return
                except (OSError, ValueError, RuntimeError) as exc:
                    print({"learning_error": type(exc).__name__}, flush=True)
                finally:
                    with self.lock:
                        self.pending.discard(key)
            print({"question_budget_exhausted": 10}, flush=True)
        except (OSError, ValueError, RuntimeError) as exc:
            print({"learning_error": type(exc).__name__}, flush=True)
        finally:
            with self.lock:
                self.closed = True
            if store is not None:
                store.conn.close()
            if table is not None:
                table.conn.close()
