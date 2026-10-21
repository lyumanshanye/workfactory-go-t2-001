# 任务系统数据包交接文档

> **版本**: 任务系统重构 v1.0  
> **日期**: 2026-11-15  
> **适用引擎**: Godot 4.4  
> **交付物**: `quest_content.json`, `quest_preview.html`

---

## 一、数据映射逻辑说明

### 1.1 字段映射总表

本任务包将策划表 `quest_design_table.json` 的扁平结构映射为引擎协议 `team_json_schema.json` 定义的严格结构。映射规则如下：

| 策划表字段（源） | 引擎Schema字段（目标） | 说明 |
|---|---|---|
| `id` | `quest_id` | 任务唯一标识，直接拷贝 |
| `name` | `display_name` | 任务显示名称，直接拷贝 |
| `prerequisites` | `dependencies` | 前置任务ID数组，直接拷贝 |
| `conditions.min_level` | `unlock_conditions.level` | 最低等级要求 |
| `conditions.has_item` | `unlock_conditions.required_items` | 需持有物品ID数组 |
| `rewards.exp` | `rewards.experience` | 经验值奖励 |
| `rewards.gold` | `rewards.currency` | 金币奖励 |
| `rewards.items` | `rewards.loot` | 掉落物品数组 |
| `rewards.items[].count` | `rewards.loot[].quantity` | 物品数量（见脏数据处理） |

### 1.2 可选字段处理策略

- **`unlock_conditions`**：仅当策划表中存在 `conditions` 字段时才生成该对象。若策划未填写（如 Q005 商队护送），输出中完全省略 `unlock_conditions` 键，不生成 `null` 或空对象。
- **Schema 严格约束**：引擎Schema在所有对象层级均设置了 `additionalProperties: false`，因此输出中不得残留任何原始字段名（如 `id`、`name`、`min_level` 等）。

### 1.3 脏数据修正

策划表中存在以下脏数据，已在转换时修正：

| 任务 | 原始字段 | 原始值 | 修正值 | 说明 |
|---|---|---|---|---|
| Q003 | `rewards.items[1].count`（古地图） | `0` | `1` | 数量不可为0，Schema 约束 `minimum: 1` |
| Q004 | `rewards.items[1].count`（附魔戒指） | `-2` | `1` | 负数为无效数据，修正为最小合法值 `1` |
| Q005 | `rewards.items[1].count`（金币道具） | `0` | `1` | 同上 |

> **注意**：修正策略统一为"不足1则置为1"。如策划有特殊情况（如纯标记物品），需另行约定协议。

---

## 二、Godot 4.4 存档系统对接

### 2.1 持久化组（Persist Group）

任务进度相关节点必须加入 **`"Persist"`** 组，以便存档系统通过 `get_tree().get_nodes_in_group("Persist")` 统一收集需要持久化的对象。

**操作步骤：**

```gdscript
# 在任务管理器节点的 _ready() 中
func _ready():
    add_to_group("Persist")
```

也可以在编辑器Inspector面板的 "Node" → "Groups" 中手动添加。

### 2.2 `save()` 方法实现

每个加入 `"Persist"` 组的节点必须实现 `save()` 方法，返回一个字典（Dictionary）。存档系统会遍历组内所有节点，逐一调用 `save()` 获取数据，然后通过 `JSON.stringify()` 序列化为字符串存入文件。

**任务进度节点的 `save()` 示例：**

```gdscript
func save():
    var save_dict = {
        "filename": get_scene_file_path(),
        "parent": get_parent().get_path(),
        "pos_x": position.x,    # Vector2 不支持 JSON，需拆解
        "pos_y": position.y,
        "completed_quests": completed_quests,   # Array[String]
        "active_quest_id": active_quest_id,     # String
        "quest_progress": quest_progress,       # Dictionary
        "rewards_claimed": rewards_claimed       # Array[String]
    }
    return save_dict
```

### 2.3 JSON 序列化限制（重要）

Godot 的 `JSON` 类仅支持基本数据类型（String、int、float、bool、Array、Dictionary）。以下类型 **无法直接序列化**：

- **`Vector2`** — 必须拆解为 `pos_x` / `pos_y` 两个浮点数
- **`Vector3`** — 必须拆解为三个分量
- **`Color`** — 需转换为 `r, g, b, a` 浮点数或十六进制字符串
- **`Rect2`、`Quaternion`** — 同理需拆解

**对任务系统的影响：**

- 若任务涉及空间位置（如世界地图上的任务标记点），保存时不能直接存 `Vector2`，必须拆解为 `x`/`y` 两个数值字段。加载时再重新组合为 `Vector2(node_data["pos_x"], node_data["pos_y"])`。
- 任务进度字典 `quest_progress` 中若含非基本类型值，需提前转换。

### 2.4 存档文件读写

存档使用 `FileAccess` 类操作文件：

```gdscript
# 保存
var save_file = FileAccess.open("user://savegame.save", FileAccess.WRITE)
var save_nodes = get_tree().get_nodes_in_group("Persist")
for node in save_nodes:
    if node.scene_file_path.is_empty():
        continue
    if !node.has_method("save"):
        continue
    var node_data = node.call("save")
    var json_string = JSON.stringify(node_data)
    save_file.store_line(json_string)

# 加载
var save_file = FileAccess.open("user://savegame.save", FileAccess.READ)
while save_file.get_position() < save_file.get_length():
    var json_string = save_file.get_line()
    var json = JSON.new()
    var parse_result = json.parse(json_string)  // 对应 JSON 类的 parse 方法（JSON.parse）
    if parse_result == OK:
        var node_data = json.data
        # ... 实例化节点并恢复数据
```

---

## 三、UI 输入传播对接

### 3.1 问题描述

当玩家打开任务日志/任务面板时，如果UI没有正确拦截输入事件，鼠标点击可能会穿透UI触发游戏内的移动、攻击等动作。这是一个常见的交互Bug。

### 3.2 输入传播机制

Godot 4.4 中，输入事件的传播顺序为：

1. **`_input()`** — 最先接收，在GUI处理之前
2. **GUI 控件处理** — 由 `mouse_filter` 属性决定
3. **`_unhandled_input()`** — 仅接收未被GUI消费的事件

**关键原则：游戏逻辑输入（如移动、攻击）应当写在 `_unhandled_input()` 而非 `_input()` 中。** 这样当UI控件消费了事件后，游戏动作就不会被触发。

### 3.3 `mouse_filter` 配置

任务UI面板中的各个控件需要正确设置 `mouse_filter` 属性：

- **按钮、文本输入等交互控件**：保持默认的 `MOUSE_FILTER_STOP`，确保能接收并消费鼠标事件。
- **装饰性图标、背景面板**：若不需要接收鼠标事件，设为 `MOUSE_FILTER_IGNORE`，让事件穿透到下层有意义的控件。
- **任务面板根容器（Panel/Control）**：应设为 `MOUSE_FILTER_STOP`，以拦截所有点击，防止事件继续传播到游戏世界。

### 3.4 `accept_event` 的使用

在任务UI节点的脚本中，如果通过 `_gui_input()` 或信号回调处理了某个输入事件，应当调用 `accept_event()` 阻止该事件继续传播到 `_unhandled_input()`：

```gdscript
# 任务日志面板
func _gui_input(event):
    if event is InputEventMouseButton and event.pressed:
        # 处理任务面板内的点击逻辑
        handle_panel_click(event)
        accept_event()  # 阻止事件传播到游戏逻辑
```

> **总结**：任务UI面板打开时，应确保根Control的 `mouse_filter` 为 `STOP`，面板内的交互处理调用 `accept_event()`，游戏逻辑使用 `_unhandled_input()`。这三者配合可完全避免UI遮挡时的动作误触。

---

## 四、暂停机制对接

### 4.1 `SceneTree.paused` 与 `process_mode`

当游戏暂停（如打开暂停菜单、剧情对话）时，`SceneTree.paused` 被设为 `true`，此时物理模拟停止，各节点的处理行为由 `process_mode` 属性控制：

| process_mode 值 | 暂停时行为 |
|---|---|
| `PROCESS_MODE_INHERIT`（默认） | 跟随祖先节点的状态，祖先暂停则自身也暂停 |
| `PROCESS_MODE_PAUSABLE` | 随暂停停止处理（_process、_physics_process 不执行） |
| `PROCESS_MODE_ALWAYS` | **即使游戏暂停也继续处理** |

### 4.2 任务UI面板的配置

任务日志、任务弹窗等UI面板在游戏暂停时仍需要响应玩家操作（如关闭面板、查看任务详情）。因此，**任务UI面板节点（或其根节点）的 `process_mode` 必须设为 `PROCESS_MODE_ALWAYS`**。

```gdscript
# 任务UI面板节点
func _ready():
    process_mode = Node.PROCESS_MODE_ALWAYS
```

如果不设置此项，当游戏暂停时（例如玩家在任务面板打开时按了暂停键），UI面板将无法接收输入、无法播放动画、甚至可能停止渲染更新。

### 4.3 注意事项

- 信号（signal）在暂停时仍然可以触发，不受 `process_mode` 影响。
- 不要试图通过"禁用所有节点"来模拟暂停效果——这会破坏节点树结构和信号连接。正确的做法是使用 `SceneTree.paused` 配合 `process_mode`。
- 任务系统的核心逻辑节点（如任务管理器 `QuestManager`）若需要在暂停时继续检测任务完成条件，也应设为 `PROCESS_MODE_ALWAYS`。但若只需要在玩家活动时检测，保持 `PROCESS_MODE_PAUSABLE` 或 `INHERIT` 即可。

---

## 五、校验清单

在合入主干前，请确认以下事项：

- [ ] `quest_content.json` 通过 `team_json_schema.json` 的完整JSON Schema校验
- [ ] 所有任务数量（6个）与策划表一致，无遗漏
- [ ] 所有 `loot[].quantity` 值 ≥ 1
- [ ] 输出中无残留的策划表原始字段名
- [ ] 任务管理器节点已加入 `"Persist"` 组并实现 `save()` 方法
- [ ] 存档数据中无 Vector2/Color 等不可序列化类型
- [ ] 任务UI面板的 `mouse_filter` 和 `accept_event` 已正确配置
- [ ] 任务UI面板的 `process_mode` 已设为 `PROCESS_MODE_ALWAYS`
- [ ] 游戏逻辑输入使用 `_unhandled_input()` 而非 `_input()`

---

*本文档基于 Godot 4.4 官方文档（存档系统教程、输入事件教程、暂停游戏教程、Control 类参考）及团队内部Schema规范编写。如有API变更，请以引擎实际版本为准。*
