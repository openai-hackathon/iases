import argparse
import json
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote
from urllib.request import Request, urlopen

from task_evolver.admission import AdmissionService
from task_evolver.expansion import config_value


MAX_BODY = 8 * 1024 * 1024
MAX_TEXT = 16384


def latest_user_text(payload):
    if payload.get("previous_response_id"):
        raise ValueError("Send full input history; previous_response_id is unsupported")
    items = payload.get("input")
    if isinstance(items, str):
        text = items
    elif isinstance(items, list):
        text = ""
        for item in reversed(items):
            if not isinstance(item, dict) or item.get("role") != "user":
                continue
            content = item.get("content")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = "\n".join(
                    part["text"]
                    for part in content
                    if isinstance(part, dict)
                    and part.get("type") in ("input_text", "text")
                    and isinstance(part.get("text"), str)
                )
            break
    else:
        raise ValueError("input must be text or a list of Responses input items")
    if not text.strip():
        raise ValueError(
            "The latest user message must contain text for semantic routing"
        )
    if len(text) > MAX_TEXT:
        raise ValueError(f"The latest user message exceeds {MAX_TEXT} characters")
    return text


class GatewayServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address,
        classifier_url,
        upstream_url,
        models,
        api_key,
        *,
        importance_snapshot=None,
        importance_threshold=80,
    ):
        self.classifier_url = classifier_url.rstrip("/")
        self.upstream_url = upstream_url.rstrip("/")
        self.models = dict(models)
        self.api_key = api_key
        if not 0 <= importance_threshold <= 100:
            raise ValueError("importance threshold must be between 0 and 100")
        self.importance_threshold = importance_threshold
        self.importance_lock = threading.Lock()
        self.importance = None
        if importance_snapshot is not None:
            self.importance = AdmissionService(snapshot=importance_snapshot)
            self.importance.refresh()
            if self.importance.version < 0:
                raise ValueError("A valid importance snapshot is required")
        super().__init__(address, GatewayHandler)


class GatewayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(300)

    def error(self, status, message):
        body = json.dumps({"error": {"message": message}}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def do_GET(self):
        if self.path != "/healthz":
            self.error(404, "Endpoint not found")
            return
        body = b'{"status":"ok"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        started = time.monotonic()
        selected = decision = ""
        importance = fit_version = None
        reason = "semantic"
        status = 400
        sent_headers = False
        try:
            if self.path != "/v1/responses":
                status = 404
                self.error(status, "Endpoint not found")
                return
            if self.headers.get("Transfer-Encoding"):
                raise ValueError(
                    "Send a Content-Length header without Transfer-Encoding"
                )
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                status = 413
                self.error(status, f"Request body must contain 1 to {MAX_BODY} bytes")
                return
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("Request body is incomplete")
            payload = json.loads(raw)
            if not isinstance(payload, dict) or payload.get("model") != "incident-auto":
                raise ValueError("model must be incident-auto")
            text = latest_user_text(payload)
            request = Request(
                self.server.classifier_url + "/api/v1/classify/intent",
                data=json.dumps({"model": "incident-auto", "text": text}).encode(),
                headers={"Content-Type": "application/json"},
            )
            try:
                with urlopen(request, timeout=30) as response:
                    result = json.loads(response.read(65537))
                alias = result["recommended_model"]
                decision = result["routing_decision"]
                selected = self.server.models[alias]
                if (
                    not isinstance(decision, str)
                    or not decision
                    or len(decision) > 128
                    or any(ord(char) < 32 or ord(char) > 126 for char in decision)
                    or result.get("signal_errors")
                ):
                    raise ValueError("Invalid classification result")
            except (OSError, ValueError, KeyError, TypeError) as error:
                if isinstance(error, HTTPError):
                    error.close()
                status = 503
                self.error(status, "Semantic classification is unavailable")
                return
            final_alias = alias
            task_key = self.headers.get("X-Incident-Task-Key")
            if task_key is not None:
                task_key = unquote(task_key, errors="strict")
            if self.server.importance is not None:
                with self.server.importance_lock:
                    self.server.importance.refresh()
                    importance = self.server.importance.scores.get(task_key)
                    fit_version = self.server.importance.version
                if (
                    importance is not None
                    and importance >= self.server.importance_threshold
                ):
                    final_alias = "incident-analysis"
                    selected = self.server.models[final_alias]
                    reason = "high-task-importance"
            payload["model"] = selected
            request = Request(
                self.server.upstream_url + "/responses",
                data=json.dumps(payload, ensure_ascii=False).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.server.api_key,
                },
            )
            try:
                response = urlopen(request, timeout=300)
            except HTTPError as error:
                response = error
            with response:
                status = response.status
                self.send_response(status)
                self.send_header(
                    "Content-Type",
                    response.headers.get("Content-Type", "application/json"),
                )
                self.send_header("x-vsr-selected-model", alias)
                self.send_header("x-vsr-selected-decision", decision)
                self.send_header("x-incident-upstream-model", selected)
                self.send_header("x-incident-selected-model", final_alias)
                self.send_header("x-incident-routing-reason", reason)
                if importance is not None:
                    self.send_header("x-incident-importance", str(importance))
                if fit_version is not None:
                    self.send_header("x-incident-fit-version", str(fit_version))
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                sent_headers = True
                self.close_connection = True
                while chunk := response.read1(65536):
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except (ValueError, UnicodeError) as error:
            if not sent_headers:
                self.error(
                    400,
                    str(error)
                    if not isinstance(error, json.JSONDecodeError)
                    else "Invalid JSON",
                )
        except (OSError, URLError):
            status = 502
            if not sent_headers:
                self.error(status, "Upstream request failed")
            self.close_connection = True
        finally:
            print(
                json.dumps(
                    {
                        "decision": decision,
                        "model": selected,
                        "importance": importance,
                        "fit_version": fit_version,
                        "routing_reason": reason,
                        "status": status,
                        "duration_ms": round((time.monotonic() - started) * 1000),
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18899)
    parser.add_argument("--classifier-url", default="http://127.0.0.1:18080")
    parser.add_argument("--fast-model", default="gpt-5.6-luna")
    parser.add_argument("--analysis-model", default="gpt-5.6-sol")
    parser.add_argument("--importance-snapshot", type=Path)
    parser.add_argument("--importance-threshold", type=float, default=80)
    args = parser.parse_args()
    key = config_value("OPENAI_API_KEY", Path(__file__).resolve().parents[2] / ".env")
    if not key:
        parser.error("Set OPENAI_API_KEY in the environment or repository .env")
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    with GatewayServer(
        (args.host, args.port),
        args.classifier_url,
        "https://api.openai.com/v1",
        {"incident-fast": args.fast_model, "incident-analysis": args.analysis_model},
        key,
        importance_snapshot=args.importance_snapshot,
        importance_threshold=args.importance_threshold,
    ) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
