"""
quest_replay_engine.py - 游戏任务进度回放引擎

核心回放引擎组件，提供事件排序、指纹去重、状态机契约校验功能。
设计为可导入的模块，不包含任何强制退出逻辑。

作者: 后端开发团队
版本: 1.0.0
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# 数据模型
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class QuestEvent:
    """任务事件数据类，承载从 JSONL 解析出的单条事件记录。"""
    event_id: str
    logical_clock: int
    timestamp: float
    quest_id: str
    event_type: str
    payload: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuestEvent":
        """从字典构造 QuestEvent，缺少必要字段时抛出 KeyError/ValueError。"""
        return cls(
            event_id=str(data["event_id"]),
            logical_clock=int(data["logical_clock"]),
            timestamp=float(data["timestamp"]),
            quest_id=str(data["quest_id"]),
            event_type=str(data["event_type"]),
            payload=dict(data.get("payload", {})),
        )


@dataclass
class EventResult:
    """单个事件的处理结果。"""
    event_id: str
    logical_clock: int
    quest_id: str
    event_type: str
    status: str  # "success" | "duplicate" | "violation" | "parse_error"
    detail: str  # 人类可读的处理说明
    state_before: Optional[str] = None
    state_after: Optional[str] = None


@dataclass
class ReplayStatistics:
    """回放统计汇总。"""
    total: int = 0
    success: int = 0
    duplicate: int = 0
    violation: int = 0
    parse_error: int = 0


@dataclass
class ReplayReport:
    """完整的回放报告。"""
    statistics: ReplayStatistics = field(default_factory=ReplayStatistics)
    details: List[EventResult] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 状态机契约
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TransitionRule:
    """单条状态转移规则。"""
    from_state: str
    to_state: str


class QuestContract:
    """
    任务状态机契约，从 JSON 文件动态加载。

    契约结构示例:
    {
        "states": {"INIT": ["ACCEPTED"], ...},
        "transitions": {"ACCEPT": {"from": "INIT", "to": "ACCEPTED"}, ...}
    }
    """

    def __init__(self) -> None:
        self.states: Dict[str, List[str]] = {}
        self.transitions: Dict[str, TransitionRule] = {}

    @classmethod
    def load(cls, contract_path: Path) -> "QuestContract":
        """
        从 JSON 文件加载状态机契约。

        Args:
            contract_path: 契约文件路径。

        Returns:
            初始化完成的 QuestContract 实例。

        Raises:
            FileNotFoundError: 文件不存在。
            json.JSONDecodeError: JSON 格式错误。
            KeyError: 缺少必要字段。
        """
        raw_text: str = contract_path.read_text(encoding="utf-8")
        data: Dict[str, Any] = json.loads(raw_text)

        contract = cls()
        contract.states = {
            str(k): [str(s) for s in v]
            for k, v in data["states"].items()
        }
        contract.transitions = {
            str(event_type): TransitionRule(
                from_state=str(rule["from"]),
                to_state=str(rule["to"]),
            )
            for event_type, rule in data["transitions"].items()
        }
        return contract

    def get_transition(self, event_type: str) -> Optional[TransitionRule]:
        """获取指定事件类型对应的转移规则，未定义则返回 None。"""
        return self.transitions.get(event_type)


# ─────────────────────────────────────────────────────────────────────────────
# 回放引擎核心
# ─────────────────────────────────────────────────────────────────────────────

class ReplayEngine:
    """
    任务进度回放引擎。

    核心职责:
      1. 根据 logical_clock 升序排序事件（相同则按 event_id 保证稳定性）。
      2. 基于 event_type + payload 计算确定性指纹，实现幂等去重。
      3. 严格按照状态机契约校验流转，违规事件标记但不中断流程。

    内存与性能说明:
      - 排序使用 Python 内置 Timsort，时间复杂度 O(N log N)。
      - 指纹集合和状态字典均使用 dict/set，查询/更新 O(1)。
      - 对于超大规模单文件（百万级以上事件），全量加载到内存可能成为瓶颈。
        优化策略:
          a) 外部排序: 将文件按 logical_clock 分桶写入临时文件，再归并。
          b) 流式去重: 若仅需去重不需全局排序，可用布隆过滤器近似判重。
          c) 分片处理: 按 quest_id 分片后各分片独立回放，最后合并报告。
    """

    DEFAULT_STATE: str = "INIT"

    def __init__(self, contract: QuestContract) -> None:
        self._contract: QuestContract = contract
        # quest_id -> 当前状态，使用 dict 保证 O(1) 查询与更新
        self._quest_states: Dict[str, str] = {}
        # 已见指纹集合，O(1) 判重
        self._seen_fingerprints: set[str] = set()

    # ── 公开接口 ──────────────────────────────────────────────────────────

    def process_stream(
        self,
        raw_events: List[Dict[str, Any]],
    ) -> ReplayReport:
        """
        处理原始事件流，返回完整回放报告。

        流程:
          1. 解析 & 容错: 逐条解析 raw_events，解析失败的记录为 parse_error。
          2. 排序: 按 (logical_clock, event_id) 升序。
          3. 去重: 指纹相同的事件仅首次生效。
          4. 契约校验: 按状态机规则校验，违规事件标记为 violation。
          5. 状态推进: 合法事件更新 quest 状态。

        Args:
            raw_events: 原始事件字典列表（尚未排序）。

        Returns:
            包含统计和明细的 ReplayReport。
        """
        report: ReplayReport = ReplayReport()

        # 第 1 步: 解析，容错
        parsed_events: List[QuestEvent] = []
        for raw in raw_events:
            try:
                evt: QuestEvent = QuestEvent.from_dict(raw)
                parsed_events.append(evt)
            except (KeyError, ValueError, TypeError) as exc:
                # 解析失败，记录错误并继续
                err_id: str = str(raw.get("event_id", "UNKNOWN"))
                result: EventResult = EventResult(
                    event_id=err_id,
                    logical_clock=int(raw.get("logical_clock", -1)),
                    quest_id=str(raw.get("quest_id", "UNKNOWN")),
                    event_type=str(raw.get("event_type", "UNKNOWN")),
                    status="parse_error",
                    detail=f"解析异常: {exc}",
                )
                report.details.append(result)
                report.statistics.total += 1
                report.statistics.parse_error += 1

        # 第 2 步: 排序 — 按 logical_clock 升序，相同时按 event_id 保证稳定性
        sorted_events: List[QuestEvent] = sorted(
            parsed_events,
            key=lambda e: (e.logical_clock, e.event_id),
        )

        # 第 3-5 步: 逐条处理 — 去重 → 契约校验 → 状态推进
        for evt in sorted_events:
            result = self._process_single_event(evt)
            report.details.append(result)
            report.statistics.total += 1
            if result.status == "success":
                report.statistics.success += 1
            elif result.status == "duplicate":
                report.statistics.duplicate += 1
            elif result.status == "violation":
                report.statistics.violation += 1
            # parse_error 已在上面统计

        return report

    def load_events_from_jsonl(self, jsonl_path: Path) -> List[Dict[str, Any]]:
        """
        从 JSONL 文件加载原始事件列表。

        逐行解析，跳过空行和格式错误的行，并记录错误信息。
        此方法仅负责读取原始数据，不做排序或校验。

        Args:
            jsonl_path: JSONL 文件路径。

        Returns:
            原始事件字典列表。格式错误行会生成带 _line_error 标记的占位记录。
        """
        raw_events: List[Dict[str, Any]] = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                stripped: str = line.strip()
                if not stripped:
                    continue
                try:
                    obj: Dict[str, Any] = json.loads(stripped)
                    raw_events.append(obj)
                except json.JSONDecodeError as exc:
                    # 格式错误的行 — 构造一个占位记录以便上层统计
                    raw_events.append({
                        "event_id": f"__parse_error_line{line_no}",
                        "logical_clock": -1,
                        "timestamp": 0.0,
                        "quest_id": "__unknown",
                        "event_type": "__unknown",
                        "payload": {},
                        "_line_error": str(exc),
                        "_line_no": line_no,
                    })
        return raw_events

    # ── 内部方法 ──────────────────────────────────────────────────────────

    def _process_single_event(self, evt: QuestEvent) -> EventResult:
        """
        处理单个已解析事件的完整流水线: 去重 → 契约校验 → 状态推进。

        任何异常都会被捕获并转化为 violation/parse_error 结果，绝不中断流程。
        """
        try:
            # 去重检查
            fingerprint: str = self._compute_fingerprint(evt)
            if fingerprint in self._seen_fingerprints:
                return EventResult(
                    event_id=evt.event_id,
                    logical_clock=evt.logical_clock,
                    quest_id=evt.quest_id,
                    event_type=evt.event_type,
                    status="duplicate",
                    detail=f"指纹重复，跳过: {fingerprint[:16]}...",
                    state_before=self._get_state(evt.quest_id),
                    state_after=self._get_state(evt.quest_id),
                )

            # 契约校验
            transition: Optional[TransitionRule] = self._contract.get_transition(evt.event_type)
            current_state: str = self._get_state(evt.quest_id)

            if transition is None:
                # 契约中未定义的事件类型 — 标记为违规，不抛异常
                return EventResult(
                    event_id=evt.event_id,
                    logical_clock=evt.logical_clock,
                    quest_id=evt.quest_id,
                    event_type=evt.event_type,
                    status="violation",
                    detail=f"未定义的事件类型: {evt.event_type}",
                    state_before=current_state,
                    state_after=current_state,
                )

            if current_state != transition.from_state:
                # 当前状态不满足转移前提 — 违规
                return EventResult(
                    event_id=evt.event_id,
                    logical_clock=evt.logical_clock,
                    quest_id=evt.quest_id,
                    event_type=evt.event_type,
                    status="violation",
                    detail=(
                        f"状态不匹配: 当前={current_state}, "
                        f"需要={transition.from_state} (事件 {evt.event_type})"
                    ),
                    state_before=current_state,
                    state_after=current_state,
                )

            # 合法转移 — 记录指纹，推进状态
            self._seen_fingerprints.add(fingerprint)
            new_state: str = transition.to_state
            self._quest_states[evt.quest_id] = new_state

            return EventResult(
                event_id=evt.event_id,
                logical_clock=evt.logical_clock,
                quest_id=evt.quest_id,
                event_type=evt.event_type,
                status="success",
                detail=f"状态转移: {current_state} → {new_state}",
                state_before=current_state,
                state_after=new_state,
            )

        except Exception as exc:
            # 兜底: 任何未预期的异常都不中断流程
            return EventResult(
                event_id=evt.event_id,
                logical_clock=evt.logical_clock,
                quest_id=evt.quest_id,
                event_type=evt.event_type,
                status="violation",
                detail=f"处理异常(兜底): {exc}",
                state_before=self._get_state(evt.quest_id),
                state_after=self._get_state(evt.quest_id),
            )

    def _compute_fingerprint(self, evt: QuestEvent) -> str:
        """
        计算事件指纹，用于幂等去重。

        指纹基于 event_type + payload 的确定性序列化。
        使用 json.dumps(sort_keys=True) 确保字典键无序性不影响结果。
        separators 去除多余空白，保证压缩表示。
        使用 SHA-256 哈希，碰撞概率极低。

        对于 payload 中可能存在的非标准 JSON 类型（如自定义对象），
        使用 default=str 做降级序列化，避免 json.dumps 崩溃。

        Args:
            evt: 待计算指纹的事件。

        Returns:
            十六进制 SHA-256 摘要字符串。
        """
        canonical_payload: str = json.dumps(
            evt.payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,  # 非标准类型降级为字符串，防止序列化崩溃
        )
        raw_fingerprint: str = f"{evt.event_type}|{canonical_payload}"
        return hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()

    def _get_state(self, quest_id: str) -> str:
        """
        获取指定任务的当前状态。

        若任务尚未出现过，返回默认初始状态 INIT。
        使用 dict.get 的默认值参数，O(1) 查询。

        Args:
            quest_id: 任务 ID。

        Returns:
            当前状态字符串。
        """
        return self._quest_states.get(quest_id, self.DEFAULT_STATE)


# ─────────────────────────────────────────────────────────────────────────────
# 报告序列化
# ─────────────────────────────────────────────────────────────────────────────

def report_to_dict(report: ReplayReport) -> Dict[str, Any]:
    """
    将 ReplayReport 转换为可 JSON 序列化的字典。

    Args:
        report: 回放报告对象。

    Returns:
        标准字典结构，可直接 json.dumps。
    """
    return {
        "statistics": {
            "total": report.statistics.total,
            "success": report.statistics.success,
            "duplicate": report.statistics.duplicate,
            "violation": report.statistics.violation,
            "parse_error": report.statistics.parse_error,
        },
        "details": [
            {
                "event_id": d.event_id,
                "logical_clock": d.logical_clock,
                "quest_id": d.quest_id,
                "event_type": d.event_type,
                "status": d.status,
                "detail": d.detail,
                "state_before": d.state_before,
                "state_after": d.state_after,
            }
            for d in report.details
        ],
    }
