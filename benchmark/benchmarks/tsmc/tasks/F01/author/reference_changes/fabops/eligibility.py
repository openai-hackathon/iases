"""Eligibility of a proposed lot assignment; no state is changed here."""
from collections.abc import Mapping, Sequence

def eligible(lot_id: str, machine_id: str, lots: Mapping, machines: Mapping,
             qualifications: Sequence[Mapping]) -> bool:
    lot, machine = lots.get(lot_id), machines.get(machine_id)
    if lot is None or machine is None:
        return False
    return (not lot["quality_hold"]
            and lot["status"] == "WAITING"
            and machine["state"] == "AVAILABLE"
            and any(q["machine_id"] == machine_id
                    and q["product_id"] == lot["product_id"]
                    and q["step_id"] == lot["step_id"] and q["valid"]
                    for q in qualifications))

def run(data: dict) -> list[bool]:
    return [eligible(x["lot_id"],x["machine_id"],data["lots"],data["machines"],data["qualifications"])
            for x in data["assignments"]]
