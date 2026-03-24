---
name: order-dispatch
description: >
  订单派工决策技能。调度员接单后，Agent 按阶段给出派工建议，生成工单描述，
  并在调度员确认后通过后端 API 创建工单。凡涉及"帮我派单"、"这个订单派工"、"分配工人"、"接单后派工"
  等场景均应触发此技能。评分逻辑依赖 worker-score 技能。
---

# Order Dispatch — 订单派工决策

## 概述

Agent 收到一个 `order_id` 后，执行以下完整流程：
1. 查询订单和商品数据
2. 为每个阶段独立筛选、评分、选人
3. 生成每张工单的任务描述（纯文本）
4. 调用后端 API 先建议后确认创建工单

---

## 第一步：数据准备

### 1.1 查询订单基本信息

```sql
SELECT o.id, o.order_no, o.priority, o.warehouse_id, o.dispatcher_id,
       c.name AS customer_name
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.id = :order_id
  AND o.status = 'in_progress';
```

若状态不是 `in_progress`，终止流程并告知调用方。

### 1.2 查询订单商品及各阶段技能要求

```sql
SELECT
  p.id         AS product_id,
  p.name       AS product_name,
  p.sku,
  oi.qty,
  p.req_skill_picking,
  p.req_skill_staging,
  p.req_skill_shipping
FROM order_items oi
JOIN products p ON oi.product_id = p.id
WHERE oi.order_id = :order_id;
```

对每个阶段，从结果中提取：
- `required_skill_min`：`MIN(req_skill_{stage})` — 技能硬拦截下限
- `required_skill_max`：`MAX(req_skill_{stage})` — 风险判断上限
- `skill_range_products`：按 `req_skill_{stage}` 排序的商品列表，用于生成工单描述

### 1.3 查询候选工人

```sql
SELECT
  u.id, u.username,
  u.skill_picking, u.skill_staging, u.skill_shipping,
  COUNT(*) FILTER (WHERE wo.status = 'pending')     AS pending_count,
  COUNT(*) FILTER (WHERE wo.status = 'in_progress') AS in_progress_count
FROM users u
LEFT JOIN work_orders wo ON wo.worker_id = u.id
  AND wo.status IN ('pending', 'in_progress')
WHERE u.role        = 'worker'
  AND u.warehouse_id = :warehouse_id
  AND u.is_active    = true
GROUP BY u.id;
```

---

## 第二步：各阶段独立决策

对 `picking`、`staging`、`shipping` 三个阶段，分别执行以下逻辑：

### 2.1 资格过滤

```
worker.skill_{stage} >= required_skill_min_{stage}  →  合格，进入评分
否则                                           →  排除，记录原因
```

### 2.2 评分

对每个合格工人，调用 **worker-score 技能**，传入：
- `skill_level`：工人在本阶段的技能等级
- `pending_count`、`in_progress_count`：当前工单负载

### 2.3 选人

取 `finalScore` 最高者作为本阶段派单对象。同分时按 `worker_id` 升序取第一个。

### 2.4 无合格工人的处理

若某阶段无任何合格工人：
- 该阶段标记为 `unassignable`
- 在最终输出中说明原因（无人满足技能要求 or 所有人负载过重导致分数极低）
- 不阻断其他阶段的决策，继续处理剩余阶段

---

## 第三步：决策工单优先级

工单优先级由 Agent 根据订单优先级和订单状态综合判断，写入 `work_orders.priority`，
供工人在任务列表中识别紧急程度。这是 Agent 的主动决策，不是对订单优先级的简单复制。

### 基础规则：继承订单优先级

```
work_order.priority = order.priority   （默认）
```

### 升级规则：以下情况将优先级提升一档

| 条件 | 说明 | 升级方向 |
|------|------|---------|
| `order.timeout_revert_count >= 1` | 订单已因超时回退过，说明派工延误 | medium → high |
| `order.timeout_revert_count >= 2` | 多次回退，情况严峻 | low → high，medium → high |
| 当前阶段是最后一个未完成阶段（shipping），且前两阶段已完成 | 临门一脚，避免拖单 | low → medium，medium → high |

升级上限为 `high`，不存在超高优先级。

### 降级规则：以下情况可将优先级降低一档

| 条件 | 说明 | 降级方向 |
|------|------|---------|
| 该阶段 `order_stages.status = 'not_started'` 且前序阶段尚未完成 | 阶段尚未到达，不必抢跑 | high → medium |

降级下限为 `low`。

### 最终优先级写入 `description`

优先级决策理由应并入工单 `description` 的末段，示例：
```
技能等级 8，评分 58.9，负载 1 张。订单已超时回退 1 次，工单优先级由 medium 升级为 high。
```

---

## 第四步：生成工单描述

工单描述为纯文本，不使用 markdown，面向执行工人，说明清楚要做什么、要注意什么。

### 描述生成规则

根据工人技能等级与商品技能要求的对比关系，动态生成提示内容：

**情况 A：工人技能等级 ≥ 所有商品要求**
→ 说明需处理的所有商品，无特殊限制提示。

**情况 B：工人技能等级介于最低和最高要求之间**
→ 列出工人可处理的商品（req_skill <= 工人等级），
  明确指出哪些商品超出其能力范围，不得操作，需上报或等待其他工人处理。

**情况 C：工人技能等级恰好等于最低要求**
→ 特别提醒工人操作难度较高，建议放慢节奏、仔细核查。

### 描述模板（以 picking 阶段为例）

```
订单 {order_no}（{customer_name}）- 分拣任务

需要分拣以下商品：
- {product_name}（SKU: {sku}）x {qty}
- {product_name}（SKU: {sku}）x {qty}

注意事项：
{按情况 A/B/C 动态生成的提示，例如：}
商品「精密电子元件」操作难度超出你的当前等级，请勿处理，完成其余商品后立即上报调度员。

优先级：{high/中等/低}
截止要求：请在收到任务后尽快开始。
```

staging、shipping 阶段描述结构相同，将"分拣"替换为"备货装箱"/"发货装车"，内容随阶段调整。

---

## 第五步：调用后端 API 建议与确认创建工单

对每个成功分配的阶段，调用以下接口：

### 接口（建议 + 确认）

```
POST /dispatcher/agent/orders/{order_id}/work-orders/suggest
POST /dispatcher/agent/orders/{order_id}/work-orders/confirm
```

建议接口请求体：

```json
{
  "stage_id": 101,
  "worker_id": 17,
  "intent": "优先保证发货阶段时效"
}
```

确认接口请求体：

```json
{
  "stage_id": 101,
  "worker_id": 17,
  "priority": "high",
  "description": "（第四步生成的纯文本，包含优先级理由）",
  "override_reason": "（存在风险时必填）"
}
```

`stage_id` 从 `order_stages` 表中按 `(order_id, stage_type)` 查得：

```sql
SELECT id FROM order_stages
WHERE order_id = :order_id AND stage_type = :stage_type;
```

### 调用顺序

建议阶段可并发调用；确认创建由调度员逐条确认后执行。

---

## 第六步：输出派工摘要

所有 API 调用完成后，输出一份完整的派工结果，供调度员确认：

```
订单 {order_no} 派工完成

分拣阶段  → 张伟（技能 8 级，评分 58.9，工单优先级 high）
备货阶段  → 李芳（技能 5 级，评分 41.3，工单优先级 medium）
发货阶段  → 王军（技能 6 级，评分 49.7，工单优先级 high ↑ 因订单超时回退 1 次）

未分配阶段：无

说明：
- 张伟当前有 1 张进行中工单，负载惩罚已计入评分。
- 所有工单已通过 API 创建，source 标记为 agent。
```

若有 `unassignable` 阶段，在"未分配阶段"处列出并说明原因，提示调度员人工介入。

---

## 完整决策流程图

```
接收 order_id
     │
     ▼
查询订单 + 商品 + 候选工人
     │
     ▼
┌─────────────────────────────────┐
│  对每个阶段（picking/           │
│  staging/shipping）：           │
│                                 │
│  1. 过滤不满足技能要求的        │
│  2. 调用 worker-score 评分      │
│  3. 取最高分工人                │
│  4. 决策工单优先级              │
│  5. 生成工单描述（纯文本）      │
└─────────────────────────────────┘
     │
     ▼
并发调用 suggest 接口
     │
     ▼
调度员确认后调用 confirm 接口落库
  │
  ▼
输出派工摘要给调度员
```

---

## 边界与异常处理

| 情况 | 处理方式 |
|------|---------|
| 订单不存在或非 in_progress | 终止，返回错误说明 |
| 某阶段 order_stages 记录不存在 | 跳过该阶段，说明阶段尚未初始化 |
| 某阶段无合格工人 | 标记 unassignable，其余阶段继续 |
| API 调用失败 | 记录失败阶段，在摘要中提示调度员手动补派 |
| 同一工人被三个阶段都选中 | 允许，评分时负载已计入，属于合理结果 |