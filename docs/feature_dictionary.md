# 特征字典（Feature Dictionary）— M4 特征工程

> 逐项记录 `build_features` 生成的每个特征的名称、含义、计算公式与所用日期范围，作为防泄漏审计依据（配合 `tests/test_windows_leakage.py`）。

## 0. 记法与约定

- **预测起点 t**：`input_end_date`（输入窗口最后一天）。
- **输入窗口**：`[t - (L - 1), t]`，L = `task.lookback_days`（7 / 14 / 28）。
- **目标窗口**：`[t + 1, t + H]`，H = `task.horizon_days`（固定 7）。
- **目标 y**：目标窗口内该类别 `purchase` 事件总和（一个标量）：`y = Σ_{d=t+1}^{t+H} purchase_d`。
- **严格时间隔离**：所有事件统计特征只对「预测起点及之前」的输入窗口求和，且一律裁剪到 `[input_start_date, input_end_date]`，绝不读取目标期或未来任何一天。日历特征只使用目标周「已知的日历信息」（星期 / 月份 / 是否跨月 / 公开节假日），不读取任何未来事件数据。
- **短窗口安全**：当 `L = 7` 时没有完整的「前 7 天」（`[t-13, t-7]` 全部早于 `input_start`），`*_prev7_total` 全为 0（真实的「无前 7 天计数」）；由此派生的 `*_trend` 与 `purchase_wow_ratio` 按下方「分母为零兜底」规则取中性值，**不会退化成原始总量**。
- **分母为零兜底**：比例 / 趋势特征的分母若为 0，按中性值兜底（避免除零、`inf` 与量级失真的原始值）——
  - 趋势类（`purchase_trend` / `views_trend` / `cart_trend`）→ `0.0`（表示「无变化」）；
  - 周环比（`purchase_wow_ratio`）→ `1.0`（表示「与上周持平」）；
  - 转化比（`cart_view_ratio` / `purchase_cart_ratio`）→ `0.0`（表示「无转化」）。
  以上均为「事件计数之比」，非独立用户转化率。

## 1. 购买特征（始终生成）

| 特征名 | 含义 | 公式 | 所用日期范围 |
| --- | --- | --- | --- |
| `purchase_last7_total` | 最近 7 天购买总量 | Σ purchase | `[t-6, t]`（裁剪到输入窗口） |
| `purchase_prev7_total` | 前 7 天购买总量 | Σ purchase | `[t-13, t-7]`（裁剪到输入窗口；L=7 时为 0） |
| `purchase_last14_total` | 最近 14 天购买总量 | Σ purchase | `[t-13, t]`（裁剪到输入窗口） |
| `purchase_last7_avg` | 最近 7 天购买日均 | last7_total / 7 | `[t-6, t]` |
| `purchase_trend` | 购买近期趋势（周环比变化率） | (last7_total − prev7_total) / prev7_total；prev7_total=0 时取 0.0 | 用到 `[t-13, t]` |

## 2. 浏览与加购特征（`use_behavior=True` 时生成）

| 特征名 | 含义 | 公式 | 所用日期范围 |
| --- | --- | --- | --- |
| `views_last7_total` | 最近 7 天浏览总量 | Σ views | `[t-6, t]` |
| `views_prev7_total` | 前 7 天浏览总量 | Σ views | `[t-13, t-7]`（L=7 时为 0） |
| `views_trend` | 浏览趋势 | (views_last7 − views_prev7) / views_prev7；views_prev7=0 时取 0.0 | `[t-13, t]` |
| `cart_last7_total` | 最近 7 天加购总量 | Σ cart | `[t-6, t]` |
| `cart_prev7_total` | 前 7 天加购总量 | Σ cart | `[t-13, t-7]`（L=7 时为 0） |
| `cart_trend` | 加购趋势 | (cart_last7 − cart_prev7) / cart_prev7；cart_prev7=0 时取 0.0 | `[t-13, t]` |

## 3. 比例特征（`use_behavior=True` 时生成）

| 特征名 | 含义 | 公式 | 所用日期范围 |
| --- | --- | --- | --- |
| `cart_view_ratio` | 加购 / 浏览（事件计数比） | cart_last7 / views_last7；views_last7=0 时取 0.0 | `[t-6, t]` |
| `purchase_cart_ratio` | 购买 / 加购（事件计数比） | purchase_last7 / cart_last7；cart_last7=0 时取 0.0 | `[t-6, t]` |
| `purchase_wow_ratio` | 最近一周购买 / 前一周购买 | purchase_last7 / purchase_prev7；purchase_prev7=0 时取 1.0 | `[t-13, t]` |

## 4. 日历特征（始终生成；只用目标周日历信息）

| 特征名 | 含义 | 公式 | 所用日期范围 |
| --- | --- | --- | --- |
| `cal_target_weekday` | 预测周起始星期 | target_start.weekday()（0=周一 … 6=周日） | 目标周 `[t+1, t+H]`（仅日历，无事件数据） |
| `cal_target_month` | 预测周起始月份 | target_start.month（1–12） | 目标周（仅日历） |
| `cal_target_cross_month` | 预测周是否跨月 | 1 if target_start.month ≠ target_end.month else 0 | 目标周（仅日历） |
| `cal_target_holiday` | 预测周是否含公开节假日 | 1 if 目标周任一天 ∈ holidays else 0 | 目标周（仅公开日历，无促销记录） |

## 5. 类别身份特征（`use_category=True` 时生成）

| 特征名 | 含义 | 公式 | 所用日期范围 |
| --- | --- | --- | --- |
| `cat_is_<id>` | 类别 One-Hot 编码 | 1 if category_id == id else 0 | 无（类别身份，不涉时间） |

- 每个 `config['category_ids']`（即 M3 开发期选定的 `variants['10'].selected_ids`）对应一列，按 id 整数升序排列。
- 编码映射只在开发期类别列表上拟合，**不使用测试期数据**。

## 6. 消融开关（供 M6 做 E2 / E3）

| 开关 | 作用 | `False` 时保留 | `True` 时新增 |
| --- | --- | --- | --- |
| `use_behavior`（E2） | 浏览与加购 | 仅第 1、4 节（购买 + 日历） | 第 2、3 节（浏览 / 加购 / 比例） |
| `use_category`（E3） | 类别身份 | 无类别列 | 第 5 节（`cat_is_<id>` One-Hot） |

- M4 只提供开关与特征输出；消融实验的运行与结论分析归 M6。

## 7. 输出列顺序

`WINDOW_META_FIELDS`（sample_id, category_id, input_start_date, input_end_date, target_start_date, target_end_date）→ 特征列（按第 1 → 2 → 3 → 4 → 5 节顺序）→ `y`。
