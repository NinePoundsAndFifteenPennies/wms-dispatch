---
name: worker-score
description: >
  工人综合评分计算技能。输入工人的技能等级和当前工单负载，输出该工人在某阶段的
  综合评分（越高越优先派单）。被 order-dispatch 技能调用，也可单独用于
  "这个工人现在适合接单吗"、"比较两名工人"等场景。
---

# Worker Score — 工人综合评分

## 输入

| 参数 | 类型 | 说明 |
|------|------|------|
| `skill_level` | int (0–10) | 工人在目标阶段的技能等级 |
| `pending_count` | int ≥ 0 | 当前 pending 工单数 |
| `in_progress_count` | int ≥ 0 | 当前 in_progress 工单数 |

> 工单负载查询 SQL：
> ```sql
> SELECT
>   COUNT(*) FILTER (WHERE status = 'pending')     AS pending_count,
>   COUNT(*) FILTER (WHERE status = 'in_progress') AS in_progress_count
> FROM work_orders
> WHERE worker_id = :worker_id;
> ```

---

## 算法

### 1. 效率倍率（对数曲线）

反映技能等级带来的完成速度优势，高等级收益递减。

```
MAX_SKILL   = 10
MAX_SPEEDUP = 3.0

speedup(skill) = 1 + (MAX_SPEEDUP - 1) × ln(1 + skill/MAX_SKILL × (e - 1))
```

| 等级 | 倍率（≈） |
|------|----------|
| 0    | 1.00×    |
| 3    | 1.72×    |
| 5    | 2.10×    |
| 8    | 2.65×    |
| 10   | 3.00×    |

### 2. 负载惩罚

在途工单越多，可用带宽越低。pending 比 in_progress 惩罚更轻（还没开始，可能很快完成）。

```
load = in_progress_count × 1.0 + pending_count × 0.5

loadPenalty(load) = 1 / (1 + load × LOAD_FACTOR)

LOAD_FACTOR = 0.4
```

| 在途情况 | load 值 | 惩罚系数（≈） |
|---------|---------|-------------|
| 空闲    | 0       | 1.00        |
| 1 in_progress | 1.0 | 0.71   |
| 2 in_progress | 2.0 | 0.56   |
| 1 in_progress + 2 pending | 2.0 | 0.56 |
| 3 in_progress | 3.0 | 0.45   |

### 3. 综合评分

评分只反映客观能力与当前负载，不掺入订单优先级。优先级由 order-dispatch 在创建工单时单独决策。

```
effNorm = (speedup - 1) / (MAX_SPEEDUP - 1)   ∈ [0, 1]

finalScore = effNorm × 100 × loadPenalty
```

**示例**：技能 8，1 个 in_progress：
```
speedup     ≈ 2.65
effNorm     = (2.65 - 1) / 2 = 0.825
load        = 1.0
loadPenalty = 1 / (1 + 1.0 × 0.4) = 0.714
finalScore  = 0.825 × 100 × 0.714 ≈ 58.9
```

对比空闲时同人：`0.825 × 100 = 82.5`，负载导致分值下降约 29%。

---

## 输出

```json
{
  "worker_id": 17,
  "skill_level": 8,
  "speedup": 2.65,
  "load": 1.0,
  "load_penalty": 0.714,
  "final_score": 58.9
}
```

---

## 边界规则

| 情况 | 处理 |
|------|------|
| `skill_level` < 最低要求 | 不参与评分，调用方过滤，此函数不处理资格判断 |
| `skill_level` = 0 | speedup = 1.0×，正常参与评分 |
| 多人分数相同 | 由调用方按 `worker_id` 升序作 tiebreaker |