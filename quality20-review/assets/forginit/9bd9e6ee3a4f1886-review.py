"""Match exercise cases to supplied recall text, not to clinical disposition."""

import argparse
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
NDC = re.compile(r"\b\d{4,5}-\d{3,4}-\d{1,2}\b")
LOT = re.compile(r"\bLot\s*(?:number\s*)?#?\s*:?\s*([A-Z0-9]+)\b", re.I)


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scope(record):
    description, codes = record["product_description"], record["code_info"]
    original_ndc = re.search(r"Original NDC\s+(\d+-\d+-\d+)", description)
    repack_ndc = re.search(r"Repack NDC\s+(\d+-\d+-\d+)", description)
    original_lot = re.search(r"Original Lot #\s*(\w+)", codes)
    repack_lot = re.search(r"Repackaged Lot #\s*(\w+)", codes)
    if any((original_ndc, repack_ndc, original_lot, repack_lot)):
        if not all((original_ndc, repack_ndc, original_lot, repack_lot)):
            raise ValueError("incomplete original/repack pairing; manual source review required")
        pairs = [(original_ndc[1], original_lot[1], "original"), (repack_ndc[1], repack_lot[1], "repack")]
        return dict(kind="paired", ndcs=[p[0] for p in pairs], pairs=pairs)
    ndcs = sorted(set(NDC.findall(description)))
    if not ndcs:
        raise ValueError("no explicit package NDC in selected record")
    if re.search(r"\ball lots\b", codes, re.I):
        if codes.strip().casefold() == "all lots":
            return dict(kind="all_lots", ndcs=ndcs, expiry_through=None)
        if codes.strip().casefold() == "all lots, expiry on or before august 2023":
            return dict(kind="all_lots", ndcs=ndcs, expiry_through="2023-08")
        raise ValueError("unhandled qualified all-lots scope")
    lots = sorted(set(LOT.findall(codes)))
    if not lots:
        raise ValueError("selected record has no supported explicit lot expression")
    return dict(kind="explicit_lots", ndcs=ndcs, lots=lots)


def match(case, record, policy):
    parsed = scope(record)
    ndc, lot = case.get("ndc"), case.get("lot")
    if not isinstance(ndc, str) or not NDC.fullmatch(ndc):
        return "undetermined", "包装标识缺失或格式不同，不能删前导零或猜补位"
    ndcs = list(parsed["ndcs"])
    if policy["use_harmonized_scope"]:
        ndcs += record.get("openfda", {}).get("package_ndc", [])
    if ndc not in ndcs:
        return "not_evidenced_here", "本条召回正文未列该包装NDC；不构成整体无召回或用药放行证明"
    if policy["exclude_terminated"] and record["status"] == "Terminated":
        return "not_evidenced_here", "按所选演练旧口径排除Terminated；需核对所选版本是否获准"
    if not isinstance(lot, str) or not lot:
        return "undetermined", "缺批号，不能确认正文范围命中"
    if parsed["kind"] == "paired":
        pairs = parsed["pairs"]
        if policy["pair_original_repack"]:
            found = any(ndc == n and lot == code for n, code, _ in pairs)
        else:
            found = lot in {p[1] for p in pairs}
        return ("text_scope_match", "包装与批号按原包装/再包装原文配对命中") if found else ("not_evidenced_here", "包装与批号未形成正文给出的对应配对")
    if parsed["kind"] == "all_lots":
        bound = parsed["expiry_through"]
        expiry = case.get("expiry_month")
        if bound and (not isinstance(expiry, str) or not re.fullmatch(r"\d{4}-(?:0[1-9]|1[0-2])", expiry)):
            return "undetermined", "All lots附有效期上界；缺有效期不能当无条件全部批次"
        found = not bound or expiry <= bound
        return ("text_scope_match", "命中正文All lots及其有效期限制") if found else ("not_evidenced_here", "有效期晚于正文All lots的限定范围")
    return ("text_scope_match", "包装NDC和明确列示批号均命中") if lot in parsed["lots"] else ("not_evidenced_here", "批号未列在本条正文中；不外推为其他记录也不涉及")


def calculate(inputs, skills):
    dataset = load(inputs / "drug-enforcement.json")
    records = dataset["results"]
    page = dataset["meta"]["results"]
    if page != dict(skip=0, limit=1000, total=len(records)):
        raise ValueError("complete captured query required")
    if any(r["product_type"] != "Drugs" or not "20240101" <= r["report_date"] <= "20240229" for r in records):
        raise ValueError("wrong domain or report-date scope")
    by_id = {r["recall_number"]: r for r in records}
    if len(by_id) != len(records):
        raise ValueError("duplicate recall number")
    policy_file = skills / "recall-text-review" / "policy.json"
    skill_file = skills / "recall-text-review" / "SKILL.md"
    policies = load(policy_file)
    approvals = load(inputs / "approval-events.json")
    cutoff = datetime.fromisoformat(policies["cutoff"])
    valid = [e for e in approvals["events"] if e["role"] == policies["authorized_role"]
             and datetime.fromisoformat(e["occurred_at"]) <= cutoff
             and datetime.fromisoformat(e["received_at"]) <= cutoff]
    approved = max(valid, key=lambda e: datetime.fromisoformat(e["received_at"]))
    policy = policies["versions"][approved["version"]]
    project = load(inputs / "review-cases.json")
    selected = project["selected_recalls"]
    if len(selected) != len(set(selected)) or any(n not in by_id for n in selected):
        raise ValueError("invalid explicit review selection")
    evidence = []
    for number in selected:
        raw = by_id[number]
        delay = (datetime.strptime(raw["report_date"], "%Y%m%d") - datetime.strptime(raw["recall_initiation_date"], "%Y%m%d")).days
        evidence.append(dict(recall_number=number, event_id=raw["event_id"], product_description=raw["product_description"],
            code_info=raw["code_info"], classification=raw["classification"], status_label_as_supplied=raw["status"],
            initiation_date=raw["recall_initiation_date"], report_date=raw["report_date"],
            termination_date_as_supplied=raw.get("termination_date"), initiation_to_report_days=delay,
            parsed_scope=scope(raw), reason_for_recall=raw["reason_for_recall"]))
    cases = []
    for case in project["cases"]:
        if case["candidate_recall"] not in selected:
            raise ValueError("case refers outside selected scope")
        raw = by_id[case["candidate_recall"]]
        decision, reason = match(case, raw, policy)
        priority = "P3" if decision == "not_evidenced_here" else "P1" if raw["classification"] == "Class I" else "P2"
        deadline = cutoff + timedelta(hours=policy["deadline_hours"][priority])
        cases.append(dict(**case, decision=decision, reason=reason, priority=priority,
            deadline_utc=deadline.isoformat(), owner="资料复核负责人", clinical_release_authorized=False,
            status_label_as_supplied=raw["status"], classification=raw["classification"]))
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("duplicate exercise case id")
    return dict(approved_version=approved["version"], cutoff=policies["cutoff"],
        data_last_updated_as_supplied=dataset["meta"]["last_updated"], source_captured_at=project["source_captured_at"],
        raw_record_count=len(records), raw_class_counts=dict(Counter(r["classification"] for r in records)),
        raw_status_label_counts=dict(Counter(r["status"] for r in records)), raw_unique_event_count=len({r["event_id"] for r in records}),
        selected_count=len(selected), selected_unique_events=len({by_id[n]["event_id"] for n in selected}),
        evidence=evidence, cases=cases, case_decision_counts=dict(Counter(r["decision"] for r in cases)),
        priority_counts=dict(Counter(r["priority"] for r in cases)),
        openfda_harmonization_used_as_scope=policy["use_harmonized_scope"], clinical_release_authorized=False,
        public_alert_issued=False, actual_inventory_available=False,
        attribution="Data provided by the U.S. Food and Drug Administration (https://open.fda.gov). Original data-review exercise, not FDA endorsement.",
        source_limitations="Captured text only; status labels are not a verified lifecycle or present safety determination. No clinical or public alert decisions.",
        input_hashes={n:sha(inputs/n) for n in ("drug-enforcement.json","approval-events.json","review-cases.json","office_tools.py")},
        skill_hashes={"SKILL.md":sha(skill_file),"policy.json":sha(policy_file)})


def run(inputs, output, skills):
    sys.path.insert(0, str(inputs))
    import office_tools

    report = calculate(inputs, skills)
    output.mkdir(parents=True, exist_ok=True)
    (output / "review.json").write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    if Path(__file__).resolve() != (output / "review.py").resolve():
        (output / "review.py").write_bytes(Path(__file__).read_bytes())
    labels = dict(text_scope_match="召回正文范围命中",not_evidenced_here="本条正文不足以支持命中",undetermined="信息不足，待核")
    case_rows = [[c["id"],c["candidate_recall"],c.get("ndc"),c.get("lot"),c.get("expiry_month"),labels[c["decision"]],c["reason"]] for c in report["cases"]]
    evidence_rows = [[r["recall_number"],r["event_id"],r["classification"],r["status_label_as_supplied"],r["code_info"]] for r in report["evidence"]]
    dates = [[r["recall_number"],r["initiation_date"],r["report_date"],r["initiation_to_report_days"],r["termination_date_as_supplied"] or "原记录未给"] for r in report["evidence"]]
    todo = [[c["id"],c["priority"],c["deadline_utc"],c["owner"],"复核原文及凭证；不据本表作患者处置或实际放行"] for c in report["cases"] if c["decision"] != "not_evidenced_here"]
    office_tools.workbook(output/"review.xlsx",[
        ("逐例范围核对",["案例","候选召回","案例包装NDC","批号","有效期月份","核对结果","判断依据"],case_rows,[10,18,20,18,16,30,48]),
        ("原始批号证据",["召回编号","事件编号","分类原值","状态标签原值","批号原文，须连同产品描述核对"],evidence_rows,[20,15,14,18,100]),
        ("时间信息",["召回编号","发起日期","报告日期","两日相差天数","终止日期原值"],dates,[23,20,20,22,24]),
        ("内部资料待办",["案例","优先级","资料复核时限UTC","负责人","下一步"],todo,[12,15,34,25,64])],rows_per_page=7)
    sections=[("本轮做了什么",[f"按{report['approved_version']}复核，截点{report['cutoff']}。原始查询含{report['raw_record_count']}条药品记录、{report['raw_unique_event_count']}个事件；本轮选{report['selected_count']}条，涉及{report['selected_unique_events']}个事件。演练案例与真实库存分开。",
        "案例结果："+"；".join(labels[k]+str(v)+"例" for k,v in report["case_decision_counts"].items())+"。命中仅指文字范围，不证明院内持有受影响药品，也不构成患者用药或库存放行决定。"]),
        ("必须改正的旧稿",["原包装与再包装NDC、批号须按各自来源配对，不做所有包装乘所有批号。补充openfda.package_ndc是标识关联，不替代召回产品正文；没有补充字段也不能删除原始记录。All lots附有效期上界时必须连同限制判断。",
        "发起日期不是报告日期；报告在2024年不代表召回也在2024年发起。状态标签、termination_date原值、接口last_updated与本次捕获时间分别保留，不能拼成已经核实的生命周期。Completed或Terminated标签都不自动授权恢复使用。"]),
        ("后续交接",["内部待办按演练SOP排资料核对优先级和UTC时限，不是医疗处置时限或法规要求。资料负责人补原始公告及更新范围，库存负责人提供真实包装/批号/有效期凭证，药事与质量负责人依据一手通知及院内程序作后续决定。没有这些凭证不捏造库存和接触患者情况。",
        "来源openFDA官方说明明确不应用本数据作临床决策、公众警报或追踪召回生命周期。当前只交内部可复算资料核对，不联系厂家或患者、不实际发布、不改变召回状态。"]),
        ("复跑与署名",["运行python review.py --inputs INPUT --output OUTPUT --skills SKILLS。结果来自固定原始JSON和本项目技能，输入不改写。Data provided by the U.S. Food and Drug Administration (https://open.fda.gov). 原创演练，不代表FDA背书。"])]
    office_tools.document(output/"handoff.docx","药品召回材料核对：范围与待办交接",sections)
    print(json.dumps({k:report[k] for k in ("selected_count","raw_record_count","case_decision_counts","priority_counts")},ensure_ascii=False))


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--inputs",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--skills",type=Path,required=True)
    a=p.parse_args()
    run(a.inputs,a.output,a.skills)
