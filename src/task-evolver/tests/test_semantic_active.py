import asyncio
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from task_evolver import ImportanceTable, PairStore, TaskEvolver
from task_evolver.active import select_question
from task_evolver.admission import AdmissionService
from task_evolver.learning import LearningQueue
from task_evolver.semantic import OpenAIEmbeddings, lookup_details


class SemanticActiveTest(unittest.TestCase):
    def setUp(self):
        self.store = PairStore()
        self.table = ImportanceTable()
        self.addCleanup(self.store.conn.close)
        self.addCleanup(self.table.conn.close)
        self.expander = Mock()
        self.expander.expand.return_value = []
        self.evolver = TaskEvolver(self.store, self.table, self.expander, "reference")
        self.evolver.answer("incident", "reference", 0.9)
        self.embedder = Mock(model="test-embedding")
        self.embedder.embed.side_effect = lambda keys: [
            [1.0, 0.0] if key != "reference" else [0.0, 1.0] for key in keys
        ]

    def test_semantic_candidates_are_cached_and_human_wins(self):
        pairs = self.store.effective()
        version = self.table.fit_version()
        first = lookup_details(self.evolver, "production outage", self.embedder)
        second = lookup_details(self.evolver, "production outage", self.embedder)
        self.assertEqual(first, second)
        self.assertEqual(first["source"], "embedding")
        self.assertIsNone(first["importance"])
        self.assertEqual(
            first["candidates"],
            [
                {
                    "key": "incident",
                    "importance": self.evolver.lookup("incident"),
                    "source": "human",
                    "similarity": 1.0,
                }
            ],
        )
        self.assertEqual(self.store.effective(), pairs)
        self.assertEqual(self.table.fit_version(), version)
        self.embedder.embed.assert_called_once()
        self.evolver.answer("production outage", "reference", 0.1)
        corrected = lookup_details(self.evolver, "production outage", self.embedder)
        self.assertEqual(corrected["source"], "human")
        self.assertEqual(corrected["candidates"], [])
        self.assertLess(corrected["importance"], 50)
        self.embedder.embed.assert_called_once()

    def test_failure_does_not_write_fake_scores_and_cache_is_model_scoped(self):
        self.embedder.embed.side_effect = RuntimeError("provider failed")
        result = lookup_details(self.evolver, "new", self.embedder)
        self.assertEqual(result["embedding_error"], "RuntimeError")
        self.assertEqual(result["source"], "miss")
        self.assertIsNone(self.evolver.lookup("new"))
        self.embedder.embed.side_effect = lambda keys: [[1.0, 0.0] for _ in keys]
        lookup_details(self.evolver, "new", self.embedder)
        self.embedder.model = "another-model"
        lookup_details(self.evolver, "new", self.embedder)
        self.assertEqual(self.embedder.embed.call_count, 3)

    def test_embedding_http_response_indexes_and_invalid_vectors(self):
        adapter = OpenAIEmbeddings("text-embedding-3-small")
        adapter.api_key = "test-key"
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps(
            {
                "data": [
                    {"index": 1, "embedding": [0, 2]},
                    {"index": 0, "embedding": [3, 0]},
                ]
            }
        ).encode()
        with patch("task_evolver.semantic.urlopen", return_value=response) as request:
            self.assertEqual(adapter.embed(["a", "b"]), [[1.0, 0.0], [0.0, 1.0]])
            payload = json.loads(request.call_args.args[0].data)
            self.assertEqual(payload["input"], ["a", "b"])
            response.read.return_value = b'{"data":[{"index":0,"embedding":[0,0]}]}'
            with self.assertRaises(ValueError):
                adapter.embed(["a"])

    def test_waiting_impact_cooldown_and_graph_connectivity(self):
        question = select_question(
            self.evolver,
            ["old-miss", "live-miss"],
            {"live-miss": 50, "incident": 60},
            {},
            100,
        )
        self.assertEqual((question.first, question.second), ("live-miss", "incident"))
        self.assertIsNone(
            select_question(
                self.evolver,
                ["live-miss"],
                {"live-miss": 50, "incident": 60},
                {("incident", "live-miss"): 99},
                100,
            )
        )
        disconnected = select_question(
            self.evolver, ["new-a"], {"new-a": 50, "new-b": 50}, {}, 100
        )
        self.assertEqual(disconnected.second, "reference")
        self.evolver.answer(question.first, question.second, 0.8)
        self.assertIsNone(
            select_question(
                self.evolver,
                [question.first],
                {question.first: 50, question.second: 60},
                {},
                100,
            )
        )

    def test_expanded_exact_match_is_reviewed(self):
        self.expander.expand.side_effect = lambda key: (
            ["alias"] if key == "incident" else []
        )
        self.evolver.answer("incident", "reference", 0.9)
        self.assertEqual(lookup_details(self.evolver, "alias")["source"], "expanded")
        question = select_question(
            self.evolver, ["alias"], {"alias": 50, "reference": 50}, {}, 100
        )
        self.assertEqual((question.first, question.second), ("alias", "reference"))
        self.evolver.answer("alias", "reference", 0.2)
        self.assertEqual(lookup_details(self.evolver, "alias")["source"], "human")

    def test_worker_selects_competing_task_and_deduplicates(self):
        updated = threading.Event()
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "pairs.db"
            store, table = PairStore(db), ImportanceTable(db)
            TaskEvolver(store, table, self.expander, "reference").answer(
                "incident", "reference", 0.9
            )
            store.conn.close()
            table.conn.close()
            with (
                patch(
                    "task_evolver.learning.OpenAIExpander", return_value=self.expander
                ),
                patch("task_evolver.learning.lookup_details", return_value={}),
                patch("task_evolver.learning.ask_score", return_value=0.8) as ask,
                patch("builtins.print"),
            ):
                worker = LearningQueue(
                    db, "reference", Path(directory) / "scores.json", [], updated.set
                )
                worker.observe({"new": 50, "incident": 60})
                self.assertTrue(updated.wait(5))
                ask.assert_called_once_with("new", "incident")
                ask.side_effect = EOFError
                worker.request("stop-key")
                worker.thread.join(5)
                self.assertFalse(worker.thread.is_alive())

    def test_conflicting_human_comparisons_are_reviewable(self):
        self.evolver.answer("reference", "third", 0.9)
        self.evolver.answer("third", "incident", 0.9)
        question = select_question(
            self.evolver, ["incident"], {"incident": 50, "reference": 50}, {}, 100
        )
        self.assertEqual(question.reason, "human_model_disagreement")

    def test_cancel_during_embedding_suppresses_stale_question(self):
        entered, release, updated = (
            threading.Event(),
            threading.Event(),
            threading.Event(),
        )

        def lookup(*args):
            entered.set()
            if not release.wait(5):
                raise TimeoutError("test lookup timeout")
            return {}

        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "pairs.db"
            store, table = PairStore(db), ImportanceTable(db)
            TaskEvolver(store, table, self.expander, "reference").answer(
                "incident", "reference", 0.9
            )
            store.conn.close()
            table.conn.close()
            with (
                patch(
                    "task_evolver.learning.OpenAIExpander", return_value=self.expander
                ),
                patch("task_evolver.learning.lookup_details", side_effect=lookup),
                patch("task_evolver.learning.ask_score", side_effect=EOFError) as ask,
                patch("builtins.print"),
            ):
                worker = LearningQueue(
                    db, "reference", Path(directory) / "scores.json", [], updated.set
                )
                worker.observe({"cancelled": 50, "incident": 60})
                self.assertTrue(entered.wait(5))
                worker.observe({"incident": 60})
                release.set()
                self.assertTrue(updated.wait(5))
                ask.assert_not_called()
                worker.request("stop-key")
                worker.thread.join(5)
                self.assertFalse(worker.thread.is_alive())

    def test_question_budget_stops_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch(
                    "task_evolver.learning.OpenAIExpander", return_value=self.expander
                ),
                patch("task_evolver.learning.lookup_details", return_value={}),
                patch("task_evolver.learning.ask_score", return_value=0.8) as ask,
                patch("builtins.print"),
            ):
                worker = LearningQueue(
                    root / "pairs.db",
                    "reference",
                    root / "scores.json",
                    [],
                    lambda: None,
                )
                worker.remaining = 1
                worker.request("new")
                worker.thread.join(5)
                self.assertTrue(worker.closed)
                worker.request("another")
                ask.assert_called_once_with("new", "reference")


class QueueObservationTest(unittest.IsolatedAsyncioTestCase):
    async def test_queue_observation_tracks_cancellation_without_blocking_admission(
        self,
    ):
        observer = Mock()
        service = AdmissionService(on_queue=observer)
        service.bindings = [(Path("/").resolve(), "task")]
        server = await asyncio.start_server(service.handle, "127.0.0.1", 0)
        self.addAsyncCleanup(server.wait_closed)
        self.addCleanup(server.close)
        clients = []
        for key in ("holder", "waiter"):
            reader, writer = await asyncio.open_connection(
                "127.0.0.1", server.sockets[0].getsockname()[1]
            )
            self.addCleanup(writer.close)
            clients.append((reader, writer))
            writer.write(
                (
                    json.dumps(
                        {
                            "op": "enqueue",
                            "client_id": key,
                            "thread_id": "t",
                            "turn_id": "t",
                            "call_id": "c",
                            "cwd": "/",
                            "tool": "test",
                        }
                    )
                    + "\n"
                ).encode()
            )
            await writer.drain()
            self.assertEqual(json.loads(await reader.readline())["status"], "queued")
        self.assertIn("task", observer.call_args.args[0])
        reader, writer = clients[1]
        writer.write(b'{"op":"cancel"}\n')
        await writer.drain()
        self.assertEqual(json.loads(await reader.readline())["status"], "released")
        self.assertEqual(observer.call_args.args[0], {})
