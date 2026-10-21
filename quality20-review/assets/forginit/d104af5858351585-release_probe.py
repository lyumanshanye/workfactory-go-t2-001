"""Inspect actual supplied pages/files and validate an offline review candidate."""

import argparse
import hashlib
import json
from pathlib import Path

from lxml import html


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(inputs, policy):
    ledger = json.loads((inputs / "procurement-ledger.json").read_text())
    rows = []
    for item in ledger["assets"]:
        page = html.fromstring((inputs / item["page"]).read_bytes())
        def field(name):
            nodes = page.xpath('//*[contains(concat(" ",normalize-space(@class)," "), $name)]',
                               name=" field-name-" + name + " ")
            if len(nodes) != 1:
                raise ValueError("missing/ambiguous original source field: " + name)
            return " ".join(nodes[0].text_content().split())
        licenses = field("field-art-licenses")
        body = field("body")
        author = field("author-submitter")
        filename = item["filename"]
        actual = inputs / filename
        observed = "CC0" if "CC0" in licenses else "CC-BY 3.0" if "CC-BY 3.0" in licenses else None
        if not actual.is_file():
            decision, reason = "hold", "missing_file_and_scope"
        elif observed is None:
            decision, reason = "hold", "unrecognized_license"
        elif observed != item["ledger_license"] and policy["conflict_rule"] == "hold":
            decision, reason = "hold", "ledger_source_conflict"
        elif observed not in policy["allowed_licenses"]:
            decision, reason = "hold", "license_out_of_scope"
        else:
            decision, reason = "eligible", "source_and_ledger_consistent"
        rows.append(dict(id=item["id"], filename=filename, decision=decision, reason=reason,
                         source_license=observed, offered_licenses=licenses, author=author,
                         source_url=item["source_url"], sha256=sha(actual) if actual.is_file() else None,
                         source_sha256=sha(inputs / item["page"]), body=body))
    return rows


def validate(candidate, rows, policy):
    expected = {r["id"]: r for r in rows if r["decision"] == "eligible"}
    holds = sorted(r["id"] for r in rows if r["decision"] == "hold")
    if (candidate.get("status") != "prepared_for_human_review" or
            candidate.get("approved_policy") != policy["version"] or
            candidate.get("holds") != holds or candidate.get("published") is not False):
        raise ValueError("status, approval or hold list differs from approved policy")
    selected = candidate.get("selected", [])
    if (not isinstance(selected, list) or any(not isinstance(x, dict) for x in selected)
            or len(selected) != len(expected) or {x.get("id") for x in selected} != set(expected)):
        raise ValueError("selected asset set differs from eligible inventory")
    for item in selected:
        row = expected[item["id"]]
        for key in ("filename", "sha256", "source_license", "source_url"):
            if item.get(key) != row[key]:
                raise ValueError("selected asset mismatch: " + key)
        if item.get("modifications") != "none":
            raise ValueError("this commission permits only unmodified review assets")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=Path(__file__).with_name("approved-policy.json"))
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text())
    if policy.get("version") != "V2" or policy.get("allow_partial_review") is not True:
        raise ValueError("not an approved V2 policy")
    rows = inspect(args.inputs, policy)
    if args.candidate:
        validate(json.loads(args.candidate.read_text()), rows, policy)
    report = dict(rows=rows, candidate_checked=bool(args.candidate), passed=True,
                  candidate_sha256=sha(args.candidate) if args.candidate else None,
                  probe_sha256=sha(Path(__file__)), policy_sha256=sha(args.policy),
                  ledger_sha256=sha(args.inputs / "procurement-ledger.json"),
                  limitation="Byte/policy checks only; no rights approval or publication")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(passed=True, inspected=len(rows), eligible=sum(r["decision"] == "eligible" for r in rows))))


if __name__ == "__main__":
    main()
