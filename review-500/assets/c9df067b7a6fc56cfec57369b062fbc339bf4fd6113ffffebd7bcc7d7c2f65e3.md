# 任务口径与权威源

- 领域：设计 / DE3-产品与包装设计
- 场景：你作为包装设计师，需在设计场景中对保护与运输性能执行执行跌落与运输测试，最终支持量产偏差接受标准的可追溯决策。

职业分类参考：O*NET 31.0 27-1021.00 Commercial and Industrial Designers。职业定义：Design and develop manufactured products, such as cars, home appliances, and children's toys. Combine artistic talent with research on product use, marketing, and materials to create the most functional and appealing product design.
此对应关系由本管线按原有二级领域编写，不是 O*NET 官方领域划分；保留原业务角色和任务，不把该职业的任意官方任务强行当成本题。材料与规则仍是旧管线构造的虚构案例，不是官方业务规范。
- `facts.csv` 是明细事实权威源；`reported_value` 是待复核旧报告值，不得直接作为最终结论。
- 同一 record_id 取最高 version，仅纳入 status=active；逐条保留两位小数后汇总。
- 类别调整系数只在 `domain-audit-sop` skill 中定义，必须依据该 skill 计算。
- 领域约束：结构方案须经样机和运输测试验证
- 领域约束：材料环保声称须有可追溯证据
