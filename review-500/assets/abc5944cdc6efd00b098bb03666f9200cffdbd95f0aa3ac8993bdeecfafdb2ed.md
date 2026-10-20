# 任务口径与权威源

- 领域：医疗 / Med1-患者服务
- 场景：你作为健康教育内容运营专员，需在医疗场景中对医保材料提交清单执行识别重复工单并保留可追溯关联，最终支持哪类服务环节出现超时集中的可追溯决策。

职业分类参考：O*NET 31.0 29-1141.00 Registered Nurses。职业定义：Assess patient health problems and needs, develop and implement nursing care plans, and maintain medical records. Administer nursing care to ill, injured, convalescent, or disabled patients. May advise patients on health maintenance and disease prevention or provide case management. Licensing or registration required.
此对应关系由本管线按原有二级领域编写，不是 O*NET 官方领域划分；保留原业务角色和任务，不把该职业的任意官方任务强行当成本题。材料与规则仍是旧管线构造的虚构案例，不是官方业务规范。
- `facts.csv` 是明细事实权威源；`reported_value` 是待复核旧报告值，不得直接作为最终结论。
- 同一 record_id 取最高 version，仅纳入 status=active；逐条保留两位小数后汇总。
- 类别调整系数只在 `domain-audit-sop` skill 中定义，必须依据该 skill 计算。
- 领域约束：涉及危急描述或临床判断的内容必须停止处理并升级专业人员
- 领域约束：仅使用完全虚构且去标识化的人员与服务记录
