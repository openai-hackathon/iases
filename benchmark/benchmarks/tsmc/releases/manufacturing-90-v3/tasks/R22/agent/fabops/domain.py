import tempfile
from pathlib import Path
from .store import connect
from .lease import execute
def run(request):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "lease.sqlite"
        connection = connect(path)
        results = []
        try:
            for command in request["commands"]:
                if command["op"] == "restart":
                    connection.close()
                    connection = connect(path)
                    results.append(None)
                else:
                    results.append(execute(connection, command))
            value = connection.execute("SELECT value FROM output WHERE id=1").fetchone()[0]
            epoch = connection.execute("SELECT value FROM epoch WHERE id=1").fetchone()[0]
            return dict(results=results, value=value, epoch=epoch)
        finally:
            connection.close()
