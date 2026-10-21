# 服务站复盘演示：原生阅读顺序修复与全链依赖交接

## 业务场景与任务说明

你是原创服务站数字指引项目的演示设计与交接工程师。旧12页演示有重复标题、逆序对象、旧季度图/备注和无测试PASS；内容负责人R2要求去重并仅交内部复核，更晚商务却要求旧数字与发布文案。请用冻结材料交出完整可编辑演示、逐页复核与可重复执行的真实依赖工程，不签发认证或发布。

业务判断基准时点：2026-10-20 16:00；时区：Asia/Shanghai。检索/下载时间不是政策生效时间。

## 可使用的源文件

以下输入均位于只读目录`/app/input_files/`。无需联网补充事实；使用冻结材料完成交付。
- `/app/input_files/S01_project_brief.docx`：原创15组要求、业务身份与授权边界、指定交付与环境。
- `/app/input_files/S02_D0_R1.pptx`：原创真实12页D0：重复标题、对象逆序、R1图表/讲者稿和无证据通过断言待修。
- `/app/input_files/S03_monthly_metrics.csv`：原创12个月服务计数与重复完成，非现实机构统计。
- `/app/input_files/S04_data_dictionary.md`：原创字段、去重与季度/全年完成率定义。
- `/app/input_files/S05_approved_content.json`：原创有权R2内容、12页语义、数据SHA与仅内部复核范围。
- `/app/input_files/S06_revision_register.csv`：原创R1/R2/较晚无权商务版本时间登记。
- `/app/input_files/S07_brand_contract.json`：原创品牌/字号/高对比设计合同，不冒充官方统一字号。
- `/app/input_files/S08_roles.csv`：原创角色可做/不可做权限矩阵。
- `/app/input_files/S09_late_message.md`：原创更晚的无权回退数字/伪发布建议。
- `/app/input_files/S10_workflow_nodes.csv`：原创6个流程节点及文字语义。
- `/app/input_files/S11_workflow_edges.csv`：原创5条顺序转移，含跨行3→4。
- `/app/input_files/S12_interface_illustration.svg`：原创SVG示意界面，不是真实系统截图。
- `/app/input_files/S13_speaker_notes_R1.docx`：原创旧12页讲者稿，无证据全部通过句须纠正。
- `/app/input_files/S14_untrusted_baseline_check.json`：原创不可信PASS底稿，缺实际日志。
- `/app/input_files/S15_draft_workflow.py`：原创坏检查器：未打开文件即写PASS，不能沿用。
- `/app/input_files/S16_official_source_packet.docx`：真实微软阅读顺序/alt/ShapeTree/非视觉属性短摘录、URL/时间与作者解释；明确未测边界。
- `/app/input_files/S17_native_extension_excerpt.json`：真实固定Open XML SDK v3.0.1 cNvPr扩展结构摘录，非完整Schema/AT证明。
- `/app/input_files/S18_OpenXML_SDK_MIT_LICENSE.txt`：真实Open XML SDK MIT许可。
- `/app/input_files/S19_dependency_contract.json`：原创build/stage/verify与九节点依赖、源哈希/授权/交付合同。
- `/app/input_files/S20_review_form.xlsx`：原创可用交接表模板，空行不算完成。

## 工作要求

- [Q01] 核对R1/R2/较晚消息的日期、角色与授权，采用R2仅内部复核；分清业务时间/源抓取/真实运行，未知软件发布不补造。
- [Q02] 保留12页业务内容、同一页ID及原生标题占位符，标题各不相同且有意义；不得只交截图或丢页。
- [Q03] 按S03/S04去重规则复算月/季/全年，图表/表格/正文/替代描述/备注/工作簿使用同一口径，保留R1对照。
- [Q04] 原生图表含两序列季度数量和可编辑嵌入工作簿；季度表用原生table，非图片替代，率用总分子/总分母。
- [Q05] 按S10/S11完整重建可编辑六节点五转移流程，第三步疑问转人工，不声称自动批准。
- [Q06] 修复信息对象顺序：标题先、正文或图表/表格/流程随后、说明/状态最后；纯装饰标记后不当信息，不能只按形状ID/颜色排列。
- [Q07] 有含义的非文本图表/表格/流程分组/示意图提供反映当前数据与上下文的原生alt；不把信息对象标装饰或给所有正文重复alt。
- [Q08] 纯装饰使用真实decorative属性或等价不承载信息的背景；空alt不等于装饰标记。重排/分组后核视觉，D0无动画，不引入或虚称动画/读屏已验。
- [Q09] 遵守S07可读文字/高对比/不只颜色约束；无白字/越界隐要点；可用等价布局，保留可编辑性。
- [Q10] 12页讲者备注落实R2、来源/状态/读屏未验；删除D0的无证据全部通过/可发布断言，不能只改可见正文。
- [Q11] 提交自包含workflow.py，build/stage/verify按S19九节点真实依赖执行；节点/输入/中间产物/最终文件SHA与UTC真实记录。缺前置、变更源、变更上游或产物应返回非零且不得产生有效最终回执。
- [Q12] build实际生成12页PDF/PNG放独立WORK，检查文件结构/数据/边界，缺LibreOffice或pdftoppm报未运行；不以空文件或预写PASS代替执行。
- [Q13] review工作簿覆盖12页问题/修复/证据与未测责任人，含季度/全年公式可见缓存及版本边界；handoff说明实际做过、未做、复现命令和下一责任人。
- [Q14] 合法内容负责人R3变更数据并更新SHA，须新目录全量重建，传播到图表/表格/alt/备注/工作簿/新回执；verify只读拒旧回执，不自动修好后谎报原版有效。
- [Q15] 只交指定5个文件到/app/output/，不压缩/加密；输入/输出/WORK独立不嵌套，不复制Gold到输入；不真实外发，不伪造PowerPoint/真实读屏/专家/批准凭证。

## 交付物要求

只将以下最终交付写入`/app/output/`。
- `/app/output/repaired_deck.pptx`：完整12页、原生标题/图表/表/流程和有效语义/备注的可编辑PPT。
- `/app/output/accessibility_review.xlsx`：覆盖12页问题/修复/定位/未测责任、季度/全年公式与缓存、版本边界的Excel。
- `/app/output/handoff.docx`：能让下一负责人继续实际复核的Word：现版、已做/未做、复现、变更重建及授权边界。
- `/app/output/workflow.py`：独立可执行build/stage/verify九节点依赖工作流；真实生成/核验，不是复制Gold或永远PASS。
- `/app/output/release_receipt.json`：绑定当前输入/其他最终文件/节点/真实渲染的回执，内部待审、不对外发布、未测项保留。

## 硬约束（单独列明）

- 只交/app/output/repaired_deck.pptx, /app/output/accessibility_review.xlsx, /app/output/handoff.docx, /app/output/workflow.py, /app/output/release_receipt.json；原生可编辑与内容语义需满足，版式/措辞可合理不同。
- 输入/输出/WORK独立不嵌套；PDF/PNG/节点仅放WORK，不改只读原材料，不真实外联/提交/发布。
- 没有实际PowerPoint/读屏/专家/发布证据须明确未做，不能以空日志/布尔PASS或哈希冒批准。
