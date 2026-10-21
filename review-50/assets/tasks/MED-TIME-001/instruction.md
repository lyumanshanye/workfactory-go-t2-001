# HPV项目实施后的患者服务Skill修订、历史回放与告知包

## 业务场景与任务说明

你是非临床患者服务培训专员。国家HPV项目已开始，废弃服务Skill仍把公开日当实施日、套9–45岁营销范围并自动批准。请依据冻结官方通知和技术方案、服务负责人R2，真正改造Skill与脚本，运行合成咨询回放，交付待审公众告知和改造审阅稿。不是给真实患者下接种许可。

业务判断基准时点：2025-11-12 09:00；时区：Asia/Shanghai。检索/下载时间不是政策生效时间。

## 可使用的源文件

以下输入均位于只读目录`/app/input_files/`。无需联网补充事实；使用冻结材料完成交付。
- `/app/input_files/S01_七部门通知.docx`：官方通知冻结正文及三日期来源。
- `/app/input_files/S02_实施技术方案正文.docx`：官方技术方案正文，不含接种率附件。
- `/app/input_files/S03_编辑委托与服务边界.docx`：原创编辑委托、权限、R2非临床路由合同及交付要求。
- `/app/input_files/S04_合成咨询回放.json`：13条纯合成咨询回放，无真实患者信息。
- `/app/input_files/legacy_skill/SKILL.md`：明确废弃、未部署的原创故障Skill组成；仅供修订，不作医学规则来源。
- `/app/input_files/legacy_skill/references/policy.json`：明确废弃、未部署的原创故障Skill组成；仅供修订，不作医学规则来源。
- `/app/input_files/legacy_skill/scripts/route_intake.py`：明确废弃、未部署的原创故障Skill组成；仅供修订，不作医学规则来源。

## 工作要求

- [Q1] 核读S01/S02及S03消息权限，区分签署/公开/实施/取证时间，拒绝无权扩大免费范围。
- [Q2] 把legacy_skill复制修订为指定五文件的可复用Skill，含可发现入口、来源和本地R2边界、有效标准库CLI及实际行为测试；不只修改说明文字。
- [Q3] 按R2完整实现日期、史缺失/矛盾、年龄/范围、特殊健康、已全程和既往部分史分流及输入错误处理；所有输出均不得给临床许可或预约确认。
- [Q4] 实际运行更新后的Skill处理S04全部13例，保存case_results.json；逐例有ID、日期、可计算年龄、路由、理由与源定位，不复制生日/健康标记。
- [Q5] 生成1页待审公众告知，准确说明国家项目范围、实施日、常规双价2剂/6个月、医护核验、既往史咨询和30分钟留观；不承诺库存、预约或个体处方。
- [Q6] 改造审阅稿给出旧错到新规则/来源/实现的映射、13例回放矩阵、真实测试情况、未验事项和人工发布复核动作；不得伪造外部服务或专业批准。

## 交付物要求

只将以下最终交付写入`/app/output/`。
- `/app/output/hpv-service-notice/SKILL.md`：可复用修订Skill组成文件，保持相对路径关系。
- `/app/output/hpv-service-notice/references/policy.json`：可复用修订Skill组成文件，保持相对路径关系。
- `/app/output/hpv-service-notice/references/service-boundary.md`：可复用修订Skill组成文件，保持相对路径关系。
- `/app/output/hpv-service-notice/scripts/route_intake.py`：可复用修订Skill组成文件，保持相对路径关系。
- `/app/output/hpv-service-notice/tests/test_routing.py`：可复用修订Skill组成文件，保持相对路径关系。
- `/app/output/case_results.json`：实际运行13例的非临床回放结果。
- `/app/output/public_notice.docx`：1页待审公众服务告知。
- `/app/output/change_review.docx`：旧错映射、回放矩阵及复核/发布边界审阅稿。

## 硬约束（单独列明）

- 只交指定8个文件到/app/output/；Skill目录不可打包，不安装/修改全局技能。
- 原输入只读；所有机构委托/案例/旧错稿是原创训练情境，不是实际机构SOP或患者记录。
- 不自行补国家政策边界、地方免费条件或个体临床处方，不实际预约、联系、接种或发布。
- 公众稿不超过1页，不含病例/生日/健康标记；脚本仅输出非临床路由与false批准状态。
