# Input Harbour 输入修复交接

基准为原创2025-06-16 R2；不是后来外包建议或6月10日R1。目标Godot4.4.1，无外部素材、插件或网络请求。

玩法从`_input`移到`_unhandled_input`，先让GUI消费事件；不通过禁用全部输入制造假修复。World为PAUSABLE，主UI路由为ALWAYS；菜单用真实SceneTree.paused。Esc在前置输入仅处理非echo的pressed并消费；其余玩法仍留后置阶段。菜单背景STOP并消费鼠标，按钮上装饰IGNORE；UI根不吞世界点击。恢复时释放GUI焦点，不重建/重置玩法节点，设置保留。

真实回放：`godot --headless --path fixed_game --script res://input_probe.gd`。两窗口640×480/960×640各15项；JSON记录实际shots、steps、ticks、value、text、menu状态。tick绝对值受机器影响，只比较暂停区间前后不变。主场景可直接在编辑器F6或命令行运行交互，不是仅打印测试结果。

官方依据见S01的Godot4.4输入、暂停、Control文档，核心取舍由S02原创R2定义。源码/事件回放结果是本地候选；未验物理鼠标/键盘、OS事件、移动/手柄、多DPI、导出、平台发布或外部QA签字，production_release=false。不把模拟事件通过说成所有设备通过。

文档归属：Juan Linietsky, Ariel Manzur and the Godot Engine community。许可说明：https://docs.godotengine.org/en/4.4/about/faq.html 。手册为CC BY 3.0；此处为注明来源的作者归纳，并非官方中文译文或官方背书；类API内容不声称有不同于原项目的统一再许可。原创工程/业务规则与上述文档区分。
