import tempfile
from pathlib import Path
from .planner import plan
from .store import commit

def run(request):
    rows = plan(request)
    with tempfile.TemporaryDirectory() as directory:
        status, published = commit(Path(directory) / "dispatch.sqlite", request, rows)
    return dict(plan=rows, status=status, reservations=published)
