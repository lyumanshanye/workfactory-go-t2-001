#!/usr/bin/env python3
"""
星汇社区党群服务中心 - 五一期间活动排程约束求解器
================================================

参考 CP-SAT (Constraint Programming - Satisfiability) 建模思路，
基于 Google OR-Tools CP-SAT 的布尔变量、约束传播、分支定界方法论，
在缺少 ortools 运行库的环境下实现等价的约束求解逻辑。

业务背景:
    依据国办发明电〔2024〕12号及2024修订版《全国年节及纪念日放假办法》,
    2025年劳动节法定假日为5月1日和5月2日，5月1日至5日放假调休共5天，
    4月27日（周日）补班。本排程覆盖4月28日（周一）至5月4日（周日）。

日期属性（依据S03/S04）:
    2025-04-28 周一 工作日
    2025-04-29 周二 工作日
    2025-04-30 周三 工作日
    2025-05-01 周四 法定假日
    2025-05-02 周五 法定假日
    2025-05-03 周六 周末休息日
    2025-05-04 周日 周末休息日

求解目标:
    在满足全部硬约束前提下，最小化所有社工有活动的总天数（人性化排班）。

来源声明:
    - 日期属性与法定假日判定: S02_2024修订.docx, S03_2025年度安排.docx, S04_官方日历摘录.json
    - CP-SAT建模范式: primary_schedule.txt (Google OR-Tools 护士排班示例)
    - 社区内部资源数据: community_facilities.json, staff_and_activities.json, holiday_rules.json（原创业务数据）
"""

import json
import csv
import os
import sys
from itertools import product
from copy import deepcopy

# ============================================================
# 0. 路径与数据加载
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 支持多种运行路径
for candidate in [
    os.path.join(SCRIPT_DIR, "..", "input_files"),
    os.path.join(SCRIPT_DIR, "input_files"),
    "/work/input_files",
]:
    if os.path.isdir(candidate):
        INPUT_DIR = os.path.abspath(candidate)
        break
else:
    INPUT_DIR = "/work/input_files"

OUTPUT_DIR = SCRIPT_DIR if os.path.isdir(os.path.join(SCRIPT_DIR, "..", "output")) else "/work/output"
# 最终确保输出目录正确
OUTPUT_DIR = "/work/output"

def load_json(filename):
    """加载JSON数据文件"""
    filepath = os.path.join(INPUT_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

facilities = load_json("community_facilities.json")
staff_data = load_json("staff_and_activities.json")
holiday_rules = load_json("holiday_rules.json")

# ============================================================
# 1. 基础数据定义 - 日期维度
# ============================================================

# REQ-01: 日期属性严格匹配S03/S04
# 来源: S04_官方日历摘录.json - statutory_dates, rest_windows, makeup_workdays
# 来源: S03_2025年度安排.docx - 劳动节5月1日至5日放假调休

DATES = ["2025-04-28", "2025-04-29", "2025-04-30",
         "2025-05-01", "2025-05-02", "2025-05-03", "2025-05-04"]

# 日期属性字典 - 基于S02/S03/S04交叉验证
# S02: 劳动节法定假日为5月1日、5月2日（国务院令第795号）
# S03: 5月1日至5日放假，4月27日补班（国办发明电〔2024〕12号）
# S04: statutory_dates包含5.1和5.2
DATE_ATTR = {}
for d in DATES:
    if d in ["2025-05-01", "2025-05-02"]:
        DATE_ATTR[d] = "statutory_holiday"  # 法定假日 (S02第四条第四项)
    elif d in ["2025-05-03", "2025-05-04"]:
        DATE_ATTR[d] = "weekend_rest"       # 周末休息日
    else:
        DATE_ATTR[d] = "workday"            # 正常工作日 (4.28-4.30)

TIME_SLOTS = facilities["time_slots"]  # ["AM", "PM"]
ROOMS = {r["name"]: r for r in facilities["rooms"]}
STAFF_LIST = staff_data["staff"]
ACTIVITIES = staff_data["activities"]

# 维护计划索引
MAINTENANCE_BLOCKS = set()
for m in facilities["maintenance"]:
    MAINTENANCE_BLOCKS.add((m["date"], m["slot"], m["room"]))

# 假日禁止规则索引
FORBIDDEN_RULES = []
for rule in holiday_rules["rules"]:
    for act_name in rule["forbidden_activities"]:
        for date in rule["dates"]:
            FORBIDDEN_RULES.append((act_name, date))

# 社工休息日索引
STAFF_REST_DAYS = {}
for s in STAFF_LIST:
    STAFF_REST_DAYS[s["name"]] = set(s["rest_days"])

# 社工技能索引
STAFF_SKILLS = {}
for s in STAFF_LIST:
    STAFF_SKILLS[s["name"]] = set(s["skills"])

# ============================================================
# 2. CP-SAT 变量定义
# ============================================================
# 参考 primary_schedule.txt 中的护士排班变量定义模式:
#   shifts[(nurse, day, shift)] = BoolVar
#
# 本问题变量映射 (domain mapping from nurse scheduling):
#   护士排班: (nurse, day, shift) -> BoolVar
#   活动排程: (activity, day, slot) -> 分配(staff, room)
#
# 由于每个活动场地已指定（活动属性固定），变量简化为:
#   x[act_idx] in {(date, slot, staff)}  -- 每个活动的可行分配域

def compute_feasible_assignments():
    """
    为每个活动计算所有满足硬约束的可行分配方案。
    这相当于CP-SAT中的变量域（domain）定义，通过预过滤减少搜索空间。
    
    REQ-03: 场地容量
    REQ-05: 技能匹配与休息日
    REQ-07: 维护避让
    REQ-02: 假日禁止
    REQ-09: 五一游园会日期限制
    """
    feasible = {}
    for act_idx, act in enumerate(ACTIVITIES):
        act_name = act["name"]
        room_name = act["room"]
        room = ROOMS[room_name]
        required_skill = act["required_skill"]
        headcount = act["headcount"]
        allowed_dates = act.get("allowed_dates", DATES)
        
        # REQ-03: 容量检查
        if headcount > room["capacity"]:
            print(f"  [ERROR] 活动'{act_name}'人数{headcount}超过场地'{room_name}'容量{room['capacity']}")
            feasible[act_idx] = []
            continue
        
        assignments = []
        for date in allowed_dates:
            if date not in DATES:
                continue
            
            # REQ-02: 假日禁止规则
            if (act_name, date) in FORBIDDEN_RULES:
                continue
            
            for slot in TIME_SLOTS:
                # REQ-07: 维护避让
                if (date, slot, room_name) in MAINTENANCE_BLOCKS:
                    continue
                
                # REQ-05: 人员技能与休息日
                for staff in STAFF_LIST:
                    staff_name = staff["name"]
                    if required_skill not in STAFF_SKILLS[staff_name]:
                        continue
                    if date in STAFF_REST_DAYS[staff_name]:
                        continue
                    assignments.append((date, slot, staff_name))
        
        feasible[act_idx] = assignments
        print(f"  活动'{act_name}': {len(assignments)}个可行分配")
    
    return feasible

print("=" * 60)
print("阶段1: 变量域计算 - 预过滤硬约束")
print("=" * 60)
feasible_assignments = compute_feasible_assignments()

# 检查是否有活动无可行分配（早期检测不可行性）
for act_idx, assigns in feasible_assignments.items():
    if len(assigns) == 0:
        print(f"\n[FATAL] 活动'{ACTIVITIES[act_idx]['name']}'无任何可行分配！")
        print("请检查约束是否存在矛盾。")
        sys.exit(2)

# ============================================================
# 3. 约束定义 - 全局互斥约束集
# ============================================================
# 预过滤已处理单变量约束，以下为多变量全局约束:
#
# C1 (REQ-03部分): 同一(date,slot)内，同一room最多一个活动
# C2 (REQ-04): 同一(date,slot)内，最多一个活动使用移动音响
# C3 (REQ-06): 同一(date,slot)内，同一staff最多负责一个活动

# 需要移动音响的活动索引
NEEDS_MOBILE_SPEAKER = set()
for act_idx, act in enumerate(ACTIVITIES):
    if "移动音响" in act.get("required_equipment", []):
        NEEDS_MOBILE_SPEAKER.add(act_idx)

# 活动场地映射
ACT_ROOM = {idx: act["room"] for idx, act in enumerate(ACTIVITIES)}

print(f"\n需要移动音响的活动: {[ACTIVITIES[i]['name'] for i in NEEDS_MOBILE_SPEAKER]}")
print(f"同场地活动组:")
room_groups = {}
for idx, act in enumerate(ACTIVITIES):
    room_groups.setdefault(act["room"], []).append(act["name"])
for room, acts in room_groups.items():
    print(f"  {room}: {acts}")

# ============================================================
# 4. 求解器核心 - 分支定界回溯搜索
# ============================================================

class ConstraintSolver:
    """
    约束求解器，参考CP-SAT的分支定界策略。
    
    搜索策略:
    1. 变量选择: MRV(Minimum Remaining Values)启发式 - 最受限优先
    2. 值选择: 按字典序枚举可行分配
    3. 约束传播: 每次赋值后即时检查全局互斥约束
    4. 分支定界: 维护当前最优目标值，剪枝不可能改善的分支
    
    等价于CP-SAT的以下操作:
    - model.NewBoolVar() -> 变量域预计算
    - model.Add() -> check_consistency()
    - model.Minimize() -> 分支定界目标函数
    - solver.Solve() -> solve()递归搜索
    """
    
    def __init__(self, feasible, activities, need_speaker, act_room):
        self.feasible = feasible
        self.activities = activities
        self.need_speaker = need_speaker
        self.act_room = act_room
        self.n_activities = len(activities)
        
        # MRV: 按可行域大小排序（最受限的变量优先赋值）
        # 这大幅减少搜索树的分支因子
        self.var_order = sorted(range(self.n_activities),
                                key=lambda i: len(feasible[i]))
        
        self.best_solution = None
        self.best_objective = float('inf')
        self.solutions_found = 0
        self.nodes_explored = 0
    
    def check_consistency(self, assignment, new_act_idx, new_date, new_slot, new_staff):
        """
        增量一致性检查 - 仅验证新赋值与已有赋值的冲突。
        
        约束:
        C1: 场地-时段互斥 (REQ-03) - 同时段同场地不能有两个活动
        C2: 移动音响-时段互斥 (REQ-04) - 同时段最多一个活动使用移动音响
        C3: 社工-时段互斥 (REQ-06) - 同时段同社工不能负责两个活动
        """
        new_room = self.act_room[new_act_idx]
        new_needs_speaker = (new_act_idx in self.need_speaker)
        
        for prev_idx, (prev_date, prev_slot, prev_staff) in assignment.items():
            # 仅检查同时段的约束
            if prev_date != new_date or prev_slot != new_slot:
                continue
            
            # C1: 场地互斥
            if self.act_room[prev_idx] == new_room:
                return False
            
            # C2: 移动音响互斥
            if new_needs_speaker and (prev_idx in self.need_speaker):
                return False
            
            # C3: 社工互斥
            if prev_staff == new_staff:
                return False
        
        return True
    
    def compute_objective(self, assignment):
        """
        目标函数: 所有社工有活动的总天数。
        
        objective = |{(staff, date) : staff在该date有至少一个活动}|
        
        REQ-08: 最小化此值，实现集中排班、人性化分配。
        """
        staff_day_set = set()
        for act_idx, (date, slot, staff) in assignment.items():
            staff_day_set.add((staff, date))
        return len(staff_day_set)
    
    def solve(self, assignment=None, var_pos=0):
        """
        递归回溯搜索 + 分支定界。
        
        采用深度优先搜索，利用MRV启发式和即时约束检查。
        分支定界：当已赋值部分的目标下界 >= 当前最优时，停止探索。
        """
        if assignment is None:
            assignment = {}
        
        self.nodes_explored += 1
        
        # 基线条件: 所有变量已赋值
        if var_pos >= self.n_activities:
            obj = self.compute_objective(assignment)
            self.solutions_found += 1
            if obj < self.best_objective:
                self.best_objective = obj
                self.best_solution = dict(assignment)
            return
        
        act_idx = self.var_order[var_pos]
        
        # 分支定界剪枝
        # 下界 = 当前已有staff-day数（剩余变量不可能减少）
        if self.best_solution is not None:
            current_obj = self.compute_objective(assignment)
            if current_obj >= self.best_objective:
                return  # 不可能改善，剪枝
        
        # 枚举当前变量的所有可行值
        for (date, slot, staff) in self.feasible[act_idx]:
            if self.check_consistency(assignment, act_idx, date, slot, staff):
                assignment[act_idx] = (date, slot, staff)
                self.solve(assignment, var_pos + 1)
                del assignment[act_idx]


# ============================================================
# 5. 执行求解
# ============================================================

print("\n" + "=" * 60)
print("阶段2: 约束求解 - 分支定界搜索")
print("=" * 60)

solver = ConstraintSolver(
    feasible=feasible_assignments,
    activities=ACTIVITIES,
    need_speaker=NEEDS_MOBILE_SPEAKER,
    act_room=ACT_ROOM
)

print(f"\n变量排序(MRV): {[ACTIVITIES[i]['name'] for i in solver.var_order]}")
print(f"各活动可行域大小: {[len(feasible_assignments[i]) for i in solver.var_order]}")

print("\n开始搜索...")
solver.solve()

# ============================================================
# 6. 求解结果验证与输出
# ============================================================

print("\n" + "=" * 60)
print("阶段3: 结果验证")
print("=" * 60)

if solver.best_solution is None:
    print("\n[求解状态] INFEASIBLE - 无可行解")
    print("需要启动冲突处置预案，详见conflict_resolution.md")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "solver_status.txt"), 'w', encoding='utf-8') as f:
        f.write("INFEASIBLE\n")
    sys.exit(1)

print(f"\n[求解状态] OPTIMAL")
print(f"  CpSolverStatus等价状态: OPTIMAL (找到全局最优解)")
print(f"  目标函数值(社工活动总天数): {solver.best_objective}")
print(f"  搜索节点数: {solver.nodes_explored}")
print(f"  找到可行解总数: {solver.solutions_found}")

# 构建输出数据
solution = solver.best_solution
csv_rows = []
print(f"\n最优排程方案:")
print("-" * 90)
header = f"{'活动名称':<12} {'日期':<12} {'时段':<5} {'场地':<10} {'社工':<6} {'人数':<5} {'设备':<12} {'日期属性'}"
print(header)
print("-" * 90)

for act_idx in sorted(solution.keys()):
    date, slot, staff = solution[act_idx]
    act = ACTIVITIES[act_idx]
    room = act["room"]
    equip_str = ",".join(act.get("required_equipment", [])) if act.get("required_equipment") else "-"
    date_type = DATE_ATTR[date]
    print(f"{act['name']:<12} {date:<12} {slot:<5} {room:<10} {staff:<6} {act['headcount']:<5} {equip_str:<12} {date_type}")
    csv_rows.append({
        "activity_name": act["name"],
        "date": date,
        "time_slot": slot,
        "room": room,
        "staff": staff,
        "headcount": act["headcount"],
        "equipment": equip_str,
        "date_type": date_type
    })

# 逐条验证全部硬约束
print("\n" + "-" * 60)
print("硬约束逐条验证:")

errors = []

# R01: 日期属性
print("\n[R01] 日期属性验证:")
for d in DATES:
    print(f"  {d}: {DATE_ATTR[d]}")

# R02: 党建讲座不在5.1/5.2
print("\n[R02] 法定假日禁止规则:")
for row in csv_rows:
    if row["activity_name"] == "党建讲座":
        if row["date"] in ["2025-05-01", "2025-05-02"]:
            errors.append("R02: 党建讲座在法定假日!")
        else:
            print(f"  党建讲座={row['date']} (非5.1/5.2) ✓")

# R03/R18: 场地容量与时段互斥
print("\n[R03/R18] 场地容量+互斥:")
room_slot_check = {}
for row in csv_rows:
    key = (row["room"], row["date"], row["time_slot"])
    if key in room_slot_check:
        errors.append(f"R03/R18: 场地冲突 {key}: {room_slot_check[key]} vs {row['activity_name']}")
    room_slot_check[key] = row["activity_name"]
    cap = ROOMS[row["room"]]["capacity"]
    if row["headcount"] > cap:
        errors.append(f"R03: 容量超限 {row['activity_name']} {row['headcount']}>{cap}")
    else:
        print(f"  {key}: {row['activity_name']} ({row['headcount']}/{cap}) ✓")

# R04: 移动音响互斥
print("\n[R04] 移动音响互斥:")
speaker_slots = {}
for row in csv_rows:
    if "移动音响" in row["equipment"]:
        key = (row["date"], row["time_slot"])
        if key in speaker_slots:
            errors.append(f"R04: 移动音响冲突 {key}")
        speaker_slots[key] = row["activity_name"]
        print(f"  {key}: {row['activity_name']} ✓")
print(f"  同时段最大使用数 <= 1 ✓")

# R05: 技能与休息日
print("\n[R05] 人员资质+休息日:")
for row in csv_rows:
    act_def = next(a for a in ACTIVITIES if a["name"] == row["activity_name"])
    if act_def["required_skill"] not in STAFF_SKILLS[row["staff"]]:
        errors.append(f"R05: 技能不匹配 {row['staff']}/{row['activity_name']}")
    if row["date"] in STAFF_REST_DAYS[row["staff"]]:
        errors.append(f"R05: 休息日冲突 {row['staff']}/{row['date']}")
    print(f"  {row['staff']}→{row['activity_name']}: 技能={act_def['required_skill']} ✓ 非休息日 ✓")

# R06: 社工时段互斥
print("\n[R06] 社工时段互斥:")
staff_slot_check = {}
for row in csv_rows:
    key = (row["staff"], row["date"], row["time_slot"])
    if key in staff_slot_check:
        errors.append(f"R06: 社工冲突 {key}")
    staff_slot_check[key] = row["activity_name"]
print(f"  所有(社工,日期,时段)组合唯一 ✓")

# R07: 5.3 PM无舞蹈室
print("\n[R07] 场地维护避让:")
violated = False
for key in room_slot_check:
    if key == ("舞蹈室", "2025-05-03", "PM"):
        errors.append("R07: 5.3 PM舞蹈室有活动!")
        violated = True
if not violated:
    print(f"  5月3日下午舞蹈室无活动 ✓")

# R09: 五一游园会在5.1或5.2
print("\n[R09] 游园会日期:")
for row in csv_rows:
    if row["activity_name"] == "五一游园会":
        if row["date"] in ["2025-05-01", "2025-05-02"]:
            print(f"  游园会={row['date']} ✓")
        else:
            errors.append(f"R09: 游园会日期错误 {row['date']}")

# R19: 活动覆盖
print(f"\n[R19] 活动覆盖度:")
act_names = set(row["activity_name"] for row in csv_rows)
if len(act_names) != 5:
    errors.append(f"R19: 活动数不为5: {len(act_names)}")
else:
    print(f"  全部5个活动已排程 ✓")

# 软约束分析
print("\n" + "-" * 60)
print("软约束(人性化排班)分析:")
staff_days = {}
for row in csv_rows:
    key = row["staff"]
    if key not in staff_days:
        staff_days[key] = set()
    staff_days[key].add(row["date"])

for staff_name, days in sorted(staff_days.items()):
    print(f"  {staff_name}: 活动天数={len(days)}, 日期={sorted(days)}")
print(f"  总目标函数值: {solver.best_objective}")

if errors:
    print(f"\n!!! 发现 {len(errors)} 个约束违反:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(3)
else:
    print(f"\n✓ 全部硬约束验证通过!")

# ============================================================
# 7. 输出CSV排程表
# ============================================================

print("\n" + "=" * 60)
print("阶段4: 输出文件")
print("=" * 60)

os.makedirs(OUTPUT_DIR, exist_ok=True)

csv_path = os.path.join(OUTPUT_DIR, "weekly_schedule.csv")
csv_headers = ["activity_name", "date", "time_slot", "room", "staff", 
               "headcount", "equipment", "date_type"]

with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=csv_headers)
    writer.writeheader()
    sorted_rows = sorted(csv_rows, key=lambda r: (r["date"], r["time_slot"]))
    writer.writerows(sorted_rows)

print(f"  排程表已写入: {csv_path}")

# 写入求解状态
status_path = os.path.join(OUTPUT_DIR, "solver_status.txt")
with open(status_path, 'w', encoding='utf-8') as f:
    f.write("OPTIMAL\n")
    f.write(f"objective_value={solver.best_objective}\n")
    f.write(f"solutions_found={solver.solutions_found}\n")
    f.write(f"nodes_explored={solver.nodes_explored}\n")

print(f"  求解状态已写入: {status_path}")

print("\n" + "=" * 60)
print("求解完成 - 所有约束验证通过")
print("=" * 60)
