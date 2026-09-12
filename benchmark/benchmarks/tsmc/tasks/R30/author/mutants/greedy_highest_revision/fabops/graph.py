"""Resolve a globally compatible, verified, rollback-safe dependency closure."""
import hashlib

def closure(artifacts, roots, floors):
    names=sorted({row["id"] for row in artifacts})
    maximum={name:max(row["revision"] for row in artifacts if row["id"]==name) for name in names}
    best,best_rank=None,None
    def ordered(selection):
        active,done,result=set(),set(),[]
        def visit(name):
            if name in active:
                raise ValueError("dependency cycle")
            if name in done:
                return
            active.add(name)
            for dep in sorted(selection[name]["requires"]):
                visit(dep[0])
            active.remove(name)
            done.add(name)
            result.append(selection[name])
        for root in sorted(roots):
            visit(root[0])
        return result
    def search(pending,selection):
        nonlocal best,best_rank
        upper=tuple(selection[name]["revision"] if name in selection else maximum[name] for name in names)
        if best_rank is not None and upper<=best_rank:
            return
        if not pending:
            try:
                result=ordered(selection)
            except ValueError:
                return
            rank=tuple(selection[name]["revision"] if name in selection else 0 for name in names)
            if best_rank is None or rank>best_rank:
                best,best_rank=result,rank
            return
        reference,*remaining=sorted(pending)
        name,low=reference[:2]
        high=reference[2] if len(reference)==3 else low
        if name in selection:
            if low<=selection[name]["revision"]<=high:
                search(remaining,selection)
            return
        candidates=[row for row in artifacts if row["id"]==name and low<=row["revision"]<=high
                    and row["revision"]>=floors.get(name,0) and not row["revoked"]
                    and hashlib.sha256(row["content"].encode()).hexdigest()==row["sha256"]]
        for row in sorted(candidates,key=lambda row:row["revision"],reverse=True):
            search(remaining+row["requires"],dict(selection,**{name:row}))
            break
    search(list(roots),{})
    if best is None:
        raise ValueError("no compatible verified closure")
    return best
