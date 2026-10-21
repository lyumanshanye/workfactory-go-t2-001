"""Reproduce two real GHCNd audit windows with explicit dependency receipts."""

import argparse
import calendar
import csv
import hashlib
import json
from pathlib import Path
import runpy
import shutil

import pandas as pd


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def analyze(inputs, output, station_first=False):
    workflow = runpy.run_path(str(inputs / "workflow.py"))
    config_path = inputs / "workflow.json"
    config = json.loads(config_path.read_text())
    policy = config["policy"]
    if policy["version"] != "QC-2024.2":
        raise ValueError("unapproved QC policy")
    output.mkdir(parents=True, exist_ok=True)
    code = Path(__file__)
    if code.resolve() != (output / "analysis.py").resolve():
        shutil.copyfile(code, output / "analysis.py")
    def seal(name):
        return workflow["seal"](config_path, inputs, output, name)
    columns = [(0, 11), (11, 15), (15, 17), (17, 21)]
    names = ["station", "year", "month", "element"]
    for day in range(1, 32):
        offset = 21 + 8 * (day - 1)
        columns.extend([(offset, offset + 5), (offset + 5, offset + 6), (offset + 6, offset + 7), (offset + 7, offset + 8)])
        names.extend([f"raw{day}", f"m{day}", f"q{day}", f"s{day}"])
    table = pd.read_fwf(inputs / "station-daily.txt", colspecs=columns, names=names, dtype=str, keep_default_na=False)
    table = table[table["year"].isin([str(y) for y in policy["years"]]) & table["element"].isin(policy["elements"])]
    if table.duplicated(["station", "year", "month", "element"]).any() or set(table["station"]) != {policy["station_id"]}:
        raise ValueError("duplicate or unexpected station/month/element")
    indexed = {(int(r["year"]), int(r["month"]), r["element"]):r for r in table.to_dict("records")}
    daily = []
    for year in policy["years"]:
        for month in range(1, 13):
            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                for element in policy["elements"]:
                    record = indexed.get((year, month, element))
                    raw_text = record[f"raw{day}"].strip() if record else ""
                    raw = int(raw_text) if raw_text else -9999
                    mflag, qflag, sflag = [record[f"{prefix}{day}"].strip() if record else "" for prefix in ("m", "q", "s")]
                    present = record is not None and raw != -9999
                    usable = present and not qflag
                    value = raw / 10.0 if usable else None
                    daily.append(dict(station=policy["station_id"], date=f"{year}-{month:02}-{day:02}", element=element,
                        record_present=bool(record), raw_value=raw_text, mflag=mflag, qflag=qflag, sflag=sflag,
                        usable=usable, value="" if value is None else f"{value:.1f}"))
    write_csv(output / "daily.csv", daily, list(daily[0]))
    seal("ingest")

    def quality_branch():
        groups = []
        for year in policy["years"]:
            for element in policy["elements"]:
                rows = [r for r in daily if r["date"].startswith(str(year)) and r["element"] == element]
                missing = sum(not r["record_present"] or r["raw_value"] == "-9999" for r in rows)
                rejected = sum(r["record_present"] and r["raw_value"] != "-9999" and bool(r["qflag"]) for r in rows)
                groups.append(dict(year=year, element=element, calendar_days=len(rows), usable=sum(r["usable"] for r in rows),
                                   missing=missing, rejected=rejected, absent_month_days=sum(not r["record_present"] for r in rows)))
        write_json(output / "quality.json", dict(policy=policy["version"], groups=groups, daily_sha256=digest(output / "daily.csv")))
        seal("quality")
        return groups

    def station_branch():
        catalog = pd.read_fwf(inputs / "stations.txt", colspecs=[(0, 11), (12, 20), (21, 30), (31, 37), (41, 71), (80, 85)],
                              names=["id", "latitude", "longitude", "elevation", "name", "wmo"], dtype=str, keep_default_na=False)
        chosen = catalog[catalog["id"] == policy["station_id"]]
        if len(chosen) != 1:
            raise ValueError("missing or ambiguous catalog station")
        row = chosen.iloc[0].to_dict()
        for key in ("latitude", "longitude", "elevation"):
            row[key] = float(row[key])
        row["catalog_sha256"] = digest(inputs / "stations.txt")
        row["scope"] = "Captured catalog identity only; not proof of unchanged historical site or homogeneous climate record"
        write_json(output / "station.json", row)
        seal("station")
        return row

    if station_first:
        station = station_branch()
        groups = quality_branch()
    else:
        groups = quality_branch()
        station = station_branch()
    monthly = []
    for year in policy["years"]:
        for month in range(1, 13):
            for element in policy["elements"]:
                rows = [r for r in daily if r["date"].startswith(f"{year}-{month:02}") and r["element"] == element]
                values = [float(r["value"]) for r in rows if r["usable"]]
                coverage = len(values) / len(rows)
                observed = (sum(values) if element == "PRCP" else sum(values) / len(values)) if values else None
                eligible = coverage >= policy["minimum_coverage"]
                metric = observed if eligible else None
                monthly.append(dict(year=year, month=month, element=element, expected_days=len(rows), usable=len(values),
                    coverage=f"{coverage:.6f}", observed_statistic="" if observed is None else f"{observed:.6f}",
                    metric="" if metric is None else f"{metric:.6f}", status="screened_observed_only" if eligible else "insufficient_coverage",
                    units="mm observed sum" if element == "PRCP" else "C observed daily mean"))
    write_csv(output / "monthly.csv", monthly, list(monthly[0]))
    seal("aggregate")
    by_month = {(r["month"], r["element"]):r for r in monthly if r["year"] == 2024}
    monthly_rows = []
    for month in range(1, 13):
        t, p = by_month[(month, "TAVG")], by_month[(month, "PRCP")]
        monthly_rows.append([month, t["usable"], float(t["metric"]) if t["metric"] else None, t["status"],
                             p["usable"], float(p["metric"]) if p["metric"] else None, p["status"]])
    notes = [
        ["Authority", "QC-2024.2 approved 2026-10-20 16:00 UTC. Older80% and later unapproved95%/zero-fill proposals are not active.90% is internal screening policy, not a NOAA standard."],
        ["Station", f"{station['id']} / {station['name']}; {station['latitude']}, {station['longitude']}; elevation {station['elevation']}m. Current captured catalog, not historical relocation metadata."],
        ["Missing and QA", "-9999 and absent monthly records remain missing; nonblank QFLAG rejected. MFLAG/SFLAG are preserved and do not by themselves imply a failed quality test."],
        ["Meaning", "PRCP is sum of observed accepted values only, never an imputed complete-month total. Temperatures are means over accepted observations. Low-coverage metric cells remain empty, not zero."],
        ["TAVG", "Source-S TAVG uses hourly values ending2400UTC; not TAXN=(TMAX+TMIN)/2 or necessarily local-day average. Preserve source/day convention."],
        ["Limits", "1989 is a QA audit window;2024 is the reporting window. No annual complete precipitation total, warming trend, forecast, causal or homogeneous-record claim."],
        ["Workflow", "ingest -> quality and station -> aggregate -> finalize. Both branches are required; upstream bytes/policy/source changes invalidate descendant receipts. Receipts are not unforgeable execution attestations."],
        ["Reproduce", "python analysis.py --inputs /app/input_files --output /app/output. Optional --station-first changes branch order only. Actual logs are required for execution claims."],
        ["Source", "NOAA GHCNd product page, supplied readme.txt, station catalog and station data snapshots. Use exact supplied bytes; live downloads can change. No NOAA endorsement or independent climate review."],
    ]
    office = runpy.run_path(str(inputs / "office_tools.py"))
    office["workbook"](output / "handoff.xlsx", [
        ("QA", ["Year", "Element", "Calendar days", "Usable", "Missing", "Rejected", "Absent-record days"],
         [[r[k] for k in ("year", "element", "calendar_days", "usable", "missing", "rejected", "absent_month_days")] for r in groups], [14, 14, 22, 17, 17, 17, 25]),
        ("Report2024", ["Month", "TAVG N", "TAVG mean C", "TAVG screening", "PRCP N", "PRCP observed mm", "PRCP screening"], monthly_rows, [12, 14, 20, 31, 14, 24, 31]),
        ("Handoff", ["Topic", "Decision / boundary"], notes, [23, 115])],
        cell_indent=1, rows_per_page=None, number_formats={"Report2024":{"C":"0.00", "F":"0.00"}})
    seal("finalize")
    print(json.dumps(dict(daily_rows=len(daily), monthly_rows=len(monthly), qa_groups=len(groups), completed=True)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--station-first", action="store_true")
    args = parser.parse_args()
    analyze(args.inputs, args.output, args.station_first)
