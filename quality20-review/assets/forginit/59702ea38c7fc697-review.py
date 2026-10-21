"""Bounded review of supplied settings and design specifications, not a build."""

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

REQUIRED_INPUTS = (
    "project.json", "approval-events.json", "settings.json", "spacing-draft.json",
    "component-states.json", "migration.html", "spacing.html", "office_tools.py",
)


SKILL = """---
name: uswds-migration-review
description: Review USWDS 2-to-3 migration settings and design-token specifications against supplied official guidance and project approvals; use for migration preparation, not deployment certification.
---

# USWDS migration review

Read the project brief and approval-events.json before proposing changes. Use only
an authorized version both approved and received by the cutoff. Keep unauthorized
drafts and late signatures for a later round; they do not authorize installation
of the version currently advertised on a documentation website.

Check code and settings versions independently. For each supplied setting, locate
the applicable official migration section and record its input value, proposed
action, resulting name/value, and any unresolved design decision. A recent code
package does not establish that its settings or custom markup are current.

For output-all-utilities=false, replace the switch with a list of modules justified
by actual class inventory and the official module table. For true, remove the old
switch; this does not approve publishing or including all components. Shared class
prefixes may require further inspection; do not invent a unique module mapping.

When applicable, rename theme-site-max-width to theme-grid-container-max-width
without changing its value. Obsolete input-tile settings cannot preserve custom
colors merely by remaining in a file: identify custom intent for the design lead
to resolve and include input--tile in the visual test inventory. Distinguish these
from obsolete default values. For changed defaults, remove overrides equal to an
official old/new default; retain genuine custom values for review. Where several
historical default changes cover one field, use the latest applicable section for
the target migration rather than overwriting it with an earlier historical default.

Read spacing tokens from spacing.html, preserving numeric/string aliases and their
documented nominal px values. In particular, a leading zero in a string token is
not a decimal number. Do not synthesize negative or named tokens absent from the
table. Compare dated guidance changes before adopting an old note. Nominal px is
not evidence of a pinned package's output or a browser's physical dimensions.

Use project.json required_states to audit which component/state specifications
were actually supplied. A missing disabled/selected state stays missing; a normal
state cannot stand in for it. Supplied specifications are not passed browser tests.

Run review.py --inputs INPUT --output OUTPUT for a reproducible evidence table;
inspect the official HTML when the script flags unknown data or a rule outside its
bounded scope. The helper does not compile Sass, inspect a live site, or establish
compatibility of later 3.x releases. Before release, the engineer must supply the
pinned package/lock/build and browser evidence, the design lead must resolve custom
visual changes, and the release owner must make a new authorized decision. Continue
justified review work while those items are pending. Do not modify inputs, contact
external parties, install packages, deploy or claim approval through this skill.
"""


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(node):
    return " ".join(node.text_content().split())


def unquote(value):
    return value.strip().strip('"').strip("'")


def read_sources(inputs):
    from lxml import html
    from packaging.version import Version

    guide = html.fromstring((inputs / "migration.html").read_bytes())
    spacing = html.fromstring((inputs / "spacing.html").read_bytes())
    changes, modules = {}, []
    for table in guide.xpath("//main//table"):
        rows = table.xpath(".//tr")
        headers = [text(c) for c in rows[0].xpath("./th|./td")]
        if headers == ["Setting", "Old default", "New default"]:
            heading = table.xpath("preceding::h4[1]")[0]
            threshold = Version(re.search(r"older than USWDS ([0-9.]+)", text(heading))[1])
            for row in rows[1:]:
                cells = [unquote(text(c)) for c in row.xpath("./th|./td")]
                field, old, new = cells
                changes.setdefault(field, []).append((threshold, old, new))
        elif headers[:2] == ["Utility module name", "Class base"]:
            for row in rows[1:]:
                cells = [text(c) for c in row.xpath("./th|./td")]
                modules.append((cells[0], cells[1]))
    obsolete = {}
    section = guide.get_element_by_id("settings-update-three-deprecated-settings")
    for code in section.xpath("following-sibling::ul[1]//code"):
        field, value = text(code).split(":", 1)
        obsolete[field] = unquote(value)
    tokens = {}
    for row in spacing.xpath("//table")[0].xpath(".//tr")[1:]:
        cells = row.xpath("./th|./td")
        nominal = int(text(cells[2]).removesuffix("px"))
        for alias in cells[0].xpath(".//code"):
            tokens[unquote(text(alias))] = nominal
    if not changes or not modules or len(obsolete) != 3 or tokens.get("tablet-lg") != 880:
        raise ValueError("official source structure changed; review before using these rules")
    return changes, modules, obsolete, tokens


def calculate(inputs):
    from packaging.version import Version

    project = load(inputs / "project.json")
    approvals = load(inputs / "approval-events.json")
    cutoff = datetime.fromisoformat(approvals["cutoff"])
    valid = [e for e in approvals["events"] if e["role"] == approvals["authorized_role"]
             and datetime.fromisoformat(e["occurred_at"]) <= cutoff
             and datetime.fromisoformat(e["received_at"]) <= cutoff]
    chosen = max(valid, key=lambda e: datetime.fromisoformat(e["received_at"]))
    policy = approvals["versions"][chosen["version"]]
    settings_version = Version(project["settings_version"])
    changes, modules, obsolete, tokens = read_sources(inputs)
    used_modules, unresolved_classes = set(), []
    for class_name in project["utility_classes"]:
        matches = sorted({module for module, base in modules if class_name.startswith(base)})
        if len(matches) == 1:
            used_modules.add(matches[0])
        else:
            unresolved_classes.append(dict(class_name=class_name, candidate_modules=matches))
    used_modules = sorted(used_modules)
    settings = []
    for field, value in load(inputs / "settings.json").items():
        action, target, proposed, basis = "retain", field, value, "没有在本范围内识别到强制修改；不等于完整兼容认证"
        if field == "$output-all-utilities":
            target = "$output-these-utilities" if value is False else None
            proposed = used_modules if value is False else None
            action, basis = "replace_list" if value is False else "remove_switch", "所有迁移：旧开关改模块名单或移除"
        elif field == "$theme-site-max-width" and settings_version < Version("2.11.2"):
            action, target, basis = "rename", "$theme-grid-container-max-width", "设置早于2.11.2：改名但保留原值"
        elif field in obsolete and settings_version < Version("2.12.0"):
            action = "review_custom" if str(value) != obsolete[field] else "remove_obsolete"
            target, proposed, basis = None, None, "设置早于2.12.0：input-tile设置已不可设置；自定义意图须单列决定"
        elif field in changes:
            applicable = sorted((row for row in changes[field] if settings_version < row[0]), reverse=True)
            if applicable:
                threshold, old, new = applicable[0]
                if str(value) in (old, new):
                    action, target, proposed = "remove_default", None, None
                basis = f"设置早于{threshold}；旧默认{old}，该节新默认{new}；自定义值不一律替换"
        settings.append(dict(field=field, value=value, action=action, target=target, proposed=proposed, basis=basis))
    spacing = []
    for row in load(inputs / "spacing-draft.json"):
        key = str(row["token"])
        nominal = tokens.get(key)
        spacing.append(dict(id=row["id"], token=row["token"], draft_px=row["draft_px"], nominal_px=nominal,
                            status="unknown_token" if nominal is None else "same" if nominal == row["draft_px"] else "correct"))
    supplied = {(r["component"], r["state"]):r["specification"] for r in load(inputs / "component-states.json")}
    states = [dict(component=c, state=s, status="specified" if (c,s) in supplied else "missing_spec",
                   specification=supplied.get((c,s))) for c, required in project["required_states"].items() for s in required]
    return dict(approved_version=chosen["version"], approved_target=policy["target"], cutoff=approvals["cutoff"],
        code_version=project["code_version"], settings_version=project["settings_version"],
        settings=settings, modules=used_modules, unresolved_classes=unresolved_classes, spacing=spacing, states=states,
        custom_decisions=[s["field"] for s in settings if s["action"] == "review_custom"],
        missing_states=[r["component"]+"/"+r["state"] for r in states if r["status"] == "missing_spec"],
        markup_step_required_by_version=Version(project["code_version"]) < Version("2.13.0"),
        publication_ready=False, compiled=False, browser_tested=False,
        source_scope="3.0迁移准备 + 当前间距文档标称值；不证明固定3.0包的实际渲染或其他3.x兼容性",
        input_hashes={name:sha(inputs / name) for name in REQUIRED_INPUTS})


def run(inputs, output):
    sys.path.insert(0, str(inputs))
    import office_tools

    report = calculate(inputs)
    output.mkdir(parents=True, exist_ok=True)
    (output / "decisions.json").write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)+"\n")
    (output / "SKILL.md").write_text(SKILL)
    source, destination = Path(__file__).resolve(), output / "review.py"
    if source != destination.resolve():
        destination.write_bytes(source.read_bytes())
    actions = dict(retain="保留自定义值", replace_list="替换为实际模块名单", remove_switch="移除旧开关",
                   rename="字段改名，原值保留", review_custom="需设计确认替代方案",
                   remove_obsolete="移除已失效的默认设置", remove_default="移除默认覆盖")
    def readable_result(setting):
        if setting["action"] == "review_custom":
            return "旧字段已失效；先记录自定义意图，待设计确定替代方式"
        if setting["target"] is None:
            return "删除此字段；不额外写入替代值"
        return setting["target"]+" = "+json.dumps(setting["proposed"],ensure_ascii=False)
    settings_rows = [[s["field"],json.dumps(s["value"],ensure_ascii=False),actions[s["action"]],
                      readable_result(s),s["basis"]] for s in report["settings"]]
    spacing_labels = dict(unknown_token="当前文档无此token，待确认", same="旧稿值正确", correct="按当前表更正")
    spacing_rows = [[r["id"],json.dumps(r["token"],ensure_ascii=False),r["draft_px"],r["nominal_px"],spacing_labels[r["status"]]] for r in report["spacing"]]
    state_rows = [[r["component"],r["state"],"已有说明，尚未测试" if r["status"] == "specified" else "缺少状态说明",
                   r["specification"] or "请设计负责人补说明；不能复制普通状态代替"] for r in report["states"]]
    handoff = [["工程", "批准目标"+report["approved_target"], "锁包/锁文件、Sass构建和资产路径证据尚缺，不运行npm latest"],
               ["工程", "工具类归属", "待检查："+json.dumps(report["unresolved_classes"],ensure_ascii=False) if report["unresolved_classes"] else "当前清单各类名均可由官方表唯一映射；不是完整CSS兼容认证"],
               ["设计", "自定义覆盖", "待决定："+"；".join(report["custom_decisions"])],
               ["设计/测试", "状态说明", "待补："+"；".join(report["missing_states"])+"；全部仍未实际浏览器测试"],
               ["发布负责人", "本轮只复核不发布", "补证完成后另行审批；已提供状态说明不等于通过无障碍认证"]]
    office_tools.workbook(output/"migration.xlsx",[
        ("设置处置",["原字段","原值","动作","建议结果","依据/条件"],settings_rows,[43,22,22,45,48]),
        ("间距校对",["编号","token原值","旧稿px","当前标称px","处置"],spacing_rows,[12,23,16,18,25]),
        ("状态覆盖",["组件","状态","材料覆盖","已有说明/补证"],state_rows,[18,19,22,65]),
        ("执行交接",["责任角色","事项","完成条件"],handoff,[22,28,90])],rows_per_page=6)
    sections=[("本轮结论",[f"采用{report['approved_version']}，批准目标{report['approved_target']}；代码{report['code_version']}与配置{report['settings_version']}分别判断。本轮交迁移准备审查，不对外发布，不声称完成构建或浏览器测试。"]),
        ("已可确定的更正",["逐项设置决定见工作簿和JSON。旧utilities开关按实际类名确定模块："+"、".join(report["modules"])+"；旧宽度字段改名不能擅自放大。已失效的自定义input-tile覆盖需设计负责人决定替代，不可删除后声称视觉不变。",
           "当前间距文档tablet-lg为880px；2022-02-24曾改800，2022-03-11又恢复880。字符串05为4px标称值，数字2为16px；未知token不能猜。表中标称px不等于任意根字号下的实际像素。"]),
        ("为什么尚不能放行",["缺少状态说明："+"、".join(report["missing_states"])+"。已有说明也不是实际截图或已通过的测试。代码包较新不能证明配置同步或自定义markup无问题；指南关于3.0/2.13.3的表述不能覆盖全部3.x。",
           "审批按发生和收到时间均不晚于截点、具备负责人权限筛选；不倒填晚到签字。工程提供固定包/锁文件、编译和浏览器证据，设计负责人补自定义与状态决策，发布负责人据新证据另行审批。"]),
        ("复跑与来源",["运行python review.py --inputs INPUT --output OUTPUT。SKILL.md供同类审查复用，不自动安装为全局技能，不授权联网安装、改输入或发布。",
           "官方USWDS迁移/间距HTML实际取得于2026-10-21；旧笔记、项目、审批和状态为原创演练。当前文档不是2022网页快照，也不是固定3.0包的运行证据；独立专业/权利与正式验收未完成。"])]
    office_tools.document(output/"handoff.docx","USWDS迁移准备：设计与工程交接",sections)
    print(json.dumps(dict(settings=len(report["settings"]),spacing=len(report["spacing"]),missing_states=report["missing_states"],custom_decisions=report["custom_decisions"]),ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    run(args.inputs,args.output)
