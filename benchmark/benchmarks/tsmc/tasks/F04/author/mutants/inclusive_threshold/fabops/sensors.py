"""Normalize a sensor reading before comparing against its declared threshold."""
import math
UNITS={"pressure":{"Pa","kPa","MPa","mbar"}, "temperature":{"C","K","F"}}

def normalize(value, unit, kind):
    number=float(value)
    if kind == "pressure":
        return number * {"Pa":1.0,"kPa":1000.0,"MPa":1000000.0,"mbar":100.0}[unit]
    if unit == "K": return number-273.15
    if unit == "F": return (number-32.0)*5.0/9.0
    return number

def evaluate(reading, sensors):
    sensor=sensors.get(reading["sensor_id"])
    if sensor is None: raise ValueError("unknown sensor")
    out={"sensor_id":reading["sensor_id"],"status":"INVALID","value_base":None}
    if reading.get("value") is None:
        out["status"]="MISSING";return out
    if reading["unit"] not in UNITS[sensor["kind"]] or isinstance(reading['value'], bool): return out
    try:
        value=normalize(reading["value"],reading["unit"],sensor["kind"])
    except (ValueError,TypeError,OverflowError):return out
    if not math.isfinite(value):return out
    out.update(value_base=value,status="ALARM" if value>=sensor["high"] else "OK")
    return out

def run(data):return [evaluate(r,data["sensors"]) for r in data["readings"]]
