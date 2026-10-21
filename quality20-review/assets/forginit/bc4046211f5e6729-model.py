"""Original bounded planning model; not an OpenTTD engine implementation."""

import argparse
from datetime import datetime
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path


def select_version(scenario, events):
    cutoff = datetime.fromisoformat(scenario["as_of"])
    approvals = {event["version"]: event for event in events["events"]
                 if event["action"] == "approve" and event["role"] in events["authorized_roles"]
                 and datetime.fromisoformat(event["at"]) <= cutoff}
    active = [packet for packet in scenario["versions"]
              if packet["id"] in approvals
              and datetime.fromisoformat(packet["effective_at"]) <= cutoff
              and (packet["retired_at"] is None or datetime.fromisoformat(packet["retired_at"]) > cutoff)]
    if len(active) != 1:
        raise ValueError("Approval authority does not identify exactly one active version")
    return active[0]


def route_result(route, rate, vehicles, policy, stressed):
    distance = abs(route["from"][0] - route["to"][0]) + abs(route["from"][1] - route["to"][1])
    age = route["age_periods"] + (policy["stress_age_periods"] if stressed else 0)
    cycle = route["cycle_days"] + (policy["stress_cycle_days"] if stressed else 0)
    demand = route["demand"] * (policy["stress_demand_percent"] if stressed else 100) // 100
    factor = max(31, 255 - max(0, age - rate["days1"]) - max(0, age - rate["days1"] - rate["days2"]))
    trips = vehicles * (policy["year_days"] // cycle)
    units = min(demand, trips * route["capacity"])
    per_unit = Fraction(rate["base"] * distance * factor, 2**21)
    full, tail = divmod(units, route["capacity"])
    # The exercise explicitly floors each complete or partial shipment payment.
    gross = full * int(per_unit * route["capacity"]) + int(per_unit * tail)
    capex = vehicles * route["capex"]
    operating = vehicles * route["annual_running"]
    return dict(distance=distance, age_periods=age, time_factor=factor, cycle_days=cycle,
                available_trips=trips, demand=demand, delivered=units, revenue=gross,
                capex=capex, annual_running=operating, first_year_net=gross - capex - operating)


def solve(scenario, events, rates):
    version = select_version(scenario, events)
    policy = version["policy"]
    routes = [dict(route, **version["route_overrides"].get(route["id"], {})) for route in scenario["routes"]]
    options = {}
    for route in routes:
        options[route["id"]] = [dict(vehicles=n,
            base=route_result(route, rates[route["cargo"]], n, policy, False),
            stress=route_result(route, rates[route["cargo"]], n, policy, True))
            for n in range(policy["max_per_option"] + 1)]
    feasible = []
    for fleet in itertools.product(range(policy["max_per_option"] + 1), repeat=len(routes)):
        if sum(fleet) > policy["fleet_limit"]:
            continue
        groups = [route["exclusive_group"] for route, n in zip(routes, fleet) if n]
        if len(set(groups)) != len(groups):
            continue
        selected = [options[r["id"]][n] for r, n in zip(routes, fleet)]
        capex = sum(x["base"]["capex"] for x in selected)
        worst = sum(x["stress"]["first_year_net"] for x in selected)
        base = sum(x["base"]["first_year_net"] for x in selected)
        if capex > policy["budget"] or worst < policy["minimum_stress_net"]:
            continue
        feasible.append(dict(fleet=dict(zip((r["id"] for r in routes), fleet)), capex=capex,
                             base_net=base, stress_net=worst, vehicles=sum(fleet)))
    feasible.sort(key=lambda x: (-x["stress_net"], -x["base_net"], x["capex"], tuple(x["fleet"].values())))
    return dict(version=version["id"], scope="wiki-based exercise planning model; not current-engine validation",
                feasible_count=len(feasible), best=feasible[0] if feasible else None,
                alternatives=feasible[1:4], options=options)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    names = ("scenario.json", "approval-events.json", "cargo-rates.json")
    values = [json.loads((args.inputs / name).read_text()) for name in names]
    result = solve(*values)
    result["input_sha256"] = {name: hashlib.sha256((args.inputs / name).read_bytes()).hexdigest() for name in names}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "plan.json").write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
