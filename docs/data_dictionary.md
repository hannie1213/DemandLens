# DemandLens 数据字典（M2 负责）

适用对象：原始事件日志 → 日汇总表 `daily_all_categories.csv`（契约 3.6）。
主数据集：Multi-category Store（大型多类别电商，Rees46 发布）；外部验证候选：Cosmetics Shop。
两组数据的字段结构一致，处理口径一致。

## 1. 原始事件 CSV（每月一个文件，不入库）

| 列 | 类型 | 含义 | M2 处理 |
|---|---|---|---|
| event_time | 文本，`YYYY-MM-DD HH:MM:SS UTC` | 事件时间（UTC） | 取前 10 位为日期；非法值计数后排除 |
| event_type | 文本 | view / cart / purchase（部分月份另有 remove_from_cart） | 小写归一化；仅契约三类进入聚合，其余单独计数 |
| product_id | 整数 | 商品 ID | 不读取（初版不用，见作业 3.1） |
| category_id | 整数 | 商品类别 ID，聚合主键之一 | 必须可解析为整数，否则计数并排除 |
| category_code | 文本，可空 | 类别路径（如 `computers.notebook`），存在缺失 | 记录每个类别出现过的编码集合，冲突时标记 |
| brand | 文本，可空 | 品牌，存在缺失 | 不读取 |
| price | 浮点 | 事件记录中的价格（币种未确认，存在 0 价格） | 不读取 |
| user_id | 整数 | 用户 ID；事件数 ≠ 独立用户数 | 不读取 |
| user_session | 文本 | 会话 ID；与订单不是同一概念 | 不读取 |

读取方式（需求 D1）：`pandas.read_csv(..., usecols=[...4 列...], chunksize=1_000_000)`
分块流式处理，单个月文件（最大 ~9 GiB）可在普通笔记本上完成。

## 2. 日汇总表 `daily_all_categories.csv`（契约 3.6）

一个 (date, category_id) 组合一行；**不补零、不筛选类别**（M2 产物）。
M3 审核质量、选择类别并补齐日历后产出 `daily_category.csv`，下游只用后者。

| 列 | 类型 | 说明 |
|---|---|---|
| date | 日期（UTC） | 事件所在 UTC 日，ISO 格式 `YYYY-MM-DD` |
| category_id | 整数 (int64) | 商品类别 ID |
| category_code | 文本，可空 | 该类别出现过的类别路径；跨块/跨月不一致时以 `\|` 连接全部取值并在核对表标记 |
| views | 整数 ≥ 0 | 当日该类别 view 事件数 |
| cart | 整数 ≥ 0 | 当日该类别 cart 事件数（不含 remove_from_cart） |
| purchase | 整数 ≥ 0 | 当日该类别 purchase 事件数；**这是唯一的预测标签来源** |

语义边界（务必随数据传递）：
- 事件数 ≠ 订单数 ≠ 销售件数；purchase 事件是「未来 7 天购买活动」的代理标签。
- 缺失行 ≠ 零购买：没有记录的 (类别, 日期) 可能是采集缺口，由 M3 审核后决定补零或剔除。
- remove_from_cart 不属于契约事件，不影响 cart 列。

## 3. 聚合核对表 `reports/tables/aggregation_check.csv`

列：`dataset, month, check, raw_value, aggregated_value, diff, status`。
关键检查项（status=OK/FAIL，其余为 INFO）：

| check | 含义 |
|---|---|
| count:view / count:cart / count:purchase | 进入聚合的有效契约事件数 == 日汇总列之和（D2 验收） |
| count_raw_all:{event} | 原始文件中该事件类型全部行数（含无效行，信息项） |
| aggregatable_rows | 进入聚合的行数 == 日汇总三列之和 |
| excluded:other_event_types | 契约外事件（如 remove_from_cart）行数 |
| invalid:date_rows / invalid:category_rows | 日期非法 / 类别 ID 非法的行数 |
| duplicate:same_contract_cols_est | 在契约四列（event_time/event_type/category_id/category_code）上完全相同的行数估计。**注意**：读取不含 user_id，热门商品同秒的多次正常浏览也会计入，不能当作真重复行；跨块重复未覆盖 |
| coverage:categories / coverage:dates | 该月覆盖的类别数 / 日期数 |
| consistency:category_code_conflicts | 同一 category_id 出现多个 category_code 的类别数 |
| cross_month:category_code_conflicts | 跨月编码不一致的类别数（合并表层面） |
| file:size_bytes | 原始文件字节数 |

## 4. 化妆品店日汇总 `daily_all_categories_cosmetics.csv`

列与语义与第 2 节完全一致；用于（候选）外部验证，不参与开发期调参。
注意其 category_code 缺失比例非常高（十月约 96.8% 事件无编码，473/489 个类别完全无编码，
以核对表实测数字为准），类别可读名基本不可用，以匿名 ID 为主。

## 5. 初步时间切分 `reports/tables/preliminary_split.csv`

列：`date, split, eval_block_start`。
- split ∈ {train, val, test}：同一 UTC 日所有类别同一分区（作业 4.6）。
- eval_block_start：互不重叠的 7 天评价区间的起始日（仅 val/test 日期有值），
  用于避免连续滑动窗口评价高度相关；不满 7 天的尾部区间不参与评价。
- 本文件是 M2 代拟草案，最终边界由 M3 审核后写入 `config/config.yaml` 并冻结。
