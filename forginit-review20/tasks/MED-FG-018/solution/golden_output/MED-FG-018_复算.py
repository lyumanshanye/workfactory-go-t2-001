"""Reproducible analysis of frozen openFDA enforcement batches, not clinical advice."""

import argparse
import calendar
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def read_batch(path, month):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    page = data["meta"]["results"]
    records = data["results"]
    if not isinstance(records, list) or not records:
        raise ValueError("nonempty record batch required")
    for key in ("skip", "limit", "total"):
        if type(page[key]) is not int or page[key] < 0:
            raise ValueError("invalid pagination metadata")
    if page["skip"] != 0 or len(records) != page["total"] or len(records) > page["limit"]:
        raise ValueError("incomplete batch: do not claim full monthly coverage")
    year, number = int(month[:4]), int(month[4:])
    start = datetime(year, number, 1)
    end = datetime(year, number, calendar.monthrange(year, number)[1])
    seen = set()
    for row in records:
        for key in ("recall_number", "event_id", "classification", "status", "report_date", "recall_initiation_date"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError("required identity or grouping field missing: " + key)
        date = datetime.strptime(row["report_date"], "%Y%m%d")
        if len(row["report_date"]) != 8 or not start <= date <= end:
            raise ValueError("report date outside the commissioned month")
        datetime.strptime(row["recall_initiation_date"], "%Y%m%d")
        if len(row["recall_initiation_date"]) != 8:
            raise ValueError("invalid initiation date")
        if row.get("product_type") != "Devices":
            raise ValueError("not a medical-device enforcement record")
        if row["recall_number"] in seen:
            raise ValueError("duplicate recall_number requires review, not silent overwrite")
        seen.add(row["recall_number"])
    return data


def month_metrics(records, month=None):
    groups = defaultdict(list)
    for row in records:
        groups[row["event_id"]].append(row)
    classes = dict(sorted(Counter(row["classification"] for row in records).items()))
    statuses = dict(sorted(Counter(row["status"] for row in records).items()))
    return {
        "records": len(records), "recall_numbers": len({row["recall_number"] for row in records}),
        "events": len(groups), "classes": classes, "statuses": statuses,
        "class_i_records_share": classes.get("Class I", 0) / len(records),
        "events_with_class_i": sum(any(row["classification"] == "Class I" for row in rows) for rows in groups.values()),
        "multi_record_events": sum(len(rows) > 1 for rows in groups.values()),
        "initiated_before_report_month": sum(row["recall_initiation_date"] < month + "01" for row in records) if month else None,
        "mixed_class_events": sorted(k for k, rows in groups.items() if len({row["classification"] for row in rows}) > 1),
        "event_rows": [{"event_id": key, "records": len(rows),
                        "recall_numbers": sorted(row["recall_number"] for row in rows),
                        "classes": sorted({row["classification"] for row in rows}),
                        "statuses": sorted({row["status"] for row in rows}),
                        "first_report": min(row["report_date"] for row in rows),
                        "last_report": max(row["report_date"] for row in rows)}
                       for key, rows in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))],
    }


def analyze(january, february):
    jan, feb = january["results"], february["results"]
    a, b = {x["event_id"] for x in jan}, {x["event_id"] for x in feb}
    ids_a, ids_b = {x["recall_number"] for x in jan}, {x["recall_number"] for x in feb}
    if ids_a & ids_b:
        raise ValueError("same recall_number occurs in disjoint report-month batches")
    return {"months": {"202401": month_metrics(jan, "202401"), "202402": month_metrics(feb, "202402")},
            "union_records": len(jan) + len(feb), "union_events": len(a | b),
            "shared_events": sorted(a & b),
            "limitations": "Report-month counts in supplied snapshots only. Not initiation-month incidence, a historical status archive, a lifecycle monitor, device prevalence, patient risk, or permission to resume use."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("/app/input_files"))
    args = parser.parse_args()
    jan = read_batch(args.input_dir / "202401_官方召回快照.json", "202401")
    feb = read_batch(args.input_dir / "202402_官方召回快照.json", "202402")
    print(json.dumps(analyze(jan, feb), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
