import tempfile
from pathlib import Path
from .stream import initial, accept
from .snapshot import materialize
from .checkpoint import connect, load, save

def run(request):
    states = {source: initial() for source in request["sources"]}
    published, results = None, []
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "snapshots.sqlite"
        db = connect(path)
        try:
            save(db, states, published)
            for command in request["commands"]:
                if command["op"] == "restart":
                    db.close()
                    db = connect(path)
                    states, published = load(db)
                    results.append("restarted")
                    continue
                candidate, next_published = dict(states), published
                if command["op"] == "page":
                    source = command["source"]
                    result, candidate[source] = accept(states[source], command)
                else:
                    snapshot = materialize(states)
                    result = "blocked" if snapshot is None else "published"
                    if snapshot is not None:
                        next_published = snapshot
                if result in {"accepted", "published"}:
                    try:
                        save(db, candidate, next_published, command.get("crash", False))
                        states, published = candidate, next_published
                    except RuntimeError:
                        result = "crashed"
                results.append(result)
            frontiers = {source: [state["epoch"], state["next"], state["watermark"]] for source, state in states.items()}
            return dict(results=results, snapshot=published, frontiers=frontiers)
        finally:
            db.close()
