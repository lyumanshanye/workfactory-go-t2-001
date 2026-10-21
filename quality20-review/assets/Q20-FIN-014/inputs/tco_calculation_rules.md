# TCO（总拥有成本）与首年现金流计算规则

本文件定义采购与租赁方案的成本计算口径，所有金额单位为人民币（元），精度要求精确到元，**禁止使用浮点数（float）进行金额累加或乘除运算**，必须使用 Python 标准库 `decimal.Decimal`。

---

## 1. 年度维保费用计算

每家供应商的每台设备每年维保费用（含7×24现场支持）计算公式：

```
annual_maintenance = base_maintenance_annual
if not support_247_included:
    annual_maintenance += cost_add_247_annual
```

> 说明：所有设备必须满足7×24小时现场维保要求。若供应商未标配该服务（`support_247_included = false`），则须加购 `cost_add_247_annual` 费用。

---

## 2. 购买模式

### 2.1 首年现金流支出

```
first_year_buy = unit_price_buy + annual_maintenance
```

即购买全款 + 第一年维保费用。

### 2.2 三年TCO

```
tco_buy = unit_price_buy + tco_horizon_years * annual_maintenance
```

即购买全款 + 三年维保费用总和。

---

## 3. 租赁模式

### 3.1 首年现金流支出

```
first_year_lease = lease_down_payment + lease_annual_rent + annual_maintenance
```

即租赁首付 + 第一年租金 + 第一年维保费用。

### 3.2 三年TCO

```
tco_lease = lease_down_payment + tco_horizon_years * lease_annual_rent + tco_horizon_years * annual_maintenance
```

即首付 + 三年租金 + 三年维保费用总和。

---

## 4. 组合方案汇总

对于一个包含多台设备的采购组合方案：

- **首年现金流总额** = 各设备首年现金流之和
- **三年TCO总额** = 各设备三年TCO之和

---

## 5. 精度要求

- 所有金额字段从JSON读取后，必须立即转换为 `Decimal` 类型
- 所有加减乘除运算均在 `Decimal` 类型上完成
- 最终输出结果应使用 `quantize(Decimal('1'))` 取整到元
- 禁止在金额计算过程中使用 `float` 类型

---

## 6. 参考背景

本计算口径参考了行业最佳实践关于资产购置的比较原则——不能仅比较月费或标价，要把同一使用期间的费用及现金占用放在一起看。具体商业实践背景参见 `procurement_research_note.md`。

本文件为内部业务计算规则，不构成任何司法辖区的强制会计准则。
