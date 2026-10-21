# 本项目的有限规划模型（不是完整引擎规范）

所有金额均为英镑；一年由year_days个游戏日组成。车辆为整数0至max_per_option辆，合计不超过fleet_limit；同exclusive_group只能选一个运输选项。各选项的demand由本选项全部车辆共享，不因车辆增加而复制。

每辆年循环数=floor(year_days/cycle_days)，完整循环每次可运capacity单位。总运量取需求与总运能的较小值，按capacity拆满批及末批。收入必须按每批向下取整后相加。

计费距离为起终点坐标的曼哈顿距离；travelled_tiles是背景行程信息。时间t使用age_periods，单位为货物老化周期，1周期约2.5游戏日；station_wait_days不属于货物老化；cycle_days已包括等待、装卸及返程。f=max(31,255-max(0,t-days1)-max(0,t-days1-days2))，单批收入=floor(base*批量*计费距离*f/2^21)。days2是第一阈值之后的持续期。

首年净现金=全年分批收入-车辆采购支出-完整年度运行费。压力情景把需求改为floor(原需求*stress_demand_percent/100)，老化周期增加stress_age_periods、循环天数增加stress_cycle_days，其余不变。两种预算分别约束采购支出，且压力净现金不低于minimum_stress_net。

在所有可行组合中，先最大化压力净现金，再最大化基准净现金，再最小化采购额，最后按routes.json输入顺序的车辆向量字典序升序打破同分。对每种预算保留最优及紧随其后的前三个可行组合；无可行组合时best为null并给出零可行数。

这份数学合同及路线/预算属于原创演练。机制背景复用旧题固定Wiki参考，但不承诺复刻当前引擎、逐位数值、极迟到衰减或真实玩家经济。无需外部搜索。预算案例之间是待比较的财务情景，不是审批优先级陷阱。
