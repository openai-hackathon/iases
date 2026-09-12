"""Search complete temporal assignments, including deliberate idle periods."""
from .resources import feasible

def plan(request):
    lots = sorted(request["lots"], key=lambda lot: lot["id"])
    best, best_score = [], None
    def visit(index, rows):
        nonlocal best, best_score
        if best_score is not None:
            count_bound = len(rows) + len(lots) - index
            if count_bound < -best_score[0]:
                return
            if count_bound == -best_score[0]:
                priority_bound = sum(lots_by_id[row[0]]["priority"] for row in rows) + sum(lot["priority"] for lot in lots[index:])
                if priority_bound < -best_score[1]:
                    return
                if priority_bound == -best_score[1]:
                    cost_bound = sum(lots_by_id[row[0]]["costs"][row[1]] for row in rows) + sum(min(lot["costs"].values(), default=0) for lot in lots[index:])
                    finish_bound = sum(row[3] for row in rows) + sum(lot["release"] + min(lot["durations"].values(), default=0) for lot in lots[index:])
                    if cost_bound > best_score[2] or (cost_bound == best_score[2] and finish_bound > best_score[3]):
                        return
        if index == len(lots):
            selected = {row[0] for row in rows}
            if any(not set(lot.get("after", [])) <= selected
                   for lot in lots if lot["id"] in selected):
                return
            priority = sum(lot["priority"] for lot in lots if lot["id"] in selected)
            cost = sum(lots_by_id[row[0]]["costs"][row[1]] for row in rows)
            finish = sum(row[3] for row in rows)
            score = (-priority, -len(rows), cost, finish, tuple(map(tuple, rows)))
            if best_score is None or score < best_score:
                best, best_score = list(rows), score
            return
        lot = lots[index]
        for tool in sorted(set(request["tools"]) & lot["costs"].keys()):
            duration = lot["durations"][tool]
            for start in range(lot["release"], min(lot["deadline"], request["horizon"]) - duration + 1):
                candidate = rows + [[lot["id"], tool, start, start + duration]]
                if feasible(request, candidate):
                    visit(index + 1, candidate)
        visit(index + 1, rows)
    lots_by_id = {lot["id"]: lot for lot in lots}
    visit(0, [])
    return best
