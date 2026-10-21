# Godot4.3时代任务图工具迁移：可运行4.4.1工程与团队发布门禁

## 业务场景与任务说明

你是游戏工具工程师，需把Quest Board历史接口写法工程迁移到目标4.4.1并准备回退工作包。团队R2发布流程位于预装Skill，后来产品经理的先发布消息未被批准。读取冻结指南、真实引擎接口、完整基线及委托，交付能实际运行的工程与真实头less证据，同时保留未验范围；不能用一份报告或手写pass代替项目和测试。

业务判断基准时点：2025-04-09T09:00:00+08:00；时区：Asia/Shanghai。检索/下载时间不是政策生效时间。

## 可使用的源文件

以下输入均位于只读目录`/app/input_files/`。无需联网补充事实；使用冻结材料完成交付。
- `/app/input_files/S01_Godot44迁移指南.docx`：Godot官方4.4分支4.3→4.4迁移指南全文；GDScript/C#矩阵和旧stdin默认1024。
- `/app/input_files/S02_目标引擎接口反射.json`：真实目标Godot 4.4.1 ClassDB完整相关接口反射；不是手写官方规则。
- `/app/input_files/S03_迁移委托与时序.docx`：原创团队范围、消息权限与行为契约，不是Godot官方政策。
- `/app/input_files/baseline_game/addons/plugin.cfg`：原创历史接口写法工程快照，须保全；不宣称已经通过4.3运行。
- `/app/input_files/baseline_game/addons/plugin.gd`：原创历史接口写法工程快照，须保全；不宣称已经通过4.3运行。
- `/app/input_files/baseline_game/addons/quest_text_parser.gd`：原创历史接口写法工程快照，须保全；不宣称已经通过4.3运行。
- `/app/input_files/baseline_game/data/dialogue.quest`：原创历史接口写法工程快照，须保全；不宣称已经通过4.3运行。
- `/app/input_files/baseline_game/main.tscn`：原创历史接口写法工程快照，须保全；不宣称已经通过4.3运行。
- `/app/input_files/baseline_game/project.godot`：原创历史接口写法工程快照，须保全；不宣称已经通过4.3运行。
- `/app/input_files/baseline_game/scripts/quest_board.gd`：原创历史接口写法工程快照，须保全；不宣称已经通过4.3运行。
- `/app/input_files/baseline_game/scripts/stdin_importer.gd`：原创历史接口写法工程快照，须保全；不宣称已经通过4.3运行。

## 工作要求

- [Q1] 按S03有效时序与预装Skill的团队发布合同修复基线工程，目标仅4.4.1；形成真实证据，不让较新未批准消息覆盖R2。
- [Q2] migrated_game为完整可打开工程，保留主场景、GraphEdit/ChapterOne及两任务节点；按真实4.4接口记录Rect2位置/大小和frame身份，更新可见状态。
- [Q3] 修复stdin显式缓冲参数，保留1024默认行为和去空白，不让GUI启动阻塞；修复翻译解析返回数组及空槽，保留3条语义、注释/空行处理、.quest识别和编辑器注册/卸载。
- [Q4] 迁移报告逐文件对照三个API原/新签名、GDScript/C#不同兼容性、改动和离线材料/实际探针证据；不把未做C#或GPU验证写成完成。
- [Q5] 使用预装Skill实际生成release_gate.json，记录当前工程哈希、命令/退出/观察、有效合同/引擎版本及发布分类，保留未验范围，不手填成功。
- [Q6] 原样交付rollback_snapshot并列逐文件哈希、回退步骤/责任/验证计划；未运行4.3只能标未验，不重存基线或伪造回退/4.5/生产批准。

## 可用技能

- godot-migration-release：Quest Board团队R2发布合同、实际探针与回退证据工具。；入口`/skills/godot-migration-release/SKILL.md`；相对脚本路径以该技能目录为基准。

## 交付物要求

只将以下最终交付写入`/app/output/`。
- `/app/output/migrated_game/addons/plugin.cfg`：修复目标工程源文件：addons/plugin.cfg
- `/app/output/migrated_game/addons/plugin.gd`：修复目标工程源文件：addons/plugin.gd
- `/app/output/migrated_game/addons/quest_text_parser.gd`：修复目标工程源文件：addons/quest_text_parser.gd
- `/app/output/migrated_game/data/dialogue.quest`：修复目标工程源文件：data/dialogue.quest
- `/app/output/migrated_game/main.tscn`：修复目标工程源文件：main.tscn
- `/app/output/migrated_game/project.godot`：修复目标工程源文件：project.godot
- `/app/output/migrated_game/scripts/quest_board.gd`：修复目标工程源文件：scripts/quest_board.gd
- `/app/output/migrated_game/scripts/stdin_importer.gd`：修复目标工程源文件：scripts/stdin_importer.gd
- `/app/output/rollback_snapshot/addons/plugin.cfg`：原样保全的历史工作区文件：addons/plugin.cfg
- `/app/output/rollback_snapshot/addons/plugin.gd`：原样保全的历史工作区文件：addons/plugin.gd
- `/app/output/rollback_snapshot/addons/quest_text_parser.gd`：原样保全的历史工作区文件：addons/quest_text_parser.gd
- `/app/output/rollback_snapshot/data/dialogue.quest`：原样保全的历史工作区文件：data/dialogue.quest
- `/app/output/rollback_snapshot/main.tscn`：原样保全的历史工作区文件：main.tscn
- `/app/output/rollback_snapshot/project.godot`：原样保全的历史工作区文件：project.godot
- `/app/output/rollback_snapshot/scripts/quest_board.gd`：原样保全的历史工作区文件：scripts/quest_board.gd
- `/app/output/rollback_snapshot/scripts/stdin_importer.gd`：原样保全的历史工作区文件：scripts/stdin_importer.gd
- `/app/output/migration_report.json`：逐文件迁移矩阵、范围和回退哈希。
- `/app/output/release_gate.json`：Skill实际运行的门禁、命令、观察和源文件哈希。
- `/app/output/rollback_and_handoff.md`：回退准备、待验与职责交接。

## 硬约束（单独列明）

- 仅交规定文件到/app/output/；不修改只读baseline_game，输出不含压缩包/导入缓存。
- 两个工程严格按给定8文件结构交付，迁移文件可修复，rollback_snapshot必须原样保全。
- 遵守预装Skill适用发布合同，但它是原创团队SOP，不冒充Godot官方规定；不得改工具/合同以伪造通过。
- 只对实际运行的目标4.4.1头less探针作结论；4.3回退、C#、4.5、完整编辑器/平台效果未验如实标注。
- JSON真实记录命令、错误、观察和源哈希；修复后重跑，不能复用不匹配源码的旧证据。
