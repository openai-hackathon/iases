def run(request):
    cursor = request["cursor"]
    rows = sorted(request["rows"], key=lambda r: (r["time"], r["id"]))
    rows = [r for r in rows if cursor is None or (r["time"], r["id"]) >= tuple(cursor)]
    page = rows[:request["limit"]]
    return dict(rows=page, next_cursor=[page[-1]["time"], page[-1]["id"]] if page else cursor)
