import http.client
import importlib.util
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

from task_evolver.admission import AdmissionService
from task_evolver.table import ImportanceTable


SPEC = importlib.util.spec_from_file_location(
    "semantic_gateway",
    Path(__file__).resolve().parents[2] / "semantic-router" / "gateway.py",
)
gateway = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gateway)


class SemanticGatewayTest(unittest.TestCase):
    def setUp(self):
        self.classifications = []
        self.requests = []
        self.classifier_status = 200
        self.recommendation = "incident-fast"
        self.signal_errors = []
        self.release = threading.Event()
        self.addCleanup(self.release.set)
        owner = self

        class Backend(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                payload = json.loads(
                    self.rfile.read(int(self.headers["Content-Length"]))
                )
                if self.server.classifier:
                    owner.classifications.append((self.path, payload))
                    result = {
                        "recommended_model": owner.recommendation,
                        "routing_decision": "incident-summary",
                        "signal_errors": owner.signal_errors,
                    }
                    status = owner.classifier_status
                else:
                    owner.requests.append((self.path, dict(self.headers), payload))
                    if payload.get("stream"):
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.end_headers()
                        self.wfile.write(b"data: first\n\n")
                        self.wfile.flush()
                        owner.release.wait(3)
                        self.wfile.write(b"data: second\n\n")
                        self.wfile.flush()
                        return
                    result = {"id": "resp_test", "output": []}
                    status = 200
                body = json.dumps(result).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        classifier = self.start(ThreadingHTTPServer(("127.0.0.1", 0), Backend))
        classifier.classifier = True
        upstream = self.start(ThreadingHTTPServer(("127.0.0.1", 0), Backend))
        upstream.classifier = False
        self.server = self.start(
            gateway.GatewayServer(
                ("127.0.0.1", 0),
                f"http://127.0.0.1:{classifier.server_port}",
                f"http://127.0.0.1:{upstream.server_port}/v1",
                {"incident-fast": "gpt-fast", "incident-analysis": "gpt-analysis"},
                "test-upstream-key",
            )
        )

    def start(self, server):
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def request(self, payload, headers=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=2
        )
        self.addCleanup(connection.close)
        connection.request(
            "POST",
            "/v1/responses",
            json.dumps(payload),
            {"Content-Type": "application/json", **(headers or {})},
        )
        return connection.getresponse()

    def test_preserves_responses_payload_and_routes_latest_user(self):
        payload = {
            "model": "incident-auto",
            "store": False,
            "input": [
                {"role": "user", "content": "Old request"},
                {"type": "reasoning", "encrypted_content": "opaque-reasoning"},
                {"role": "assistant", "phase": "commentary", "content": "Working"},
                {
                    "type": "custom_tool_call",
                    "call_id": "call_1",
                    "name": "shell",
                    "input": "uptime",
                },
                {
                    "type": "custom_tool_call_output",
                    "call_id": "call_1",
                    "output": "healthy",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Summarize this incident"}
                    ],
                },
            ],
            "tools": [{"type": "custom", "name": "shell", "format": {"type": "text"}}],
            "include": ["reasoning.encrypted_content"],
        }
        response = self.request(payload)
        self.assertEqual(
            (response.status, json.loads(response.read())),
            (200, {"id": "resp_test", "output": []}),
        )
        path, headers, forwarded = self.requests[0]
        self.assertEqual(path, "/v1/responses")
        self.assertEqual(headers.get("Authorization"), "Bearer test-upstream-key")
        self.assertEqual(forwarded, {**payload, "model": "gpt-fast"})
        self.assertEqual(
            self.classifications,
            [
                (
                    "/api/v1/classify/intent",
                    {"model": "incident-auto", "text": "Summarize this incident"},
                )
            ],
        )

    def test_streams_first_chunk_before_upstream_finishes(self):
        response = self.request(
            {"model": "incident-auto", "input": "Summarize incident", "stream": True}
        )
        try:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.read(len(b"data: first\n\n")), b"data: first\n\n")
            self.assertFalse(self.release.is_set())
            self.release.set()
            self.assertEqual(response.read(), b"data: second\n\n")
        finally:
            self.release.set()

    def test_classifier_failure_never_calls_upstream(self):
        self.classifier_status = 503
        response = self.request({"model": "incident-auto", "input": "Diagnose outage"})
        self.assertEqual(response.status, 503)
        response.read()
        self.assertEqual(self.requests, [])

    def test_unknown_recommended_model_never_calls_upstream(self):
        self.recommendation = "unapproved-model"
        response = self.request({"model": "incident-auto", "input": "Diagnose outage"})
        self.assertEqual(response.status, 503)
        response.read()
        self.assertEqual(self.requests, [])

    def test_rejects_server_stored_context(self):
        response = self.request(
            {
                "model": "incident-auto",
                "input": "Continue",
                "previous_response_id": "resp_old",
            }
        )
        self.assertEqual(response.status, 400)
        response.read()
        self.assertEqual((self.classifications, self.requests), ([], []))

    def test_rejects_oversized_body_before_reading_it(self):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=2
        )
        self.addCleanup(connection.close)
        connection.putrequest("POST", "/v1/responses")
        connection.putheader("Content-Length", str(gateway.MAX_BODY + 1))
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 413)
        response.read()
        self.assertEqual((self.classifications, self.requests), ([], []))

    def test_signal_failure_never_calls_upstream(self):
        self.signal_errors = ["embedding service unavailable"]
        response = self.request({"model": "incident-auto", "input": "Diagnose outage"})
        self.assertEqual(response.status, 503)
        response.read()
        self.assertEqual(self.requests, [])

    def test_rejects_invalid_routing_input(self):
        for payload in [
            {"model": "gpt-direct", "input": "Bypass routing"},
            {
                "model": "incident-auto",
                "input": [{"role": "assistant", "content": "No user"}],
            },
            {"model": "incident-auto", "input": "x" * (gateway.MAX_TEXT + 1)},
        ]:
            with self.subTest(payload_type=type(payload["input"]).__name__):
                response = self.request(payload)
                self.assertEqual(response.status, 400)
                response.read()
        self.assertEqual((self.classifications, self.requests), ([], []))

    def importance_table(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "importance.json"
        table = ImportanceTable(snapshot_path=path)
        self.addCleanup(table.conn.close)
        self.server.importance = AdmissionService(snapshot=path)
        return table, path

    def test_importance_promotes_fast_without_demoting_analysis(self):
        table, _ = self.importance_table()
        table.update({"critical": 80, "routine": 20, "晶圓事件": 90})
        payload = {
            "model": "incident-auto",
            "input": "Summarize incident",
            "store": False,
        }
        for semantic, key, expected, reason, score in [
            (
                "incident-fast",
                "critical",
                "incident-analysis",
                "high-task-importance",
                80,
            ),
            (
                "incident-fast",
                "晶圓事件",
                "incident-analysis",
                "high-task-importance",
                90,
            ),
            ("incident-fast", "routine", "incident-fast", "semantic", 20),
            ("incident-fast", "unknown", "incident-fast", "semantic", None),
            ("incident-fast", None, "incident-fast", "semantic", None),
            ("incident-analysis", "routine", "incident-analysis", "semantic", 20),
        ]:
            with self.subTest(semantic=semantic, key=key):
                self.recommendation = semantic
                headers = {"X-Incident-Importance": "100"}
                if key is not None:
                    headers["X-Incident-Task-Key"] = quote(key, safe="")
                response = self.request(payload, headers)
                self.assertEqual(response.status, 200)
                self.assertEqual(response.getheader("x-vsr-selected-model"), semantic)
                self.assertEqual(
                    response.getheader("x-incident-selected-model"), expected
                )
                self.assertEqual(
                    response.getheader("x-incident-routing-reason"), reason
                )
                value = response.getheader("x-incident-importance")
                self.assertEqual(float(value) if value is not None else None, score)
                if score is not None:
                    self.assertEqual(response.getheader("x-incident-fit-version"), "1")
                response.read()
                _, sent_headers, forwarded = self.requests[-1]
                self.assertEqual(
                    forwarded, {**payload, "model": self.server.models[expected]}
                )
                self.assertNotIn(
                    "x-incident-task-key", {name.lower() for name in sent_headers}
                )
                self.assertNotIn(
                    "x-incident-importance", {name.lower() for name in sent_headers}
                )

    def test_importance_hot_reload_keeps_last_good_snapshot(self):
        table, path = self.importance_table()
        table.update({"incident": 20})
        original = path.read_text()
        payload = {"model": "incident-auto", "input": "Summarize incident"}
        headers = {"X-Incident-Task-Key": "incident"}
        response = self.request(payload, headers)
        self.assertEqual(
            response.getheader("x-incident-selected-model"), "incident-fast"
        )
        self.assertEqual(response.getheader("x-incident-fit-version"), "1")
        response.read()
        table.update({"incident": 95})
        current = path.read_text()
        for name, snapshot in [
            ("newer", current),
            ("older", original),
            ("corrupt", "{"),
        ]:
            with self.subTest(snapshot=name):
                path.write_text(snapshot)
                response = self.request(payload, headers)
                self.assertEqual(response.status, 200)
                self.assertEqual(
                    response.getheader("x-incident-selected-model"), "incident-analysis"
                )
                self.assertEqual(response.getheader("x-incident-fit-version"), "2")
                self.assertEqual(float(response.getheader("x-incident-importance")), 95)
                response.read()
                self.assertEqual(
                    self.requests[-1][2], {**payload, "model": "gpt-analysis"}
                )

    def test_constructor_snapshot_and_custom_threshold(self):
        table, path = self.importance_table()
        endpoints = (
            self.server.classifier_url,
            self.server.upstream_url,
            self.server.models,
            self.server.api_key,
        )
        with self.assertRaisesRegex(ValueError, "valid importance snapshot"):
            gateway.GatewayServer(
                self.server.server_address,
                *endpoints,
                importance_snapshot=path,
            )
        table.update({"incident": 90})
        self.server = self.start(
            gateway.GatewayServer(
                ("127.0.0.1", 0),
                *endpoints,
                importance_snapshot=path,
                importance_threshold=95,
            )
        )
        for score, expected in [(90, "incident-fast"), (96, "incident-analysis")]:
            with self.subTest(score=score):
                if score == 96:
                    table.update({"incident": score})
                response = self.request(
                    {"model": "incident-auto", "input": "Summarize incident"},
                    {"X-Incident-Task-Key": "incident"},
                )
                self.assertEqual(response.status, 200)
                self.assertEqual(
                    response.getheader("x-incident-selected-model"), expected
                )
                self.assertEqual(
                    float(response.getheader("x-incident-importance")), score
                )
                response.read()
                self.assertEqual(
                    self.requests[-1][2]["model"], self.server.models[expected]
                )
