#!/usr/bin/env python3
"""
replay_executor.py - 任务进度回放执行器（操作示例脚本）

读取输入文件（事件流 + 状态机契约），实例化回放引擎，执行回放，
并将结构化报告输出到 replay_report.json。

使用方式:
    python replay_executor.py

输入文件（位于同级 input_files 目录或 /work/input_files）:
    - replay_events.jsonl   原始事件流
    - quest_contract.json   状态机契约

输出文件:
    - replay_report.json    结构化回放报告
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

# 将脚本所在目录加入模块搜索路径，确保能导入同目录引擎
_SCRIPT_DIR: Path = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from quest_replay_engine import (
    QuestContract,
    ReplayEngine,
    ReplayReport,
    report_to_dict,
)


def resolve_input_paths() -> tuple[Path, Path]:
    """
    解析输入文件路径，优先查找 /work/input_files，
    其次查找脚本同级 input_files 目录。

    Returns:
        (events_path, contract_path) 元组。

    Raises:
        FileNotFoundError: 任一文件不存在。
    """
    candidates: list[Path] = [
        Path("/work/input_files"),
        Path("/app/input_files"),
        _SCRIPT_DIR / "input_files",
    ]

    input_dir: Path | None = None
    for c in candidates:
        if c.is_dir():
            input_dir = c
            break

    if input_dir is None:
        raise FileNotFoundError("未找到输入文件目录，已搜索: " + str(candidates))

    events_path: Path = input_dir / "replay_events.jsonl"
    contract_path: Path = input_dir / "quest_contract.json"

    if not events_path.exists():
        raise FileNotFoundError(f"事件流文件不存在: {events_path}")
    if not contract_path.exists():
        raise FileNotFoundError(f"契约文件不存在: {contract_path}")

    return events_path, contract_path


def resolve_output_path() -> Path:
    """
    确定输出报告路径，优先使用 /work/output，
    其次使用脚本所在目录。

    Returns:
        输出文件的完整路径。
    """
    output_dir: Path = Path("/work/output")
    if not output_dir.exists():
        output_dir = _SCRIPT_DIR
    return output_dir / "replay_report.json"


def main() -> None:
    """
    执行回放的主入口。

    步骤:
      1. 定位输入文件。
      2. 加载状态机契约。
      3. 读取原始事件流。
      4. 实例化引擎并执行回放。
      5. 序列化报告并写入 JSON 文件。
    """
    # 1. 定位输入
    events_path: Path
    contract_path: Path
    events_path, contract_path = resolve_input_paths()
    print(f"[INFO] 事件流文件: {events_path}")
    print(f"[INFO] 契约文件:   {contract_path}")

    # 2. 加载契约
    contract: QuestContract = QuestContract.load(contract_path)
    print(f"[INFO] 契约加载完成: {len(contract.transitions)} 条转移规则, "
          f"{len(contract.states)} 个状态")

    # 3. 读取事件流
    engine: ReplayEngine = ReplayEngine(contract)
    raw_events: list[Dict[str, Any]] = engine.load_events_from_jsonl(events_path)
    print(f"[INFO] 读取到 {len(raw_events)} 条原始事件")

    # 4. 执行回放
    report: ReplayReport = engine.process_stream(raw_events)
    print(f"[INFO] 回放完成:")
    print(f"       总数={report.statistics.total}, "
          f"成功={report.statistics.success}, "
          f"去重={report.statistics.duplicate}, "
          f"违规={report.statistics.violation}, "
          f"解析错误={report.statistics.parse_error}")

    # 5. 写入报告
    output_path: Path = resolve_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_dict: Dict[str, Any] = report_to_dict(report)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)
    print(f"[INFO] 报告已写入: {output_path}")


if __name__ == "__main__":
    main()
