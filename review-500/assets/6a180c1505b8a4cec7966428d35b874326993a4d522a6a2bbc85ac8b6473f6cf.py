"""Reference OEE implementation used by the Willowmere plant feed."""
from datetime import datetime, time

CELL_CONFIG = {
    "CELL01": {"ideal_cycle_seconds": 12.0, "outputs_per_cycle": 1},
    "CELL02": {"ideal_cycle_seconds": 15.0, "outputs_per_cycle": 1},
    "CELL03": {"ideal_cycle_seconds": 10.0, "outputs_per_cycle": 1},
    "CELL04": {"ideal_cycle_seconds": 20.0, "outputs_per_cycle": 1},
    "CELL05": {"ideal_cycle_seconds": 18.0, "outputs_per_cycle": 1},
    "CELL06": {"ideal_cycle_seconds": 16.0, "outputs_per_cycle": 1},
    "CELL07": {"ideal_cycle_seconds": 24.0, "outputs_per_cycle": 2},
    "CELL08": {"ideal_cycle_seconds": 14.0, "outputs_per_cycle": 1},
    "CELL09": {"ideal_cycle_seconds": 22.0, "outputs_per_cycle": 1},
    "CELL10": {"ideal_cycle_seconds": 11.0, "outputs_per_cycle": 1},
    "CELL11": {"ideal_cycle_seconds": 19.0, "outputs_per_cycle": 1},
}
SHIFT_ORDER = ("SHIFT1", "SHIFT2", "SHIFT3")
EXCLUDED_REASONS = {"PM", "NO_MATERIAL"}

def _ts(value):
    return datetime.fromisoformat(value)

def _shift(value):
    t = value.time()
    if time(6, 0) <= t < time(14, 0):
        return "SHIFT1"
    if time(14, 0) <= t < time(21, 49):
        return "SHIFT2"
    return "SHIFT3"

def _metrics(run, down, good, reject, cfg):
    planned = run + down
    produced = good + reject
    theoretical = produced / cfg["outputs_per_cycle"] * cfg["ideal_cycle_seconds"] / 60.0
    availability = run / planned if planned > 0 else None
    performance = min(1.0, theoretical / run) if run > 0 else None
    quality = good / produced if produced > 0 else None
    oee = availability * performance * quality if None not in (availability, performance, quality) else None
    return {"run_minutes": run, "downtime_minutes": down, "planned_production_minutes": planned,
            "good_units": good, "reject_units": reject, "theoretical_production_minutes": theoretical,
            "availability": availability, "performance": performance, "quality": quality, "oee": oee}

def build_report(events, period_start, period_end):
    start, end = _ts(period_start), _ts(period_end)
    buckets = {cell: {shift: [0.0, 0.0, 0, 0] for shift in SHIFT_ORDER} for cell in CELL_CONFIG}
    for event in events:
        duration = float(event["duration_minutes"])
        # Legacy baseline assumes positive durations; extension adds explicit validation.
        stamp = _ts(event["timestamp"])
        if stamp < start or stamp >= end or event["cell_id"] not in buckets:
            continue
        cell, shift = event["cell_id"], _shift(stamp)
        state = event.get("state")
        if state == "RUN":
            b = buckets[cell][shift]
            b[0] += duration; b[2] += int(event.get("good_units", 0) or 0); b[3] += int(event.get("reject_units", 0) or 0)
        elif state == "DOWN" and event.get("downtime_reason") not in EXCLUDED_REASONS:
            buckets[cell][shift][1] += duration
    cells = []
    plant_raw = [0.0, 0.0, 0, 0]
    plant_theoretical = 0.0
    for cell, cfg in CELL_CONFIG.items():
        shifts = []
        cell_raw = [0.0, 0.0, 0, 0]
        for shift in SHIFT_ORDER:
            run, down, good, reject = buckets[cell][shift]
            m = _metrics(run, down, good, reject, cfg)
            shifts.append({"shift_id": shift, **m})
            cell_raw[0] += run; cell_raw[1] += down; cell_raw[2] += good; cell_raw[3] += reject
        agg = _metrics(*cell_raw, cfg)
        cells.append({"cell_id": cell, "shifts": shifts, "aggregate": agg})
        plant_raw[0] += cell_raw[0]; plant_raw[1] += cell_raw[1]; plant_raw[2] += cell_raw[2]; plant_raw[3] += cell_raw[3]
        plant_theoretical += agg["theoretical_production_minutes"]
    plant = _metrics(*plant_raw, {"ideal_cycle_seconds": 0.0, "outputs_per_cycle": 1})
    plant["theoretical_production_minutes"] = plant_theoretical
    plant["performance"] = min(1.0, plant_theoretical / plant_raw[0]) if plant_raw[0] > 0 else None
    plant["oee"] = plant["availability"] * plant["performance"] * plant["quality"] if None not in (plant["availability"], plant["performance"], plant["quality"]) else None
    return {"period_start": period_start, "period_end": period_end, "cells": cells, "plant": plant}

if __name__ == "__main__":
    import json, sys
    print(json.dumps(build_report([], "2026-01-01T00:00:00", "2026-01-02T00:00:00"), indent=2))
