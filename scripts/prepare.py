import argparse
import json
import shutil
import subprocess
from pathlib import Path


def prepare(root, destination):
    sources = json.loads((root / "integrations/sources.json").read_text())
    destination.mkdir(parents=True, exist_ok=False)
    for name, source in sources.items():
        checkout = destination / name
        subprocess.run(["git", "init", str(checkout)], check=True)
        subprocess.run(
            ["git", "fetch", "--depth=1", source["url"], source["revision"]],
            cwd=checkout,
            check=True,
        )
        subprocess.run(
            ["git", "checkout", "--detach", "FETCH_HEAD"], cwd=checkout, check=True
        )
        patch = root / "integrations" / name / "changes.patch"
        subprocess.run(
            ["git", "apply", "--check", str(patch)], cwd=checkout, check=True
        )
        subprocess.run(["git", "apply", str(patch)], cwd=checkout, check=True)
        for origin, target in source["copies"].items():
            shutil.copytree(
                root / origin,
                checkout / target,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
    shutil.copytree(
        root / "src/model-router/research", destination / "icr-router/experiments"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    prepare(root, args.destination.resolve() if args.destination else root / ".work")
