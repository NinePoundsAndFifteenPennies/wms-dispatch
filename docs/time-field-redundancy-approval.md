# 时间字段冗余审批清单

本文档用于审批“可能冗余的时间字段”，避免在生产中误删关键审计数据。

## 审批说明

- `结论` 列：`建议删除` / `建议保留` / `待业务确认`
- `审批结果` 列：由负责人填写 `同意` / `拒绝` / `暂缓`
- 默认策略：审计字段（`created_at`, `updated_at`）优先保留，除非有明确替代链路。

---

## A. 已执行项（本轮已落地）

| 表 | 字段 | 原因 | 结论 | 审批结果 |
|---|---|---|---|---|
| work_orders | assigned_at | 创建工单时与 `created_at` 同时写入，语义重叠 | 建议删除 | 同意（已执行） |

---

## B. 待审批候选项

| 表 | 字段候选 | 冗余判断 | 影响面 | 结论 | 审批结果 |
|---|---|---|---|---|---|
| work_orders | updated_at | 多数场景可由状态时间字段替代，但仍有列表排序与审计价值 | 后端列表排序、前端表格 | 建议保留 |  |
| order_stages | updated_at | 与 `completed_at` 部分重叠，但阶段中间态仍需追踪 | 阶段流转排查、审计 | 建议保留 |  |
| transfer_orders | updated_at | 与审批/执行/完成时间部分重叠，仍用于通用“最近变更” | 管理端查询排序 | 建议保留 |  |
| inbound_records | updated_at | 与 `confirmed_at` 在已确认场景重叠，但未确认场景仍有变更追踪价值 | 入库过程排查 | 建议保留 |  |
| orders | updated_at | 与 `accepted_at/completed_at/cancelled_at` 有局部重叠，但覆盖范围更广 | 列表排序、审计、变更追踪 | 建议保留 |  |

---

## C. 非冗余（不建议删除）

| 表 | 字段组 | 说明 |
|---|---|---|
| orders | accepted_at / completed_at / cancelled_at / last_reverted_at | 分别对应不同业务事件，不能合并 |
| work_orders | created_at / started_at / completed_at / terminated_at | 分别对应派发、开工、完工、终止 |
| transfer_orders | approved_at / executed_at / completed_at | 审批、执行、完成语义不同 |
| inbound_records | expected_arrival_at / confirmed_at | 预计到货与实际确认语义不同 |

---

## 建议审批顺序

1. 先审批 `updated_at` 是否进入下一轮精简范围（建议默认保留）。
2. 若同意精简，再按“单表单迁移”方式逐项处理，禁止跨域大批量删除。
3. 每次删除前补齐替代字段与查询改造，确保报表和排序不回归。
