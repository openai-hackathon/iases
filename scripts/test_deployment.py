import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.request import urlopen

from deploy.render_router import render

ROOT = Path(__file__).resolve().parents[1]


class DeploymentTest(unittest.TestCase):
    def test_router_config_requires_models_and_quotes_values(self):
        with self.assertRaisesRegex(ValueError, "FAST_MODEL"):
            render("${FAST_MODEL}", {})
        with self.assertRaisesRegex(ValueError, "ANALYSIS_MODEL"):
            render("${FAST_MODEL}", {"FAST_MODEL": "fast"})
        models = {"FAST_MODEL": 'fast"\nmodel', "ANALYSIS_MODEL": "strong"}
        rendered = render("[${FAST_MODEL}, ${ANALYSIS_MODEL}]", models)
        self.assertEqual(json.loads(rendered), list(models.values()))

    def test_router_template_matches_container_catalog(self):
        template = (ROOT / "src/model-router/gateway/config.yaml").read_text()
        rendered = render(template, {"FAST_MODEL": "fast", "ANALYSIS_MODEL": "strong"})
        self.assertIn("default_model: incident-analysis", rendered)
        self.assertIn(
            "modelCards:\n    - name: incident-fast\n    - name: incident-analysis",
            rendered,
        )
        self.assertNotIn("response_cache:", rendered)
        self.assertNotIn("${", rendered)

    def test_container_bind_addresses_serve_real_requests(self):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src/task-evolver")
        environment["OPENAI_API_KEY"] = "deployment-test-key"
        for service in ("scheduler", "gateway"):
            with self.subTest(service=service):
                with socket.socket() as reservation:
                    reservation.bind(("127.0.0.1", 0))
                    port = reservation.getsockname()[1]
                command = (
                    [sys.executable, "-m", "task_evolver.admission"]
                    if service == "scheduler"
                    else [
                        sys.executable,
                        str(ROOT / "src/model-router/gateway/gateway.py"),
                    ]
                )
                process = subprocess.Popen(
                    command + ["--host", "0.0.0.0", "--port", str(port)],
                    env=environment,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                try:
                    deadline = time.monotonic() + 10
                    while True:
                        try:
                            connection = socket.create_connection(
                                ("127.0.0.1", port), timeout=1
                            )
                            connection.close()
                            break
                        except OSError:
                            if (
                                process.poll() is not None
                                or time.monotonic() >= deadline
                            ):
                                self.fail(f"{service} did not start")
                            time.sleep(0.05)
                    if service == "gateway":
                        with urlopen(
                            f"http://127.0.0.1:{port}/healthz", timeout=2
                        ) as response:
                            self.assertEqual(json.load(response), {"status": "ok"})
                    else:
                        with socket.create_connection(
                            ("127.0.0.1", port), timeout=2
                        ) as client:
                            stream = client.makefile("rb")
                            with stream:
                                request = dict(
                                    op="enqueue",
                                    client_id="test",
                                    thread_id="thread",
                                    turn_id="turn",
                                    call_id="call",
                                    cwd="/workspace/incident",
                                    tool="test",
                                )
                                client.sendall(json.dumps(request).encode() + b"\n")
                                self.assertEqual(
                                    [
                                        json.loads(stream.readline()),
                                        json.loads(stream.readline()),
                                    ],
                                    [{"status": "queued"}, {"status": "granted"}],
                                )
                                client.sendall(b'{"op":"release"}\n')
                                self.assertEqual(
                                    json.loads(stream.readline()),
                                    {"status": "released"},
                                )
                finally:
                    process.terminate()
                    try:
                        process.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate(timeout=5)
