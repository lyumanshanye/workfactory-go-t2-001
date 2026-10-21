#!/usr/bin/env python3
"""
Hexline Studio – Transport Prototype First-Year Fleet Planner
Usage: python model.py --inputs INPUT_DIR --output OUTPUT_DIR
"""
import json, math, hashlib, os, argparse

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def time_factor(t, days1, days2):
    return max(31, 255 - max(0, t - days1) - max(0, t - days1 - days2))

def calc_revenue(cr, dist, age_t, n, cap, acycles, demand):
    base, d1, d2 = cr["base"], cr["days1"], cr["days2"]
    trips = n * acycles
    total_cap = trips * cap
    delivered = min(demand, total_cap)
    f = time_factor(age_t, d1, d2)
    if cap == 0:
        return 0, 0, trips
    full = delivered // cap
    rem = delivered % cap
    rev = full * math.floor(base * cap * dist * f / (2**21))
    if rem > 0:
        rev += math.floor(base * rem * dist * f / (2**21))
    return rev, delivered, trips

def option_metrics(routes, cr, pol, stress):
    yd = pol["year_days"]; mx = pol["max_per_option"]
    sdp = pol.get("stress_demand_percent", 100)
    sap = pol.get("stress_age_periods", 0)
    scd = pol.get("stress_cycle_days", 0)
    out = {}
    for r in routes:
        rid = r["id"]; c = cr[r["cargo"]]
        dist = manhattan(r["from"], r["to"])
        cd = r["cycle_days"] + (scd if stress else 0)
        at = r["age_periods"] + (sap if stress else 0)
        ac = math.floor(yd / cd) if cd > 0 else 0
        dm = r["demand"] if not stress else math.floor(r["demand"] * sdp / 100)
        tf = time_factor(at, c["days1"], c["days2"])
        ms = []
        for n in range(mx + 1):
            tr = n * ac; tc = tr * r["capacity"]
            dv = min(dm, tc)
            rv, _, _ = calc_revenue(c, dist, at, n, r["capacity"], ac, dm)
            cx = n * r["capex"]; rn = n * r["annual_running"]
            ms.append({"vehicles":n,"distance":dist,"age_periods":at,"time_factor":tf,
                "cycle_days":cd,"available_trips":tr,"demand":dm,"delivered":dv,
                "revenue":rv,"capex":cx,"annual_running":rn,"first_year_net":rv-cx-rn})
        out[rid] = ms
    return out

def enum_fleets(routes, pol):
    mx = pol["max_per_option"]; fl = pol["fleet_limit"]
    grps = {}
    for r in routes:
        grps.setdefault(r["exclusive_group"], []).append(r["id"])
    gchoices = {}
    for g, rids in grps.items():
        ch = [{rid:0 for rid in rids}]
        for rid in rids:
            for n in range(1, mx+1):
                c = {r2:0 for r2 in rids}; c[rid] = n; ch.append(c)
        gchoices[g] = ch
    gn = list(grps.keys())
    def go(i, cur, tot):
        if i == len(gn):
            yield dict(cur); return
        g = gn[i]
        for c in gchoices[g]:
            a = sum(c.values())
            if tot + a <= fl:
                nf = dict(cur); nf.update(c)
                yield from go(i+1, nf, tot+a)
    return list(go(0, {}, 0))

def eval_fleet(fleet, rdict, cr, pol, stress):
    yd = pol["year_days"]
    sdp = pol.get("stress_demand_percent", 100)
    sap = pol.get("stress_age_periods", 0)
    scd = pol.get("stress_cycle_days", 0)
    trev = tcx = trn = 0
    for rid, n in fleet.items():
        if n == 0: continue
        r = rdict[rid]; c = cr[r["cargo"]]
        dist = manhattan(r["from"], r["to"])
        cd = r["cycle_days"] + (scd if stress else 0)
        at = r["age_periods"] + (sap if stress else 0)
        ac = math.floor(yd / cd) if cd > 0 else 0
        dm = r["demand"] if not stress else math.floor(r["demand"] * sdp / 100)
        rv, _, _ = calc_revenue(c, dist, at, n, r["capacity"], ac, dm)
        trev += rv; tcx += n * r["capex"]; trn += n * r["annual_running"]
    return trev, tcx, trn, trev - tcx - trn

def solve(inputs_dir, output_dir):
    routes = load_json(os.path.join(inputs_dir, "routes.json"))
    cr = load_json(os.path.join(inputs_dir, "cargo-rates.json"))
    pol = load_json(os.path.join(inputs_dir, "planning_policy.json"))
    rdict = {r["id"]: r for r in routes}
    rids = [r["id"] for r in routes]
    isha = {fn: sha256_file(os.path.join(inputs_dir, fn))
            for fn in ["routes.json","cargo-rates.json","planning_policy.json"]}
    fleets = enum_fleets(routes, pol)
    frs = []
    for fl in fleets:
        brv, bcx, brn, bnet = eval_fleet(fl, rdict, cr, pol, False)
        srv, scx, srn, snet = eval_fleet(fl, rdict, cr, pol, True)
        frs.append({"fleet":fl,"capex":bcx,"base_net":bnet,"stress_net":snet,
                     "base_revenue":brv,"stress_revenue":srv,"annual_running":brn})
    bopts = option_metrics(routes, cr, pol, False)
    sopts = option_metrics(routes, cr, pol, True)
    msn = pol["minimum_stress_net"]
    cases = {}
    for bc in pol["budget_cases"]:
        cid = bc["id"]; bgt = bc["budget"]
        feas = [f for f in frs if f["capex"] <= bgt and f["stress_net"] >= msn]
        feas.sort(key=lambda f: (-f["stress_net"], -f["base_net"], f["capex"],
                                  tuple(f["fleet"].get(rid,0) for rid in rids)))
        fc = len(feas)
        best = alts = None
        if fc > 0:
            b = feas[0]
            best = {"fleet":b["fleet"],"capex":b["capex"],"base_net":b["base_net"],
                    "stress_net":b["stress_net"],
                    "vehicles":{rid:b["fleet"].get(rid,0) for rid in rids}}
            alts = []
            for i in range(1, min(4, fc)):
                a = feas[i]
                alts.append({"fleet":a["fleet"],"capex":a["capex"],"base_net":a["base_net"],
                    "stress_net":a["stress_net"],
                    "vehicles":{rid:a["fleet"].get(rid,0) for rid in rids}})
        opts = []
        for r in routes:
            rid = r["id"]; vs = []
            for n in range(pol["max_per_option"]+1):
                bm = bopts[rid][n]; sm = sopts[rid][n]
                mf = ["distance","age_periods","time_factor","cycle_days",
                      "available_trips","demand","delivered","revenue","capex",
                      "annual_running","first_year_net"]
                vs.append({"count":n,"base":{k:bm[k] for k in mf},
                           "stress":{k:sm[k] for k in mf}})
            opts.append({"route_id":rid,"cargo":r["cargo"],
                         "exclusive_group":r["exclusive_group"],"vehicles":vs})
        cases[cid] = {"budget":bgt,"feasible_count":fc,"best":best,
                      "alternatives":alts if alts is not None else [],"options":opts}
    s = cases["standard"]; r = cases["reduced"]
    if s["best"] and r["best"]:
        cs = s["best"]["capex"] - r["best"]["capex"]
        snf = s["best"]["stress_net"] - r["best"]["stress_net"]
        snrf = r["best"]["stress_net"] / s["best"]["stress_net"] if s["best"]["stress_net"] else None
    else:
        cs = snf = 0; snrf = None
    plan = {"currency":pol["currency"],"cases":cases,
            "budget_comparison":{"capex_saved":cs,"stress_net_forgone":snf,
                                  "stress_net_retained_fraction":snrf},
            "input_sha256":isha}
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "plan.json"), 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    return plan

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    solve(a.inputs, a.output)
