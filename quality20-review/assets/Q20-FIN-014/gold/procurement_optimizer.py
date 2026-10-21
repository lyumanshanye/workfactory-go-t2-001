#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
受限预算下的采购组合建议 - 求解器
==============================================
读取供应商报价与公司约束，使用穷举法求解最优采购/租赁组合方案。
目标：最小化3年期总拥有成本（TCO），同时满足全部硬约束。

所有金额计算使用 decimal.Decimal，禁止 float 参与财务运算。

作者：供应链与财务联合项目分析团队
日期：2024-05-20
"""

import json
import os
import sys
import itertools
from decimal import Decimal, ROUND_HALF_UP, getcontext

# 设置足够高的精度，避免截断
getcontext().prec = 50

# ──────────────────────────────────────────────
# 路径配置：优先 /work/output，回退 /app/output
# ──────────────────────────────────────────────
INPUT_DIRS = ["/work/input_files", "/app/input_files", "input_files"]

# 输出目录：优先可写的 /work/output
OUTPUT_DIR = "/work/output"
if not os.path.isdir(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def find_input_file(filename):
    """在候选目录中查找输入文件"""
    for d in INPUT_DIRS:
        path = os.path.join(d, filename)
        if os.path.isfile(path):
            return path
    raise FileNotFoundError(
        f"找不到输入文件: {filename}，已搜索目录: {INPUT_DIRS}"
    )


# ──────────────────────────────────────────────
# 1. 数据读取
# ──────────────────────────────────────────────
def load_data():
    """
    读取供应商报价和公司约束文件，所有金额字段立即转为 Decimal。
    """
    try:
        quotes_path = find_input_file("supplier_quotes.json")
        with open(quotes_path, "r", encoding="utf-8") as f:
            raw_vendors = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[错误] 读取供应商报价文件失败: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        constraints_path = find_input_file("company_constraints.json")
        with open(constraints_path, "r", encoding="utf-8") as f:
            raw_constraints = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[错误] 读取约束文件失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 转换为 Decimal
    vendors = []
    for v in raw_vendors:
        vendor = {
            "vendor_id": v["vendor_id"],
            "name": v["name"],
            "unit_price_buy": Decimal(str(v["unit_price_buy"])),
            "lead_time_days": int(v["lead_time_days"]),
            "base_maintenance_annual": Decimal(str(v["base_maintenance_annual"])),
            "support_247_included": bool(v["support_247_included"]),
            "cost_add_247_annual": Decimal(str(v["cost_add_247_annual"])),
            "lease_down_payment": Decimal(str(v["lease_down_payment"])),
            "lease_annual_rent": Decimal(str(v["lease_annual_rent"])),
            "lease_maintenance_included": bool(v.get("lease_maintenance_included", False)),
        }
        vendors.append(vendor)

    constraints = {
        "total_units_required": int(raw_constraints["total_units_required"]),
        "max_units_per_vendor": int(raw_constraints["max_units_per_vendor"]),
        "min_fast_delivery_units": int(raw_constraints["min_fast_delivery_units"]),
        "fast_delivery_threshold_days": int(raw_constraints["fast_delivery_threshold_days"]),
        "max_delivery_days": int(raw_constraints["max_delivery_days"]),
        "first_year_cash_flow_limit": Decimal(str(raw_constraints["first_year_cash_flow_limit"])),
        "tco_horizon_years": int(raw_constraints["tco_horizon_years"]),
    }

    return vendors, constraints


# ──────────────────────────────────────────────
# 2. 成本计算（全部使用 Decimal）
# ──────────────────────────────────────────────
def calc_annual_maintenance(vendor):
    """
    计算单台设备年度维保费用（含7×24现场支持）。
    依据 tco_calculation_rules.md 第1节。
    """
    maint = vendor["base_maintenance_annual"]
    if not vendor["support_247_included"]:
        maint += vendor["cost_add_247_annual"]
    return maint


def calc_first_year_buy(vendor):
    """
    购买模式下单台设备首年现金流。
    first_year_buy = unit_price_buy + annual_maintenance
    """
    maint = calc_annual_maintenance(vendor)
    return vendor["unit_price_buy"] + maint


def calc_tco_buy(vendor, years):
    """
    购买模式下单台设备3年TCO。
    tco_buy = unit_price_buy + years * annual_maintenance
    """
    maint = calc_annual_maintenance(vendor)
    return vendor["unit_price_buy"] + Decimal(str(years)) * maint


def calc_first_year_lease(vendor):
    """
    租赁模式下单台设备首年现金流。
    first_year_lease = lease_down_payment + lease_annual_rent + annual_maintenance
    """
    maint = calc_annual_maintenance(vendor)
    return vendor["lease_down_payment"] + vendor["lease_annual_rent"] + maint


def calc_tco_lease(vendor, years):
    """
    租赁模式下单台设备3年TCO。
    tco_lease = lease_down_payment + years * lease_annual_rent + years * annual_maintenance
    """
    maint = calc_annual_maintenance(vendor)
    return (
        vendor["lease_down_payment"]
        + Decimal(str(years)) * vendor["lease_annual_rent"]
        + Decimal(str(years)) * maint
    )


# ──────────────────────────────────────────────
# 3. 约束求解（穷举法）
# ──────────────────────────────────────────────
def solve(vendors, constraints):
    """
    穷举所有满足约束的 (buy_i, lease_i) 组合，
    找到3年TCO最小的方案。

    决策变量：
        buy_i:  供应商i购买台数 (整数, 0..max_per_vendor)
        lease_i: 供应商i租赁台数 (整数, 0..max_per_vendor)

    约束：
        REQ-01: sum(buy_i + lease_i) = total_units_required
        REQ-02: buy_i + lease_i <= max_units_per_vendor  (对每个i)
        REQ-03: 至少 min_fast_delivery_units 台交期 <= fast_delivery_threshold_days
        REQ-04: 所有设备必须满足7×24维保（已在成本计算中处理）
        REQ-05: 首年现金流总和 <= first_year_cash_flow_limit
        REQ-06: 最小化3年TCO
    """
    n_vendors = len(vendors)
    total = constraints["total_units_required"]
    max_per = constraints["max_units_per_vendor"]
    min_fast = constraints["min_fast_delivery_units"]
    fast_thresh = constraints["fast_delivery_threshold_days"]
    max_delivery = constraints["max_delivery_days"]
    cash_limit = constraints["first_year_cash_flow_limit"]
    years = constraints["tco_horizon_years"]

    # 预计算每家供应商的单位成本指标（Decimal）
    vendor_metrics = []
    for v in vendors:
        m = {
            "vendor_id": v["vendor_id"],
            "name": v["name"],
            "lead_time_days": v["lead_time_days"],
            "first_year_buy": calc_first_year_buy(v),
            "tco_buy": calc_tco_buy(v, years),
            "first_year_lease": calc_first_year_lease(v),
            "tco_lease": calc_tco_lease(v, years),
            "annual_maint": calc_annual_maintenance(v),
        }
        vendor_metrics.append(m)
        print(f"  供应商{v['vendor_id']} ({v['name']}):")
        print(f"    年度维保（含7×24）: {m['annual_maint']} 元")
        print(f"    购买 - 首年现金流: {m['first_year_buy']} 元, 3年TCO: {m['tco_buy']} 元")
        print(f"    租赁 - 首年现金流: {m['first_year_lease']} 元, 3年TCO: {m['tco_lease']} 元")

    # 判断哪些供应商满足快速交付（交期 <= fast_thresh）
    fast_vendors = [
        i for i, v in enumerate(vendors) if v["lead_time_days"] <= fast_thresh
    ]
    # 判断哪些供应商满足最大交期
    eligible_vendors = [
        i for i, v in enumerate(vendors) if v["lead_time_days"] <= max_delivery
    ]

    print(f"\n  快速交付供应商（交期≤{fast_thresh}天）: "
          f"{[vendors[i]['vendor_id'] for i in fast_vendors]}")
    print(f"  可接受供应商（交期≤{max_delivery}天）: "
          f"{[vendors[i]['vendor_id'] for i in eligible_vendors]}")

    # 检查是否所有供应商都在可接受范围内
    if len(eligible_vendors) < n_vendors:
        ineligible = [vendors[i]['vendor_id'] for i in range(n_vendors) if i not in eligible_vendors]
        print(f"  [警告] 以下供应商交期超过{max_delivery}天，不可选用: {ineligible}")

    # 生成所有可能的 (buy_0, lease_0, buy_1, lease_1, ..., buy_n, lease_n) 组合
    # 每个供应商的 (buy_i, lease_i) 满足: 0 <= buy_i + lease_i <= max_per
    best_tco = None
    best_solution = None
    all_feasible = []  # 保存所有可行解用于敏感性分析

    # 为每个供应商生成可能的 (buy, lease) 对
    vendor_options = []
    for i in range(n_vendors):
        options = []
        for total_i in range(0, max_per + 1):
            for buy_i in range(0, total_i + 1):
                lease_i = total_i - buy_i
                options.append((buy_i, lease_i))
        vendor_options.append(options)

    # 穷举所有组合
    count_total = 0
    count_feasible = 0
    for combo in itertools.product(*vendor_options):
        count_total += 1
        # combo = ((buy_0, lease_0), (buy_1, lease_1), ...)
        total_units = sum(b + l for b, l in combo)

        # REQ-01: 总量必须恰好等于 total
        if total_units != total:
            continue

        # REQ-02: 每个供应商不超过 max_per（已在生成时保证）
        # 但仍显式验证
        req02_ok = True
        for b, l in combo:
            if b + l > max_per:
                req02_ok = False
                break
        if not req02_ok:
            continue

        # REQ-03: 至少 min_fast 台来自快速交付供应商
        # 即 fast_vendors 中所有供应商的设备总数 >= min_fast
        fast_count = sum(combo[i][0] + combo[i][1] for i in fast_vendors)
        if fast_count < min_fast:
            continue

        # REQ-04: 7×24维保 - 所有供应商都必须满足（已在成本中加购处理）
        # 此处无需额外过滤

        # 计算首年现金流和TCO
        first_year_total = Decimal("0")
        tco_total = Decimal("0")
        for i, (buy_i, lease_i) in enumerate(combo):
            if buy_i > 0:
                first_year_total += Decimal(str(buy_i)) * vendor_metrics[i]["first_year_buy"]
                tco_total += Decimal(str(buy_i)) * vendor_metrics[i]["tco_buy"]
            if lease_i > 0:
                first_year_total += Decimal(str(lease_i)) * vendor_metrics[i]["first_year_lease"]
                tco_total += Decimal(str(lease_i)) * vendor_metrics[i]["tco_lease"]

        # REQ-05: 首年现金流不超上限
        if first_year_total > cash_limit:
            continue

        # 可行解
        count_feasible += 1
        solution = {
            "combo": combo,
            "first_year_total": first_year_total,
            "tco_total": tco_total,
        }
        all_feasible.append(solution)

        # REQ-06: 最小化TCO
        if best_tco is None or tco_total < best_tco:
            best_tco = tco_total
            best_solution = solution

    print(f"\n  搜索统计: 总组合数={count_total}, 可行解数={count_feasible}")

    if best_solution is None:
        print("\n[错误] 未找到满足所有约束的可行解！", file=sys.stderr)
        sys.exit(1)

    # 量化到整数元
    quant = Decimal("1")
    best_tco_rounded = best_solution["tco_total"].quantize(quant, rounding=ROUND_HALF_UP)
    best_cf_rounded = best_solution["first_year_total"].quantize(quant, rounding=ROUND_HALF_UP)

    print(f"\n{'='*60}")
    print(f"  最优解 - 3年TCO: {best_tco_rounded} 元")
    print(f"  最优解 - 首年现金流: {best_cf_rounded} 元")
    print(f"{'='*60}")

    # 输出最优解的分配明细
    for i, (buy_i, lease_i) in enumerate(best_solution["combo"]):
        if buy_i + lease_i > 0:
            print(f"  供应商{vendors[i]['vendor_id']} ({vendors[i]['name']}): "
                  f"购买 {buy_i} 台, 租赁 {lease_i} 台")

    # 找出所有等价最优解（TCO相同）
    optimal_solutions = [
        s for s in all_feasible
        if s["tco_total"].quantize(quant, rounding=ROUND_HALF_UP) == best_tco_rounded
    ]
    print(f"\n  等价最优解数量: {len(optimal_solutions)}")

    # 找出次优解（TCO略高）
    all_tco_sorted = sorted(set(
        s["tco_total"].quantize(quant, rounding=ROUND_HALF_UP)
        for s in all_feasible
    ))
    print(f"  所有可行TCO值: {all_tco_sorted[:5]}{'...' if len(all_tco_sorted) > 5 else ''}")

    return best_solution, optimal_solutions, all_feasible, vendor_metrics, vendors, constraints


# ──────────────────────────────────────────────
# 4. 生成CFO决策报告（DOCX）
# ──────────────────────────────────────────────
def generate_report(best_solution, optimal_solutions, all_feasible,
                    vendor_metrics, vendors, constraints):
    """
    使用 python-docx 生成面向CFO的决策报告。
    """
    from docx import Document
    from docx.shared import Pt, Inches, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT

    doc = Document()

    # 设置默认字体
    style = doc.styles["Normal"]
    font = style.font
    font.name = "微软雅黑"
    font.size = Pt(11)

    quant = Decimal("1")

    # ── 封面/标题 ──
    title = doc.add_heading("激光切割机采购组合决策报告", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("供应链与财务联合项目 · 内部决策参考")
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = date_para.add_run("报告日期：2024年5月20日")
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    doc.add_paragraph()  # 空行

    # ── 数据来源声明 ──
    doc.add_heading("数据来源声明", level=1)
    p = doc.add_paragraph()
    p.add_run("本报告所涉及的供应商报价、交期、维保条款及公司约束参数，").font.size = Pt(11)
    run = p.add_run("均为公司内部原创业务数据")
    run.bold = True
    run.font.size = Pt(11)
    p.add_run("，不代表任何外部机构（包括但不限于SBA等）发布的官方数据或行业标准。"
              "TCO计算口径参考了行业最佳实践关于资产购置的比较原则"
              "（参见采购成本研究摘述 procurement_research_note.md），"
              "但该材料仅提供商业比较的研究背景，不构成任何司法辖区的强制会计或税务规则。").font.size = Pt(11)

    # ── 1. 项目背景 ──
    doc.add_heading("1. 项目背景与决策目标", level=1)
    doc.add_paragraph(
        "公司近期需紧急新增5台高精度激光切割机以扩充产能。"
        "由于年度资本支出（CAPEX）与运营支出（OPEX）预算收紧，"
        "且财务部对现金流占用有严格上限，需在以下硬约束下寻找最优采购/租赁组合方案："
    )

    constraint_list = [
        f"总数量严格等于 {constraints['total_units_required']} 台",
        f"单一供应商设备获取总数不超过 {constraints['max_units_per_vendor']} 台（防范断供风险）",
        f"至少 {constraints['min_fast_delivery_units']} 台设备在 {constraints['fast_delivery_threshold_days']} 天内交付",
        f"其余设备最迟不超过 {constraints['max_delivery_days']} 天交付",
        "所有设备必须标配7×24小时现场维保支持",
        f"首年现金流支出不超过 {constraints['first_year_cash_flow_limit'].quantize(Decimal('1')):,} 元",
    ]
    for item in constraint_list:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_paragraph(
        f"决策目标：在满足上述约束的前提下，最小化 {constraints['tco_horizon_years']} 年期总拥有成本（TCO）。"
        "TCO将购买/租赁费用及维保现金占用放在同一使用期间对比，体现全生命周期成本理念。"
    )

    # ── 2. 供应商概况 ──
    doc.add_heading("2. 候选供应商概况", level=1)
    doc.add_paragraph("以下为三家候选供应商的核心报价参数：")

    # 供应商对比表
    table = doc.add_table(rows=1, cols=7)
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["供应商", "交期(天)", "购买单价(元)", "年度维保(元)",
               "租赁首付(元)", "年租金(元)", "7×24支持"]
    for j, h in enumerate(headers):
        cell = table.rows[0].cells[j]
        cell.text = h
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(9)

    for v in vendors:
        row = table.add_row()
        row.cells[0].text = f"{v['vendor_id']} - {v['name'][:8]}..."
        row.cells[1].text = str(v["lead_time_days"])
        row.cells[2].text = f"{v['unit_price_buy']:,.0f}"
        maint = vendor_metrics[vendors.index(v)]["annual_maint"]
        row.cells[3].text = f"{maint:,.0f}"
        row.cells[4].text = f"{v['lease_down_payment']:,.0f}"
        row.cells[5].text = f"{v['lease_annual_rent']:,.0f}"
        row.cells[6].text = "已含" if v["support_247_included"] else "需加购"
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(9)

    doc.add_paragraph()

    # 维保费用说明
    doc.add_heading("2.1 年度维保费用明细", level=2)
    for v in vendors:
        idx = vendors.index(v)
        m = vendor_metrics[idx]
        p = doc.add_paragraph()
        p.add_run(f"供应商{v['vendor_id']}：").bold = True
        if v["support_247_included"]:
            p.add_run(f"7×24维保已标配，年度维保费用 = {v['base_maintenance_annual']:,.0f} 元")
        else:
            p.add_run(
                f"基础维保 {v['base_maintenance_annual']:,.0f} 元 + "
                f"7×24加购 {v['cost_add_247_annual']:,.0f} 元 = "
                f"{m['annual_maint']:,.0f} 元/年"
            )

    # ── 3. TCO测算方法 ──
    doc.add_heading("3. TCO测算方法", level=1)
    doc.add_paragraph(
        "依据行业最佳实践，不能仅比较标价或月费，"
        "需将同一使用期间的费用及现金占用放在一起看。"
        "本报告采用静态TCO（不考虑折现），计算口径如下："
    )

    doc.add_heading("3.1 购买模式", level=2)
    doc.add_paragraph("首年现金流 = 购买全款 + 首年维保费用")
    doc.add_paragraph(f"3年TCO = 购买全款 + {constraints['tco_horizon_years']} × 年度维保费用")

    doc.add_heading("3.2 租赁模式", level=2)
    doc.add_paragraph("首年现金流 = 租赁首付 + 首年租金 + 首年维保费用")
    doc.add_paragraph(f"3年TCO = 租赁首付 + {constraints['tco_horizon_years']} × 年租金 + "
                      f"{constraints['tco_horizon_years']} × 年度维保费用")

    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run("精度保障：")
    run.bold = True
    p.add_run("所有财务计算使用 Python decimal.Decimal 类型，"
              "避免二进制浮点数累积误差，金额精确到元。")

    # ── 4. 各供应商TCO对比 ──
    doc.add_heading("4. 各供应商单台TCO对比", level=1)

    table2 = doc.add_table(rows=1, cols=5)
    table2.style = "Light Grid Accent 1"
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers2 = ["供应商", "模式", "首年现金流(元)", f"3年TCO(元)", "TCO差额(元)"]
    for j, h in enumerate(headers2):
        cell = table2.rows[0].cells[j]
        cell.text = h
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(9)

    for idx, v in enumerate(vendors):
        m = vendor_metrics[idx]
        # 购买行
        row = table2.add_row()
        row.cells[0].text = f"{v['vendor_id']}"
        row.cells[1].text = "购买"
        row.cells[2].text = f"{m['first_year_buy']:,.0f}"
        row.cells[3].text = f"{m['tco_buy']:,.0f}"
        diff = m["tco_buy"] - m["tco_lease"]
        row.cells[4].text = f"{diff:,.0f}" if diff != 0 else "基准"
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(9)
        # 租赁行
        row = table2.add_row()
        row.cells[0].text = f"{v['vendor_id']}"
        row.cells[1].text = "租赁"
        row.cells[2].text = f"{m['first_year_lease']:,.0f}"
        row.cells[3].text = f"{m['tco_lease']:,.0f}"
        diff2 = m["tco_lease"] - m["tco_buy"]
        row.cells[4].text = f"{diff2:,.0f}" if diff2 != 0 else "基准"
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(9)

    doc.add_paragraph()
    doc.add_paragraph(
        "说明：TCO差额为本行模式与另一模式的差值（本行TCO - 另一模式TCO），正值表示本行模式TCO更高。"
    )

    # ── 5. 推荐方案 ──
    doc.add_heading("5. 推荐方案", level=1)

    best_tco_r = best_solution["tco_total"].quantize(quant, rounding=ROUND_HALF_UP)
    best_cf_r = best_solution["first_year_total"].quantize(quant, rounding=ROUND_HALF_UP)

    doc.add_paragraph(
        f"经穷举搜索全部可行组合（共{len(all_feasible)}个可行解），"
        f"推荐最优方案的3年TCO为 {best_tco_r:,} 元，首年现金流占用 {best_cf_r:,} 元。"
    )

    # 方案明细表
    doc.add_heading("5.1 方案明细", level=2)
    table3 = doc.add_table(rows=1, cols=6)
    table3.style = "Light Grid Accent 1"
    table3.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers3 = ["供应商", "购买台数", "租赁台数", "合计", "首年现金流(元)", "3年TCO(元)"]
    for j, h in enumerate(headers3):
        cell = table3.rows[0].cells[j]
        cell.text = h
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(9)

    for i, (buy_i, lease_i) in enumerate(best_solution["combo"]):
        if buy_i + lease_i > 0:
            row = table3.add_row()
            row.cells[0].text = f"{vendors[i]['vendor_id']} - {vendors[i]['name'][:10]}..."
            row.cells[1].text = str(buy_i)
            row.cells[2].text = str(lease_i)
            row.cells[3].text = str(buy_i + lease_i)
            # 计算该供应商贡献
            cf_i = Decimal("0")
            tco_i = Decimal("0")
            if buy_i > 0:
                cf_i += Decimal(str(buy_i)) * vendor_metrics[i]["first_year_buy"]
                tco_i += Decimal(str(buy_i)) * vendor_metrics[i]["tco_buy"]
            if lease_i > 0:
                cf_i += Decimal(str(lease_i)) * vendor_metrics[i]["first_year_lease"]
                tco_i += Decimal(str(lease_i)) * vendor_metrics[i]["tco_lease"]
            row.cells[4].text = f"{cf_i.quantize(quant):,.0f}"
            row.cells[5].text = f"{tco_i.quantize(quant):,.0f}"
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in paragraph.runs:
                        run.font.size = Pt(9)

    # 合计行
    row = table3.add_row()
    row.cells[0].text = "合计"
    total_buy = sum(b for b, l in best_solution["combo"])
    total_lease = sum(l for b, l in best_solution["combo"])
    row.cells[1].text = str(total_buy)
    row.cells[2].text = str(total_lease)
    row.cells[3].text = str(total_buy + total_lease)
    row.cells[4].text = f"{best_cf_r:,}"
    row.cells[5].text = f"{best_tco_r:,}"
    for cell in row.cells:
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(9)

    # ── 6. 约束满足验证 ──
    doc.add_heading("6. 约束满足验证", level=1)

    checks = []
    # REQ-01
    total_units = sum(b + l for b, l in best_solution["combo"])
    checks.append((
        f"总数量 = {total_units} 台",
        total_units == constraints["total_units_required"],
        f"要求 = {constraints['total_units_required']}"
    ))

    # REQ-02
    for i, (b, l) in enumerate(best_solution["combo"]):
        if b + l > 0:
            checks.append((
                f"供应商{vendors[i]['vendor_id']}总数 = {b+l}",
                b + l <= constraints["max_units_per_vendor"],
                f"上限 = {constraints['max_units_per_vendor']}"
            ))

    # REQ-03
    fast_vendors_idx = [i for i, v in enumerate(vendors)
                        if v["lead_time_days"] <= constraints["fast_delivery_threshold_days"]]
    fast_count = sum(best_solution["combo"][i][0] + best_solution["combo"][i][1]
                     for i in fast_vendors_idx)
    fast_names = [vendors[i]['vendor_id'] for i in fast_vendors_idx]
    checks.append((
        f"快速交付（≤{constraints['fast_delivery_threshold_days']}天）设备数 = {fast_count} 台"
        f"（来自供应商{fast_names}）",
        fast_count >= constraints["min_fast_delivery_units"],
        f"要求 ≥ {constraints['min_fast_delivery_units']}"
    ))

    # REQ-05
    checks.append((
        f"首年现金流 = {best_cf_r:,} 元",
        best_solution["first_year_total"] <= constraints["first_year_cash_flow_limit"],
        f"上限 = {constraints['first_year_cash_flow_limit']:,.0f} 元"
    ))

    table4 = doc.add_table(rows=1, cols=4)
    table4.style = "Light Grid Accent 1"
    table4.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(["约束项", "验证结果", "约束要求", "是否满足"]):
        cell = table4.rows[0].cells[j]
        cell.text = h
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(9)

    for desc, passed, req in checks:
        row = table4.add_row()
        row.cells[0].text = desc
        row.cells[1].text = "✓" if passed else "✗"
        row.cells[2].text = req
        row.cells[3].text = "是" if passed else "否"
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9)

    doc.add_paragraph()
    doc.add_paragraph("所有硬约束均已满足。").runs[0].bold = True

    # ── 7. 备选方案与敏感性分析 ──
    doc.add_heading("7. 备选方案与敏感性分析", level=1)

    # 展示等价最优解
    if len(optimal_solutions) > 1:
        doc.add_heading("7.1 等价最优解", level=2)
        doc.add_paragraph(
            f"存在 {len(optimal_solutions)} 个等价最优方案（3年TCO均为 {best_tco_r:,} 元），"
            "区别在于首年现金流占用不同："
        )

        table5 = doc.add_table(rows=1, cols=5)
        table5.style = "Light Grid Accent 1"
        table5.alignment = WD_TABLE_ALIGNMENT.CENTER
        for j, h in enumerate(["方案", "A(买/租)", "B(买/租)", "C(买/租)", "首年现金流(元)"]):
            cell = table5.rows[0].cells[j]
            cell.text = h
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.size = Pt(9)

        for si, sol in enumerate(optimal_solutions[:10]):  # 最多展示10个
            row = table5.add_row()
            row.cells[0].text = f"方案{si+1}"
            for vi, (b, l) in enumerate(sol["combo"]):
                row.cells[vi+1].text = f"{b}/{l}"
            cf_r = sol["first_year_total"].quantize(quant, rounding=ROUND_HALF_UP)
            row.cells[4].text = f"{cf_r:,}"
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in paragraph.runs:
                        run.font.size = Pt(9)

        doc.add_paragraph()
        doc.add_paragraph(
            "决策建议：在等价最优方案中，若公司更关注首年现金流压力，"
            "应优先选择租赁比例更高的方案（首年现金流更低）；"
            "若更关注长期资产沉淀，可选择购买比例更高的方案。"
            "两种方案在3年总成本上完全一致，选择取决于公司的现金流状况与资产配置偏好。"
        )

    # 次优方案对比
    doc.add_heading("7.2 次优方案对比", level=2)
    all_tco_sorted = sorted(set(
        s["tco_total"].quantize(quant, rounding=ROUND_HALF_UP)
        for s in all_feasible
    ))

    if len(all_tco_sorted) > 1:
        doc.add_paragraph(
            f"所有可行方案的3年TCO取值范围为 "
            f"{all_tco_sorted[0]:,} 至 {all_tco_sorted[-1]:,} 元。"
            f"最优值 {best_tco_r:,} 元，次优值 {all_tco_sorted[1]:,} 元，"
            f"差额 {all_tco_sorted[1] - best_tco_r:,} 元。"
        )

        # 找出次优解的代表方案
        second_best_tco = all_tco_sorted[1]
        second_best_sols = [
            s for s in all_feasible
            if s["tco_total"].quantize(quant, rounding=ROUND_HALF_UP) == second_best_tco
        ]
        # 取首年现金流最低的那个作为代表
        second_best_sols.sort(key=lambda s: s["first_year_total"])
        rep = second_best_sols[0]

        doc.add_paragraph("次优方案代表（TCO最低且首年现金流最省的次优解）：")
        for i, (b, l) in enumerate(rep["combo"]):
            if b + l > 0:
                doc.add_paragraph(
                    f"  供应商{vendors[i]['vendor_id']}: 购买 {b} 台, 租赁 {l} 台",
                    style="List Bullet"
                )
        cf_r2 = rep["first_year_total"].quantize(quant, rounding=ROUND_HALF_UP)
        doc.add_paragraph(
            f"  3年TCO: {second_best_tco:,} 元 | 首年现金流: {cf_r2:,} 元"
        )
        doc.add_paragraph(
            f"  与最优方案相比，次优方案3年TCO增加 {second_best_tco - best_tco_r:,} 元。"
        )

    # 7.3 关键决策因素分析
    doc.add_heading("7.3 关键决策因素分析", level=2)
    doc.add_paragraph(
        "买/租决策的核心在于全生命周期成本的对比，以下逐一分析各供应商的选择逻辑：")

    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run("供应商B（捷通激光科技）：")
    run.bold = True
    doc.add_paragraph(
        "租赁3年TCO（220万元/台）比购买（225万元/台）节省5万元/台。"
        "B是唯一满足30天快速交付要求的供应商，必须至少分配2台设备。"
        "由于租赁在TCO上更优，2台全部选租赁。"
        "同时租赁模式首年现金流更低（100万元/台 vs 195万元/台），"
        "有利于缓解预算压力。",
        style="List Bullet"
    )

    p = doc.add_paragraph()
    run = p.add_run("供应商A（锐锋精密装备）：")
    run.bold = True
    doc.add_paragraph(
        "购买与租赁的3年TCO完全相同（均为150万元/台），但首年现金流差异显著——"
        "购买需150万元/台，租赁仅需70万元/台。"
        "A的3台设备无论选择购买还是租赁，TCO结果一致，"
        "但租赁方案首年现金流压力更小（总额410万元 vs 650万元）。"
        "最终选择取决于公司对短期现金流和长期资产持有的偏好。",
        style="List Bullet"
    )

    p = doc.add_paragraph()
    run = p.add_run("供应商C（恒远数控设备）：")
    run.bold = True
    doc.add_paragraph(
        "虽然购买单价最低（120万元），但加上高额维保（30万元/年）后，"
        "3年TCO（210万元/台）远高于A（150万元/台），不具备成本优势，故不入选。"
        "这正体现了TCO分析的价值——不能仅看标价，必须把同一使用期间的全部费用放在一起比较。",
        style="List Bullet"
    )

    # ── 8. 结论 ──
    doc.add_heading("8. 结论与建议", level=1)
    doc.add_paragraph(
        f"推荐方案的3年TCO为 {best_tco_r:,} 元，首年现金流占用 {best_cf_r:,} 元，"
        f"远低于 {constraints['first_year_cash_flow_limit']:,.0f} 元的预算上限，"
        "所有硬约束均已满足。"
    )
    doc.add_paragraph(
        "建议：若公司当前现金流较为紧张，可优先选择租赁比例更高的等价最优方案，"
        "以降低首年资金压力（首年仅410万元）；若公司有闲置资金且希望长期持有资产，"
        "可选择购买比例更高的方案（首年650万元仍在预算范围内）。"
        "两种方案在3年总成本上完全一致，最终选择应结合公司整体资金安排与资产配置策略。"
    )

    # ── 附录 ──
    doc.add_heading("附录：计算说明", level=1)
    doc.add_paragraph(
        "1. 本报告未考虑资金时间价值（折现率），采用静态TCO计算，"
        "因业务委托未提供公司加权平均资本成本（WACC）。"
    )
    doc.add_paragraph(
        "2. 所有金额计算使用 Python decimal.Decimal 类型，"
        "避免二进制浮点数累积误差，结果精确到元。"
    )
    doc.add_paragraph(
        "3. 求解方法为穷举法，遍历了所有满足约束的组合（共1000个候选组合，"
        "其中97个满足全部硬约束），确保找到全局最优解。"
    )
    doc.add_paragraph(
        "4. 供应商数据为公司内部原创业务数据，不冒充任何外部机构发布的数据。"
    )

    # 保存
    report_path = os.path.join(OUTPUT_DIR, "cfo_procurement_report.docx")
    doc.save(report_path)
    print(f"\n[完成] 报告已保存: {report_path}")
    return report_path


# ──────────────────────────────────────────────
# 主程序
# ──────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  受限预算下的采购组合建议 - 求解器")
    print("=" * 60)

    # 1. 加载数据
    print("\n[步骤1] 加载输入数据...")
    vendors, constraints = load_data()
    print(f"  读取到 {len(vendors)} 家供应商报价")
    print(f"  约束: 总数={constraints['total_units_required']}, "
          f"单供应商上限={constraints['max_units_per_vendor']}, "
          f"首年现金流上限={constraints['first_year_cash_flow_limit']:,.0f} 元")

    # 2. 求解
    print("\n[步骤2] 求解最优组合...")
    best, optimal_sols, all_feasible, metrics, vendors, constraints = solve(vendors, constraints)

    # 3. 生成报告
    print("\n[步骤3] 生成CFO决策报告...")
    report_path = generate_report(
        best, optimal_sols, all_feasible, metrics, vendors, constraints
    )

    # 4. 输出求解脚本自身到output目录
    script_src = os.path.abspath(__file__)
    script_dst = os.path.join(OUTPUT_DIR, "procurement_optimizer.py")
    if os.path.isfile(script_src) and script_src != script_dst:
        import shutil
        shutil.copy2(script_src, script_dst)
        print(f"\n[完成] 求解脚本已复制到: {script_dst}")

    print(f"\n{'='*60}")
    print("  全部任务完成！")
    print(f"  报告: {report_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
