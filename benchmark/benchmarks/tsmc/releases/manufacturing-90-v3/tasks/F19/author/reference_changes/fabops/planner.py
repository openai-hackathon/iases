"""Enumerate small dispatch plans with shared tool and reticle constraints."""
def plan(lots, tools, stock):
    lots = sorted(lots, key=lambda lot: lot["id"])
    best, best_score = [], None
    def visit(index, pairs, used, remaining, priority, cost):
        nonlocal best, best_score
        if index == len(lots):
            score = (-len(pairs), -priority, cost, tuple(pairs))
            if best_score is None or score < best_score:
                best, best_score = list(pairs), score
            return
        lot = lots[index]
        visit(index + 1, pairs, used, remaining, priority, cost)
        reticle = lot["reticle"]
        if remaining.get(reticle, 0) == 0:
            return
        for tool in sorted(tools):
            if tool in used or tool not in lot["costs"]:
                continue
            next_stock = dict(remaining)
            next_stock[reticle] -= 1
            visit(index + 1, pairs + [(lot["id"], tool)], used | {tool}, next_stock,
                  priority + lot["priority"], cost + lot["costs"][tool])
    visit(0, [], set(), dict(stock), 0, 0)
    return [list(pair) for pair in best]
