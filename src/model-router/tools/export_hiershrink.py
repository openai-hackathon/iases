import argparse
import json
from pathlib import Path

import numpy as np


def export(source, destination, encoder, model_map):
    with np.load(source, allow_pickle=False) as data:
        models = [model_map[name] for name in data["models"].tolist()]
        if (
            not models
            or len(set(models)) != len(models)
            or not all(isinstance(name, str) and name for name in models)
        ):
            raise ValueError("Map each artifact model to a unique backend ID")
        artifact = {
            "version": 1,
            "encoder": encoder,
            "models": models,
            "layers": [
                {
                    "weights": data[f"w{index}"].tolist(),
                    "bias": data[f"b{index}"].tolist(),
                }
                for index in range(3)
            ],
            **{
                name: data[name].tolist()
                for name in ["profile", "offset", "table", "centers", "costs"]
            },
        }
    payload = json.dumps(artifact, allow_nan=False, separators=(",", ":"))
    with Path(destination).open("x") as output:
        output.write(payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--encoder", required=True)
    parser.add_argument("--model-map", required=True)
    args = parser.parse_args()
    export(
        args.source,
        args.destination,
        args.encoder,
        json.loads(Path(args.model_map).read_text()),
    )
