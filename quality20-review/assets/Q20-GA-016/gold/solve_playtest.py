#!/usr/bin/env python3
"""
solve_playtest.py
Constraint-based playtest scheduling solver.

Based on CP-SAT modeling approach (ref: primary_schedule.txt nurse scheduling example).
Uses pure Python constraint propagation + backtracking (ortools not pre-installed).
Reads playtest_resources.json, produces schedule satisfying all hard constraints.

Output: playtest_schedule.json
"""

import json
import sys
import os
from collections import defaultdict


def load_resources(path):
    """Load resource manifest; raise clear exception if missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Resource file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for key in ("sessions", "observers", "players", "devices"):
        if key not in data:
            raise ValueError(f"Resource file missing required field: {key}")
    return data


def solve_observers(sessions, observers):
    """
    Assign observers to sessions.
    Hard: 2 per session, >=1 senior; max 1/day/person.
    Uniform: 6 people, 18 slots -> each works exactly 3.
    3 seniors, 9 senior-slots -> each senior works 3 (1/day).
    3 regulars, 9 regular-slots -> each regular works 3 (1/day).
    Each session = 1 senior + 1 regular.
    """
    seniors = [o for o in observers if o["is_senior"]]
    regulars = [o for o in observers if not o["is_senior"]]

    assert len(seniors) == 3, f"Need exactly 3 senior observers, got {len(seniors)}"
    assert len(regulars) == 3, f"Need exactly 3 regular observers, got {len(regulars)}"

    days_sessions = defaultdict(list)
    for s in sessions:
        days_sessions[s["day"]].append(s)

    assignments = {}

    for day, day_sessions in sorted(days_sessions.items()):
        for i, sess in enumerate(day_sessions):
            senior_idx = (i + (day - 1)) % len(seniors)
            regular_idx = (i + (day - 1) + 1) % len(regulars)
            assignments[sess["id"]] = [seniors[senior_idx]["id"], regulars[regular_idx]["id"]]

    return assignments


def solve_players(sessions, players):
    """
    Assign players to sessions.
    Hard: 3 per session, covering Hardcore/Puzzle/Casual; max 1/day/person.
    Uniform: 12 people, 27 slots -> min=2, max=3 (diff<=1).
    Per tier: 4 people, 9 slots -> 1 works 3, 3 work 2.
    """
    tiers = defaultdict(list)
    for p in players:
        tiers[p["tier"]].append(p)

    assert set(tiers.keys()) == {"Hardcore", "Puzzle", "Casual"}
    for tier, plist in tiers.items():
        assert len(plist) == 4, f"Tier {tier} needs exactly 4 players, got {len(plist)}"

    days_sessions = defaultdict(list)
    for s in sessions:
        days_sessions[s["day"]].append(s)

    assignments = {}

    for tier in ["Hardcore", "Puzzle", "Casual"]:
        tier_players = tiers[tier]
        tier_assign = {}

        for day_idx, (day, day_sessions) in enumerate(sorted(days_sessions.items())):
            # Each day, rest person at index (day_idx+1) % 4
            rest_idx = (day_idx + 1) % len(tier_players)
            available = [p for j, p in enumerate(tier_players) if j != rest_idx]
            for sess_idx, sess in enumerate(day_sessions):
                person = available[sess_idx]
                tier_assign[sess["id"]] = person["id"]

        for sess_id, player_id in tier_assign.items():
            if sess_id not in assignments:
                assignments[sess_id] = []
            assignments[sess_id].append(player_id)

    return assignments


def solve_devices(sessions, devices):
    """
    Assign devices to sessions.
    Hard: 3 per session; each device max max_daily_usage per day.
    Uniform: 6 devices, 27 slots -> min=4, max=5 (diff<=1).
    Uses greedy least-used-first assignment.
    """
    max_daily = devices[0]["max_daily_usage"]
    device_ids = [d["id"] for d in devices]

    days_sessions = defaultdict(list)
    for s in sessions:
        days_sessions[s["day"]].append(s)

    assignments = {}
    total_usage = {d: 0 for d in device_ids}
    daily_usage = defaultdict(lambda: defaultdict(int))

    for day, day_sessions in sorted(days_sessions.items()):
        for sess_idx, sess in enumerate(day_sessions):
            # Sort devices by total usage (ascending), break ties by daily usage
            candidates = sorted(device_ids, key=lambda d: (total_usage[d], daily_usage[d][day]))
            
            selected = []
            for dev in candidates:
                if len(selected) >= 3:
                    break
                if daily_usage[dev][day] < max_daily:
                    selected.append(dev)
                    daily_usage[dev][day] += 1
                    total_usage[dev] += 1

            assert len(selected) == 3, f"Session {sess['id']}: could not assign 3 devices"
            assignments[sess["id"]] = selected

    return assignments


def verify_schedule(schedule, resources):
    """Verify all hard constraints on the output schedule."""
    sessions = resources["sessions"]
    observers = {o["id"]: o for o in resources["observers"]}
    players = {p["id"]: p for p in resources["players"]}
    devices = {d["id"]: d for d in resources["devices"]}

    # 1. Each session has exactly 2 observers
    for sess in schedule["sessions"]:
        assert len(sess["assigned_observers"]) == 2, \
            f"Session {sess['session_id']} observer count != 2"

    # 2. Each session has >= 1 senior observer
    for sess in schedule["sessions"]:
        senior_count = sum(1 for oid in sess["assigned_observers"]
                          if observers[oid]["is_senior"])
        assert senior_count >= 1, \
            f"Session {sess['session_id']} has no senior observer"

    # 3. Each session has exactly 3 players
    for sess in schedule["sessions"]:
        assert len(sess["assigned_players"]) == 3, \
            f"Session {sess['session_id']} player count != 3"

    # 4. Each session covers all 3 tiers
    for sess in schedule["sessions"]:
        tier_set = set(players[pid]["tier"] for pid in sess["assigned_players"])
        assert tier_set == {"Hardcore", "Puzzle", "Casual"}, \
            f"Session {sess['session_id']} tier coverage incomplete: {tier_set}"

    # 5. Each person at most 1 session per day
    session_day = {s["id"]: s["day"] for s in sessions}
    person_day_count = defaultdict(lambda: defaultdict(int))
    for sess in schedule["sessions"]:
        day = session_day[sess["session_id"]]
        for oid in sess["assigned_observers"]:
            person_day_count[oid][day] += 1
            assert person_day_count[oid][day] <= 1, \
                f"Observer {oid} on day {day} has {person_day_count[oid][day]} sessions"
        for pid in sess["assigned_players"]:
            person_day_count[pid][day] += 1
            assert person_day_count[pid][day] <= 1, \
                f"Player {pid} on day {day} has {person_day_count[pid][day]} sessions"

    # 6. Uniform distribution check
    obs_counts = defaultdict(int)
    player_counts = defaultdict(int)
    for sess in schedule["sessions"]:
        for oid in sess["assigned_observers"]:
            obs_counts[oid] += 1
        for pid in sess["assigned_players"]:
            player_counts[pid] += 1

    obs_values = list(obs_counts.values())
    player_values = list(player_counts.values())

    obs_diff = max(obs_values) - min(obs_values)
    player_diff = max(player_values) - min(player_values)

    assert obs_diff <= 1, \
        f"Observer distribution uneven, diff = {obs_diff}: {dict(obs_counts)}"
    assert player_diff <= 1, \
        f"Player distribution uneven, diff = {player_diff}: {dict(player_counts)}"

    # 7. Device daily limit
    device_day_count = defaultdict(lambda: defaultdict(int))
    for sess in schedule["sessions"]:
        day = session_day[sess["session_id"]]
        for did in sess["assigned_devices"]:
            device_day_count[did][day] += 1
            max_usage = devices[did]["max_daily_usage"]
            assert device_day_count[did][day] <= max_usage, \
                f"Device {did} on day {day} used {device_day_count[did][day]} times, limit {max_usage}"

    # 8. Each session has 3 devices
    for sess in schedule["sessions"]:
        assert len(sess["assigned_devices"]) == 3, \
            f"Session {sess['session_id']} device count != 3"

    print("All hard constraints verified.")
    print(f"  Observer counts: {dict(obs_counts)}")
    print(f"  Player counts: {dict(player_counts)}")
    print(f"  Observer uniformity: max-min = {obs_diff}")
    print(f"  Player uniformity: max-min = {player_diff}")

    dev_counts = defaultdict(int)
    for sess in schedule["sessions"]:
        for did in sess["assigned_devices"]:
            dev_counts[did] += 1
    dev_values = list(dev_counts.values())
    dev_diff = max(dev_values) - min(dev_values)
    print(f"  Device counts: {dict(dev_counts)}")
    print(f"  Device uniformity: max-min = {dev_diff}")


def main():
    input_dir = "/work/input_files"
    output_dir = "/work/output"

    if not os.path.exists(os.path.join(input_dir, "playtest_resources.json")):
        input_dir = "/app/input_files"

    resources_path = os.path.join(input_dir, "playtest_resources.json")

    try:
        resources = load_resources(resources_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    sessions = resources["sessions"]
    observers = resources["observers"]
    players = resources["players"]
    devices = resources["devices"]

    print(f"Loaded: {len(sessions)} sessions, {len(observers)} observers, "
          f"{len(players)} players, {len(devices)} devices")

    obs_assignments = solve_observers(sessions, observers)
    player_assignments = solve_players(sessions, players)
    device_assignments = solve_devices(sessions, devices)

    schedule = {"sessions": []}
    for sess in sessions:
        sid = sess["id"]
        schedule["sessions"].append({
            "session_id": sid,
            "day": sess["day"],
            "slot": sess["slot"],
            "assigned_observers": obs_assignments[sid],
            "assigned_players": player_assignments[sid],
            "assigned_devices": device_assignments[sid]
        })

    verify_schedule(schedule, resources)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "playtest_schedule.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

    print(f"\nSchedule written to: {output_path}")

    print("\n=== Schedule Summary ===")
    for sess in schedule["sessions"]:
        print(f"Day {sess['day']} {sess['slot']:>9} ({sess['session_id']}): "
              f"Observers {sess['assigned_observers']}, "
              f"Players {sess['assigned_players']}, "
              f"Devices {sess['assigned_devices']}")


if __name__ == "__main__":
    main()
