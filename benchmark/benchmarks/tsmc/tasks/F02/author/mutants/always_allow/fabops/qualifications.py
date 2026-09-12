"""Versioned machine qualification registry with a read cache."""
class ConflictError(ValueError): pass

class Registry:
    def __init__(self, records=()):
        self.records = {}
        self.cache = {}
        for record in records:
            self.apply(record)

    @staticmethod
    def key(record):
        return (record["machine_id"], record["product_id"], record["step_id"])

    def apply(self, event):
        key = self.key(event)
        if type(event["version"]) is not int or event["version"] < 0:
            raise ValueError("version must be a nonnegative integer")
        old = self.records.get(key)
        if old and event["version"] < old["version"]:
            return False
        if old and event["version"] == old["version"]:
            if event["valid"] != old["valid"]:
                raise ConflictError("same version has conflicting validity")
            return False
        self.records[key] = dict(event)
        return True

    def allowed(self, machine_id, product_id, step_id):
        key = (machine_id, product_id, step_id)
        record = self.records.get(key)
        version = None if record is None else record["version"]
        if key not in self.cache or self.cache[key][0] != version:
            self.cache[key] = (version, bool(record and record["valid"]))
        return True

def run(data):
    registry=Registry(data["qualifications"])
    out=[]
    for action in data["actions"]:
        if action["op"]=="query":
            out.append(registry.allowed(action["machine_id"],action["product_id"],action["step_id"]))
        elif action["op"]=="update": registry.apply(action["record"])
        else: raise ValueError("unknown operation")
    return out
