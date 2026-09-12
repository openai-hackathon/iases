import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from task_evolver.expansion import config_value


ROUTER_REVISION = "a08a982388f83d4daabb3e6a3c40240bd0a96238"


def run(args):
    project = Path(__file__).resolve().parents[2]
    templates = Path(__file__).resolve().parent
    source = args.router_root.resolve()
    snapshot_revision = source / "UPSTREAM_REVISION"
    if snapshot_revision.is_file():
        revision = snapshot_revision.read_text().strip()
    else:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=source,
            text=True,
        ).strip()
    if revision != ROUTER_REVISION:
        raise ValueError(f"Use Semantic Router commit {ROUTER_REVISION}")
    runtime = args.runtime.resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    key = config_value("OPENAI_API_KEY", project / ".env")
    if not key:
        raise ValueError("Set OPENAI_API_KEY in the environment or repository .env")
    env["OPENAI_API_KEY"] = key
    libraries = [
        str(source / part / "target/release")
        for part in (
            "candle-binding",
            "ml-binding",
            "nlp-binding",
        )
    ]
    env["CGO_ENABLED"] = "1"
    env["CGO_LDFLAGS"] = " ".join("-L" + path for path in libraries)
    env["LD_LIBRARY_PATH"] = os.pathsep.join(libraries)
    env["DYLD_LIBRARY_PATH"] = os.pathsep.join(libraries)
    binary = args.binary.resolve() if args.binary else runtime / "router"
    if not args.binary:
        subprocess.run(
            ["go", "build", "-tags=milvus", "-o", str(binary), "./cmd"],
            cwd=source / "src/semantic-router",
            env=env,
            check=True,
        )
    config = (templates / "config.yaml").read_text()
    for name, value in {
        "FAST_MODEL": args.fast_model,
        "ANALYSIS_MODEL": args.analysis_model,
    }.items():
        config = config.replace("${" + name + "}", json.dumps(value))
    (runtime / "config.yaml").write_text(config)
    for port in (18899, 50061, 18080, 19190):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    processes = []
    try:
        with (runtime / "router.log").open("w") as router_log:
            router = subprocess.Popen(
                [
                    str(binary),
                    "-config",
                    str(runtime / "config.yaml"),
                    "-port",
                    "50061",
                    "-api-port",
                    "18080",
                    "-api-bind",
                    "127.0.0.1",
                    "-metrics-port",
                    "19190",
                ],
                cwd=source,
                env=env,
                stdout=router_log,
                stderr=subprocess.STDOUT,
            )
        processes.append(router)
        until = time.monotonic() + 180
        while True:
            if router.poll() is not None:
                raise RuntimeError(f"Router exited; inspect {runtime / 'router.log'}")
            try:
                with urlopen("http://127.0.0.1:18080/health", timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                pass
            if time.monotonic() >= until:
                raise TimeoutError(
                    f"Router did not start; inspect {runtime / 'router.log'}"
                )
            time.sleep(0.5)
        with (runtime / "gateway.log").open("w") as gateway_log:
            gateway = subprocess.Popen(
                [
                    sys.executable,
                    str(templates / "gateway.py"),
                    "--fast-model",
                    args.fast_model,
                    "--analysis-model",
                    args.analysis_model,
                    "--importance-threshold",
                    str(args.importance_threshold),
                    *(
                        [
                            "--importance-snapshot",
                            str(args.importance_snapshot.resolve()),
                        ]
                        if args.importance_snapshot
                        else []
                    ),
                ],
                cwd=project,
                env=env,
                stdout=gateway_log,
                stderr=subprocess.STDOUT,
            )
        processes.append(gateway)
        until = time.monotonic() + 180
        while True:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError(f"Service exited; inspect logs in {runtime}")
            try:
                with socket.create_connection(("127.0.0.1", 18899), timeout=1):
                    break
            except OSError:
                if time.monotonic() >= until:
                    raise TimeoutError("Gateway did not start")
                time.sleep(0.5)
        print(
            json.dumps(
                {
                    "base_url": "http://127.0.0.1:18899/v1",
                    "model": "incident-auto",
                    "fast_model": args.fast_model,
                    "analysis_model": args.analysis_model,
                    "logs": str(runtime),
                }
            ),
            flush=True,
        )
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        raise RuntimeError(f"Service exited; inspect logs in {runtime}")
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--router-root", type=Path, required=True)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--runtime", type=Path, default=Path(".cache/semantic-router"))
    parser.add_argument("--fast-model", default="gpt-5.6-luna")
    parser.add_argument("--analysis-model", default="gpt-5.6-sol")
    parser.add_argument("--importance-snapshot", type=Path)
    parser.add_argument("--importance-threshold", type=float, default=80)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        run(args)
    except KeyboardInterrupt:
        pass
