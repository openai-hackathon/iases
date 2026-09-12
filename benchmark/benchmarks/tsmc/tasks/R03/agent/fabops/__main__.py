import argparse, json
from pathlib import Path
from .service import run
def main():
    parser=argparse.ArgumentParser(description="Replay a synthetic factory issue")
    parser.add_argument("--input",required=True)
    args=parser.parse_args()
    with Path(args.input).open(encoding="utf-8") as f:
        payload=json.load(f)
    print(json.dumps(run(payload),ensure_ascii=False,sort_keys=True,allow_nan=False))
if __name__ == "__main__": main()
