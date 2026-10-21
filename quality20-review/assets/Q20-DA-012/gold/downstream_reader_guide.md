# GDP数据产品 — 下游阅读与避坑说明

> **文档版本**: 1.0.0  
> **编写日期**: 2026-10-21  
> **适用契约**: gdp_metadata_contract.json v1.0.0

---

## 1. 产品概述与数据溯源

### 1.1 数据来源

本数据产品的原始数据来自 **World Bank World Development Indicators (WDI)** 公开API，通过以下三个指标代码获取：

| 指标代码 | 官方名称 | 单位 |
|---|---|---|
| `NY.GDP.MKTP.CD` | GDP (current US$) | Current US$ |
| `NY.GDP.MKTP.KD` | GDP (constant 2015 US$) | Constant 2015 US$ |
| `NY.GDP.MKTP.KD.ZG` | GDP growth (annual %) | Annual % |

### 1.2 时间信息

- **API数据集 lastupdated**: 2026-10-08
- **本次抓取时间**: 2026-10-20T22:02:54 UTC

### 1.3 数据结构说明

本数据产品采用 **宽表结构**：每条记录包含一个国家在某一个年度的三个GDP指标数值。这种设计便于下游系统直接消费和可视化，无需额外的行列转置操作。

---

## 2. 字段字典

| 字段名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `metadata` | object | ✅ | 数据元信息头 |
| `metadata.api_lastupdated` | string (date) | ✅ | WDI数据集整体更新日期（见第4节详解） |
| `metadata.retrieved_at` | string (date-time) | ✅ | 本次数据抓取的UTC时间 |
| `records` | array | ✅ | 观测数据数组 |
| `records[].country_iso3` | string | ✅ | ISO 3166-1 alpha-3 国家代码 |
| `records[].country_name` | string | ✅ | 国家英文名 |
| `records[].year` | string | ✅ | 观测年份 (YYYY) |
| `records[].gdp_current_usd` | number \| null | ✅ | 现价美元GDP (NY.GDP.MKTP.CD) |
| `records[].gdp_constant_2015_usd` | number \| null | ✅ | 2015不变价美元GDP (NY.GDP.MKTP.KD) |
| `records[].gdp_growth_annual_pct` | number \| null | ✅ | 实际GDP年增长率 (NY.GDP.MKTP.KD.ZG) |

### 2.1 指标官方定义（来源：WDI API sourceNote）

**gdp_current_usd (NY.GDP.MKTP.CD)**:  
Gross domestic product is the total income earned through the production of goods and services in an economic territory during an accounting period. This indicator is expressed in **current prices**, meaning no adjustment has been made to account for price changes over time. This indicator is expressed in **United States dollars**.

**gdp_constant_2015_usd (NY.GDP.MKTP.KD)**:  
Gross domestic product is the total income earned through the production of goods and services in an economic territory during an accounting period. This indicator is expressed in **constant prices**, meaning the series has been adjusted to account for price changes over time. **The reference year for this adjustment is 2015.** This indicator is expressed in **United States dollars**.

**gdp_growth_annual_pct (NY.GDP.MKTP.KD.ZG)**:  
This indicator denotes the **percentage change over each previous year** of the **constant price (base year 2015) series** in United States dollars.

---

## 3. 核心口径说明（作者中文归纳，非官方译文）

> **重要声明**：以下内容基于世界银行公开帮助文档的中文归纳整理，非官方翻译。具体英文原文请参考对应链接。

### 3.1 现价 vs 不变价

- **现价美元 (CD)** 同时包含三个因素的变化：实际产出变动、价格变动（通货膨胀/紧缩）、汇率变动。
- **不变价美元 (KD)** 以2015年为基准年，剔除了价格变动的影响，仅反映实物量的跨期变化。
- 现价美元GDP同比下跌 ≠ 实际产出下降。可能仅是汇率贬值或物价下降所致。
- 某年现价美元低于不变价美元，不代表数据错误。两者量纲不同，不可直接比较大小。

### 3.2 实际增长率的唯一正确来源

**实际GDP增长率应直接使用 `gdp_growth_annual_pct` (KD.ZG) 字段**，或基于 `gdp_constant_2015_usd` (KD) 相邻年份的比值计算。

**严禁使用 `gdp_current_usd` (CD) 的同比变化来替代实际增长率。**

---

## 4. ⚠️ 避坑指南（常见误区）

### 误区一：用现价美元 (CD) 计算实际经济增长率

**错误做法**：`growth = (CD_2024 / CD_2023) - 1`

**为什么错**：CD同时受价格变动和汇率变动影响。例如，某国本币对美元贬值30%，即使实际产出增长5%，其现价美元GDP也可能同比下降。用CD算出的"增长率"混淆了实际增长、通胀和汇率三个完全不同的经济现象。

**正确做法**：直接使用 `gdp_growth_annual_pct` 字段，或基于 `gdp_constant_2015_usd` 计算：  
`growth = (KD_year / KD_prev_year) - 1`

**依据**：世界银行帮助文档明确指出 current vs constant price 的区别。

### 误区二：用 CD/KD 比率当作GDP平减指数或通胀率

**错误做法**：`deflator = CD / KD` 或 `inflation = (CD/KD) - 1`

**为什么错**：CD和KD都是以美元计价的。CD/KD的比率混合了**国内价格变动**和**美元汇率变动**（GDP deflator × 汇率指数），并不等于国内GDP平减指数。真正的GDP平减指数需要以本币计算：`deflator_local = (名义GDP本币 / 实际GDP本币)`。

**正确做法**：如需GDP平减指数，应从WDI获取本币计价的GDP数据（如 `NY.GDP.MKTP.KN`）另行计算，不得直接用美元数据替代。

**依据**：世界银行不变价序列推导方法说明。

### 误区三：混淆 API lastupdated 与各国实际发布日期

**错误做法**：将 `api_lastupdated` (2026-10-08) 理解为所有国家数据的首次发布日期。

**为什么错**：`lastupdated` 是世界银行WDI数据集整体批量更新的日期，不代表各国统计局向WDI提交数据的具体日期。各国统计局的发布时间各不相同，有些国家可能提前数月已公布，有些可能在此日期之后还有修正。本数据产品不提供各国具体发布日期信息。

**正确做法**：将 `api_lastupdated` 视为"数据截止日"（data vintage），用于标识数据版本，不用于推断发布时间线。

### 误区四：自行回填历史数据或编造修订版本

**错误做法**：发现某年数据缺失，用前后年份插值或按比例外推补全。

**为什么错**：本数据产品仅提供同一次冻结的WDI快照，不提供历史版本（vintage）对比。世界银行和各国统计局可能对历史数据进行修订，但这些修订信息不在本数据产品中。自行编造填补会引入虚假精度。

**正确做法**：缺失年份留空（null），不做插值。如需历史修订信息，应直接查询各国统计局或WDI完整历史数据库。

### 误区五：将"D0"污染稿视为有效数据

**错误说明**：在任何内部文档中可能出现的标记为"D0"的数据版本或文件，**不是任何官方WDI历史修订版本**。D0是作者原创的污染数据稿（test artifact），仅用于内部质量校验。

**正确做法**：忽略所有标记为D0的数据，不得将其纳入任何分析或报告。

---

## 5. 数据边界与限制

1. **本数据产品不包含**：季度数据、月度数据、本币计价GDP、人均GDP、行业细分GDP。
2. **基期说明**：不变价GDP的基准年为2015年。如果世界银行未来更换基准年（如改为2020年），历史序列将发生断裂，需特别注意。
3. **修订风险**：各国可能在后续年份修订其国民账户数据，导致本快照中的历史值与未来版本不一致。本数据产品不承诺自动跟踪修订。
4. **null值**：如某国家某年某指标返回null，表示WDI当前版本中暂无该观测值，不应自行填补。

---

## 6. 版权与免责

- **数据来源归属**：World Bank. World Development Indicators. 数据使用应保留World Bank及数据来源归属。
- **免责声明**：本数据产品及其说明文档不表示World Bank背书任何特定业务结论或分析结果。所有使用本数据产品进行的分析、预测或决策，由使用者自行负责。
- **指标定义版权**：指标定义来源于World Bank WDI API官方sourceNote，版权归World Bank所有。

---

## 7. 联系与支持

如对数据口径有疑问，请：
1. 首先查阅本文档第3、4节
2. 参考World Bank官方帮助文档链接
3. 联系数据产品团队确认，不要自行推断
