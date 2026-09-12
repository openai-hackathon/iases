import sqlite3
def migrate(connection, fail):
    connection.execute("BEGIN")
    try:
        connection.execute("ALTER TABLE measurements ADD COLUMN unit TEXT")
        if fail:
            raise RuntimeError("injected interruption")
        connection.execute("UPDATE measurements SET unit = 'Pa'")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
def run(request):
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE measurements (value INTEGER)")
        connection.executemany("INSERT INTO measurements VALUES (?)", [(v,) for v in request["values"]])
        connection.commit()
        try:
            migrate(connection, request["fail"])
        except RuntimeError:
            if request["retry"]:
                migrate(connection, False)
        columns = [r[1] for r in connection.execute("PRAGMA table_info(measurements)")]
        rows = [list(r) for r in connection.execute("SELECT * FROM measurements ORDER BY rowid")]
        return dict(columns=columns, rows=rows)
    finally:
        connection.close()
