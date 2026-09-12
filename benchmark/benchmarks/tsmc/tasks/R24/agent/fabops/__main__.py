"""Run a deterministic synthetic manufacturing request."""
import argparse
import json
from pathlib import Path
from .domain import run

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    request = json.loads(Path(args.input).read_text())
    print(json.dumps(run(request), sort_keys=True, allow_nan=False))

if __name__ == "__main__":
    main()
