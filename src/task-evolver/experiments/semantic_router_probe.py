import argparse
import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

from experiments.app_server_demo import Client


async def collect(client):
    report = {"status": "pending", "tool_completed": False, "final_text": ""}
    while True:
        event = await client.events.get()
        params = event.get("params", {})
        if event.get("method") == "item/completed":
            item = params.get("item", {})
            if item.get("type") == "commandExecution":
                report["tool_completed"] |= (
                    item.get("status") == "completed"
                    and item.get("exitCode") == 0
                    and "semantic-router-tool-ok"
                    in (item.get("aggregatedOutput") or "")
                )
            if item.get("type") == "agentMessage":
                report["final_text"] = item.get("text", "")
        if event.get("method") == "turn/completed":
            report["status"] = params["turn"]["status"]
            if params["turn"].get("error"):
                report["error"] = str(params["turn"]["error"])[:2000]
            report["passed"] = (
                report["status"] == "completed"
                and report["tool_completed"]
                and report["final_text"].strip() == "semantic-router-confirmed"
            )
            return report


async def run(
    binary, base_url, model, output, timeout=180, api_key_env=None, *, task_key=None
):
    started = time.monotonic()
    report = {
        "status": "failed",
        "passed": False,
        "tool_completed": False,
        "final_text": "",
    }
    secret = os.environ.get(api_key_env, "") if api_key_env else ""
    client = None
    with tempfile.TemporaryDirectory(
        prefix="semantic-router-probe-", ignore_cleanup_errors=True
    ) as directory:
        root = Path(directory)
        home = root / "home"
        work = root / "work"
        home.mkdir()
        work.mkdir()
        config = [
            f"model = {json.dumps(model)}",
            'model_provider = "semantic_router"',
            'approval_policy = "never"',
            'sandbox_mode = "danger-full-access"',
            "[features]",
            "code_mode = false",
            "unified_exec = false",
            "[model_providers.semantic_router]",
            'name = "Semantic Router"',
            f"base_url = {json.dumps(base_url)}",
            'wire_api = "responses"',
            "requires_openai_auth = false",
            "supports_websockets = false",
        ]
        if api_key_env:
            config.append(f"env_key = {json.dumps(api_key_env)}")
        if task_key:
            config.append(
                'http_headers = { "X-Incident-Task-Key" = '
                + json.dumps(quote(task_key, safe=""))
                + " }"
            )
        (home / "config.toml").write_text("\n".join(config) + "\n")
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("CODEX_SCHEDULER_")
        }
        env["CODEX_HOME"] = str(home)
        try:
            async with asyncio.timeout(timeout):
                if api_key_env and not secret:
                    raise ValueError("The API key environment variable is empty")
                process = await asyncio.create_subprocess_exec(
                    str(binary.resolve()),
                    "app-server",
                    "--listen",
                    "stdio://",
                    cwd=work,
                    env=env,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                    limit=2**24,
                )
                client = Client(process)
                await client.rpc(
                    "initialize",
                    {
                        "clientInfo": {"name": "semantic-router-probe", "version": "1"},
                        "capabilities": {"experimentalApi": True},
                    },
                )
                process.stdin.write(b'{"method":"initialized"}\n')
                thread = await client.rpc(
                    "thread/start",
                    {
                        "cwd": str(work),
                        "model": model,
                        "modelProvider": "semantic_router",
                        "approvalPolicy": "never",
                        "sandbox": "danger-full-access",
                    },
                )
                await client.rpc(
                    "turn/start",
                    {
                        "threadId": thread["thread"]["id"],
                        "input": [
                            {
                                "type": "text",
                                "text_elements": [],
                                "text": (
                                    "Run exactly one harmless local shell command: "
                                    "printf 'semantic-router-tool-ok\\n'. "
                                    "Do not read or change files. Do not use the network. "
                                    "After the tool succeeds, reply with exactly semantic-router-confirmed."
                                ),
                            }
                        ],
                    },
                )
                report = await collect(client)
        except Exception as error:
            report["error_type"] = type(error).__name__
        finally:
            if client is not None:
                try:
                    await asyncio.wait_for(client.close(), 5)
                except (TimeoutError, ProcessLookupError, BrokenPipeError):
                    if client.process.returncode is None:
                        client.process.terminate()
                        await client.process.wait()
                    client.reader.cancel()
                    await asyncio.gather(client.reader, return_exceptions=True)
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    report["transport"] = "responses-sse"
    if secret:
        report["final_text"] = report["final_text"].replace(secret, "[redacted]")
    report["final_text"] = report["final_text"][:2000]
    serialized = json.dumps(report, indent=2)
    if secret:
        serialized = serialized.replace(secret, "[redacted]")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(serialized + "\n")
    print(serialized)
    return report["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--binary", type=Path, default=Path("codex-rs/target/debug/codex")
    )
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-key-env")
    parser.add_argument("--task-key")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    passed = asyncio.run(
        run(
            args.binary,
            args.base_url,
            args.model,
            args.output,
            args.timeout,
            args.api_key_env,
            task_key=args.task_key,
        )
    )
    raise SystemExit(0 if passed else 1)
