from datetime import datetime
def run(request):
    instant = datetime.fromisoformat(request["at"])
    def valid(row):
        start = datetime.fromisoformat(row["start"])
        end = datetime.fromisoformat(row["end"])
        return start <= instant <= end
    return sorted(row["id"] for row in request["qualifications"] if valid(row))
