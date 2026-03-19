# 数据库设计文档 (极简重构版，不可变)

## 📊 数据库架构

---

## 资源设计

所有图片等资源都放在根目录 `resources/` 下，按类型分子目录：

```text
resources/
  ├── warehouse_covers/   // 仓库封面图
  ├── product_images/     // 产品图片
  ├── user_avatars/       // 用户头像
  └── other/              // 其他资源，后续自定义
```

---

## 设计原则

1. **极简技能模型**：抛弃繁琐的技能字典映射，将技能严格限定为`picking`、`staging`、`shipping`三个作业阶段，直接通过数值等级比对（工人等级 ≥ 产品要求等级）进行任务调度匹配。
2. 明确库存口径：库存现存量与占用量分离，避免字段歧义。
3. 核心动作可审计：取消、终止、库存变更、审批结果必须可追溯。
4. 高并发可实现：关键流程可通过事务 + 行级锁保证一致性。

---

### 1. users（用户表）
系统中的所有用户（管理员、调度员、工人）。**引入了扁平化的三阶段技能等级**。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 用户唯一标识 |
| username | VARCHAR(64) | UNIQUE, NOT NULL | 登录用户名 |
| password | VARCHAR(255) | NOT NULL | 密码（bcrypt 哈希存储） |
| email | VARCHAR(128) | UNIQUE, NOT NULL | 邮箱地址 |
| role | VARCHAR(16) | NOT NULL | 角色：admin / dispatcher / worker |
| warehouse_id | INTEGER | FK → warehouses.id | 所属仓库（调度员和工人必填，管理员为空） |
| skill_picking | INTEGER | NOT NULL, DEFAULT 0 | 分拣技能等级（0代表不会，数值越大越熟练） |
| skill_staging | INTEGER | NOT NULL, DEFAULT 0 | 备货装箱技能等级 |
| skill_shipping | INTEGER | NOT NULL, DEFAULT 0 | 发货装车技能等级 |
| avatar | VARCHAR(512) | | 头像URL/路径 |
| description | TEXT | | 用户描述/备注 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 账户是否激活（软禁用） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 最后修改时间 |

**关键约束**：
- `role` 通过 CHECK 约束限制为 `'admin'`、`'dispatcher'`、`'worker'`
- `CHECK (role = 'admin' OR warehouse_id IS NOT NULL)`
- `CHECK (skill_picking >= 0 AND skill_staging >= 0 AND skill_shipping >= 0)`
- 管理员账号不可被禁用（业务层保证）

---

### 2. customers（客户表）
订单客户信息

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 客户ID |
| name | VARCHAR(128) | NOT NULL | 客户名称/公司名 |
| contact | VARCHAR(128) | NOT NULL | 联系方式（电话/邮箱） |
| address | TEXT | | 送货地址 |
| description | TEXT | | 客户备注 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否有效（软删除） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 最后修改时间 |

---

### 3. warehouses（仓库表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 仓库ID |
| name | VARCHAR(128) | UNIQUE, NOT NULL | 仓库名称 |
| address | TEXT | NOT NULL | 仓库地址 |
| latitude | DECIMAL(9,6) | | 纬度 |
| longitude | DECIMAL(9,6) | | 经度 |
| capacity | INTEGER | NOT NULL, DEFAULT 0 | 仓库容量（最大库存单位数） |
| cover_image | VARCHAR(512) | | 仓库封面图路径 |
| description | TEXT | | 仓库描述 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否有效（软删除） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

---

### 4. products（产品表）
产品/SKU 主数据。**直接内嵌三阶段的最低作业技能要求**。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 产品ID |
| sku | VARCHAR(64) | UNIQUE, NOT NULL | SKU编码 |
| name | VARCHAR(128) | NOT NULL | 产品名称 |
| category | VARCHAR(64) | | 产品类别 |
| unit_weight | DECIMAL(10,2) | | 单位重量（克） |
| unit_of_measure | VARCHAR(16) | NOT NULL, DEFAULT 'piece' | 计量单位（piece / box / kg 等） |
| req_skill_picking | INTEGER | NOT NULL, DEFAULT 0 | 分拣该产品要求的最低技能等级 |
| req_skill_staging | INTEGER | NOT NULL, DEFAULT 0 | 备货该产品要求的最低技能等级 |
| req_skill_shipping | INTEGER | NOT NULL, DEFAULT 0 | 发货该产品要求的最低技能等级 |
| cover_image | VARCHAR(512) | | 产品图片路径 |
| description | TEXT | | 产品描述 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 是否有效（软下架） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

**约束**：`CHECK (req_skill_picking >= 0 AND req_skill_staging >= 0 AND req_skill_shipping >= 0)`

---

### 5. inventory（库存表）
实时库存主表（频繁更新）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 库存记录ID |
| warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 仓库ID |
| product_id | INTEGER | FK → products.id, NOT NULL | 产品ID |
| qty_on_hand | INTEGER | NOT NULL, DEFAULT 0 | 仓内现存量 |
| qty_reserved | INTEGER | NOT NULL, DEFAULT 0 | 已接单预留量 |
| qty_locked | INTEGER | NOT NULL, DEFAULT 0 | 调拨软锁定量 |
| qty_threshold | INTEGER | NOT NULL, DEFAULT 0 | 库存阈值 |
| qty_available | INTEGER | GENERATED ALWAYS AS (qty_on_hand - qty_reserved - qty_locked) STORED | 可用库存（计算字段） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

**约束**：
- `UNIQUE (warehouse_id, product_id)`
- `CHECK (qty_on_hand >= 0 AND qty_reserved >= 0 AND qty_locked >= 0)`
- `CHECK (qty_on_hand >= qty_locked)`（复合约束：现存量绝不能小于调拨锁定量）
- `CHECK (qty_on_hand - qty_reserved - qty_locked >= 0)`（确保可用库存永远不会变成负数）

**统一口径**：
```text
可接单库存 = qty_available (由数据库底层实时计算，严禁代码写入)
可调拨库存 = qty_available
库存预警   = qty_available < qty_threshold
```

---

### 6. inventory_movements（库存流水表）
用于库存审计、对账和问题追溯

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGSERIAL | PK | 流水ID |
| inventory_id | INTEGER | FK → inventory.id, NOT NULL | 对应库存记录 |
| warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 仓库ID |
| product_id | INTEGER | FK → products.id, NOT NULL | 产品ID |
| change_type | VARCHAR(32) | NOT NULL | reserve / reserve_release / ship_deduct / transfer_lock / transfer_unlock / transfer_deduct / inbound_confirm / stocktake_adjust |
| delta_on_hand | INTEGER | NOT NULL, DEFAULT 0 | 现存量变化 |
| delta_reserved | INTEGER | NOT NULL, DEFAULT 0 | 预留量变化 |
| delta_locked | INTEGER | NOT NULL, DEFAULT 0 | 锁定量变化 |
| before_on_hand | INTEGER | NOT NULL | 变更前现存量 |
| before_reserved | INTEGER | NOT NULL | 变更前预留量 |
| before_locked | INTEGER | NOT NULL | 变更前锁定量 |
| after_on_hand | INTEGER | NOT NULL | 变更后现存量 |
| after_reserved | INTEGER | NOT NULL | 变更后预留量 |
| after_locked | INTEGER | NOT NULL | 变更后锁定量 |
| related_type | VARCHAR(32) | | 关联资源类型（order / transfer_order / inbound_record / stocktake） |
| related_id | INTEGER | | 关联资源ID |
| operated_by | INTEGER | FK → users.id | 操作人 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |

---

### 7. stocktakes（盘点事件表）
用于记录每次人工盘点的离散事件，`inventory_movements` 通过 `related_type='stocktake'` + `related_id` 进行关联。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 盘点事件ID |
| inventory_id | INTEGER | FK → inventory.id, NOT NULL | 对应库存记录 |
| before_on_hand | INTEGER | NOT NULL | 盘点前现存量 |
| after_on_hand | INTEGER | NOT NULL | 盘点后现存量 |
| delta_on_hand | INTEGER | NOT NULL | 现存量变化 |
| reason | TEXT | | 本次人工盘点调整原因 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 事件创建时间 |

---

### 8. orders（订单表）
业务订单主表（不存阶段明细）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 订单ID |
| order_no | VARCHAR(32) | UNIQUE, NOT NULL | 订单号 |
| customer_id | INTEGER | FK → customers.id, NOT NULL | 客户ID |
| warehouse_id | INTEGER | FK → warehouses.id | 发货仓库(调度员接单后关联其所在仓库) |
| dispatcher_id | INTEGER | FK → users.id | 责任调度员（接单后填写） |
| description | TEXT | | 订单备注 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending_acceptance' | pending_acceptance / in_progress / completed / cancelled |
| priority | VARCHAR(8) | NOT NULL, DEFAULT 'medium' | high / medium / low |
| accepted_at | TIMESTAMP | | 接单时间 |
| completed_at | TIMESTAMP | | 完成时间 |
| cancelled_at | TIMESTAMP | | 取消时间 |
| cancelled_by | INTEGER | FK → users.id | 取消人 |
| cancellation_reason | TEXT | | 取消原因 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

**说明**：订单总金额通过查询 `SUM(order_items.qty * order_items.unit_price)` 动态计算，不单独存储。

**取消权限与规则口径（与业务规则文档一致）**：
- `pending_acceptance`：仅管理员可取消。
- `in_progress`：仅责任调度员可取消，且取消前必须不存在 `pending`/`in_progress` 工单。
- 取消后写入管理员通知（当前单管理员场景落 1 条 `notifications` 记录）。

**结构结论**：`orders` 与 `order_items` 保持拆分，不合并。
- 订单天然是 1:N 明细模型，合并会破坏范式并引入重复字段。
- 多 SKU 扩展、部分改价、审计追溯在分表设计下更清晰。
- 库存预留/释放/扣减与明细数量映射依赖 `order_items` 粒度。
- 动态金额计算（`SUM(qty * unit_price)`）与报表统计更可维护。

---

### 9. order_items（订单明细表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 明细ID |
| order_id | INTEGER | FK → orders.id, NOT NULL | 所属订单 |
| product_id | INTEGER | FK → products.id, NOT NULL | 产品ID |
| qty | INTEGER | NOT NULL, CHECK (qty > 0) | 数量 |
| unit_price | INTEGER | NOT NULL, CHECK (unit_price >= 0) | 单价（以分为单位，避免精度丢失）|

---

### 10. order_stages（订单阶段表）
用于承接“同阶段并行、跨阶段串行、手动标记阶段完成”规则

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 阶段记录ID |
| order_id | INTEGER | FK → orders.id, NOT NULL | 订单ID |
| stage_type | VARCHAR(16) | NOT NULL | picking / staging / shipping |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'not_started' | not_started / in_progress / completed |
| completion_type | VARCHAR(8) | | auto / manual |
| completed_at | TIMESTAMP | | 阶段完成时间 |
| completed_by | INTEGER | FK → users.id | 阶段完成操作人 |
| remark | TEXT | | 手动阶段完成备注 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

**约束**：`UNIQUE (order_id, stage_type)`

**阶段完成规则（由应用层保证）**：
阶段完成有两条路径，均由应用层在写操作前校验，数据库不直接强制：

1. **自动完成**：某阶段下所有关联 `work_orders` 的 status 均为 `completed` 时，系统自动将该阶段的 status 置为 `completed`，`completion_type` 记为 `auto`，`completed_at` 记录当前时间，`completed_by` 为空。
2. **手动标记**：调度员主动触发。应用层须同时满足以下两个前置条件才允许执行：
   * 该阶段下至少存在一张 `status = 'completed'` 的工单。
   * **【核心拦截条件】该阶段下不存在任何 `status IN ('in_progress', 'pending')` 的工单（剩余未完成工单，包括派了还没干的，须先由调度员 terminated）。**
   * 满足条件后，status 置为 `completed`，`completion_type` 记为 `manual`，`completed_by` 记录操作调度员 ID，`remark` 可填写标记原因。

**关门规则**：阶段一旦 `status = 'completed'`，应用层在创建该阶段新工单时必须拒绝请求并返回错误，不允许任何绕过。
**串行推进规则**：创建下一阶段工单前，应用层须校验上一阶段的 `status = 'completed'`，否则拒绝创建。三个阶段的顺序固定为 `picking` → `staging` → `shipping`。

---

### 11. work_orders（工作订单表）
分配给工人的执行任务

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 工作单ID |
| order_id | INTEGER | FK → orders.id, NOT NULL | 关联订单 |
| stage_type | VARCHAR(16) | NOT NULL | picking / staging / shipping |
| worker_id | INTEGER | FK → users.id, NOT NULL | 工人ID |
| dispatcher_id | INTEGER | FK → users.id, NOT NULL | 分配调度员 |
| warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 操作仓库（冗余字段，用于查询优化） |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | pending / in_progress / completed / terminated |
| priority | VARCHAR(8) | NOT NULL, DEFAULT 'medium' | high / medium / low |
| deadline | TIMESTAMP | | 截止时间 |
| description | TEXT | | 任务描述 |
| source | VARCHAR(8) | NOT NULL, DEFAULT 'manual' | manual / agent |
| agent_reason | TEXT | | AI分配理由 |
| assigned_at | TIMESTAMP | | 分配时间 |
| started_at | TIMESTAMP | | 开始时间 |
| completed_at | TIMESTAMP | | 完成时间 |
| terminated_at | TIMESTAMP | | 终止时间 |
| terminated_by | INTEGER | FK → users.id | 终止人 |
| termination_reason | TEXT | | 终止原因 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

**一致性约束建议（推荐入库）**：
- 增加 `orders(id, dispatcher_id)` 复合唯一约束。
- 增加复合外键 `work_orders(order_id, dispatcher_id) -> orders(id, dispatcher_id)`，确保工单调度员与订单责任调度员一致。
- 使用约束触发器保证“已取消订单不可存在 `pending`/`in_progress` 工单”。

---

### 12. work_order_notes（工单备注表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 备注ID |
| work_order_id | INTEGER | FK → work_orders.id, NOT NULL | 工单ID |
| note_type | VARCHAR(16) | NOT NULL | normal / damaged / qty_mismatch / other |
| content | TEXT | NOT NULL | 备注内容 |
| created_by | INTEGER | FK → users.id, NOT NULL | 创建人 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |

---

### 13. transfer_orders（调拨单表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 调拨单ID |
| product_id | INTEGER | FK → products.id, NOT NULL | 产品ID |
| from_warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 源仓库 |
| to_warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 目标仓库 |
| requested_by | INTEGER | FK → users.id, NOT NULL | 申请人 |
| approved_by | INTEGER | FK → users.id | 审批人 |
| qty | INTEGER | NOT NULL, CHECK (qty > 0) | 调拨数量 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | pending / approved / rejected / cancelled / completed |
| description | TEXT | | 调拨说明 |
| rejection_reason | TEXT | | 驳回原因 |
| source | VARCHAR(8) | NOT NULL, DEFAULT 'manual' | manual / agent |
| agent_reason | TEXT | | AI建议理由 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |
| approved_at | TIMESTAMP | | 审批时间 |
| executed_at | TIMESTAMP | | 来源仓扣减完成时间 |
| completed_at | TIMESTAMP | | 目标仓确认入库完成时间 |

**约束**：`CHECK (from_warehouse_id != to_warehouse_id)`

---

### 14. inbound_records（待入库记录表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 记录ID |
| transfer_order_id | INTEGER | FK → transfer_orders.id, NOT NULL | 关联调拨单 |
| warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 目标仓库 |
| product_id | INTEGER | FK → products.id, NOT NULL | 产品ID |
| qty | INTEGER | NOT NULL, CHECK (qty > 0) | 待入库数量 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | pending / confirmed |
| expected_arrival_at | TIMESTAMP | | 预期到达时间 |
| confirmed_by | INTEGER | FK → users.id | 确认入库人 |
| confirmed_at | TIMESTAMP | | 确认入库时间 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

**约束**：`UNIQUE (transfer_order_id)`

---

### 15. notifications（通知表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 通知ID |
| user_id | INTEGER | FK → users.id, NOT NULL | 接收用户ID |
| type | VARCHAR(32) | NOT NULL | 通知类型 |
| title | VARCHAR(256) | NOT NULL | 标题 |
| body | TEXT | | 内容 |
| related_id | INTEGER | | 关联资源ID |
| related_type | VARCHAR(32) | | 关联资源类型 |
| is_read | BOOLEAN | NOT NULL, DEFAULT false | 是否已读 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |

---

### 16. reports（报表表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 报表ID |
| generated_by | INTEGER | FK → users.id, NOT NULL | 生成人 |
| target_user_id | INTEGER | FK → users.id | 目标人员 |
| period_start | DATE | NOT NULL | 统计开始 |
| period_end | DATE | NOT NULL, CHECK (period_end >= period_start) | 统计结束 |
| stats_json | JSONB | | 结构化统计数据 |
| content | TEXT | | 报表内容 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 生成时间 |

---

## 极简调度核心逻辑（Agent 匹配指引）

AI Agent 或系统在为某个阶段（如 `picking`）分配工单时，只需执行极其简单的比对，无需任何复杂的 JOIN。例如，寻找符合订单（假定包含产品1、产品2）分拣要求的空闲工人：

```sql
SELECT u.id, u.username
FROM users u
WHERE u.role = 'worker'
  AND u.warehouse_id = :warehouse_id
  AND u.is_active = true
  -- 匹配逻辑：工人的分拣等级 >= 订单内所有产品分拣要求的最高值
  AND u.skill_picking >= (
      SELECT MAX(p.req_skill_picking)
      FROM order_items oi
      JOIN products p ON oi.product_id = p.id
      WHERE oi.order_id = :order_id
  )
  -- 确保当前空闲
  AND NOT EXISTS (
      SELECT 1 FROM work_orders wo 
      WHERE wo.worker_id = u.id AND wo.status = 'in_progress'
  );
```

---

## 关键关系图

```text
users (1) ──── (N) orders (dispatcher_id / cancelled_by)
  │   ├──── (N) work_orders (worker_id / dispatcher_id / terminated_by)
  │   ├──── (N) work_order_notes (created_by)
  │   ├──── (N) transfer_orders (requested_by / approved_by)
  │   ├──── (N) inbound_records (confirmed_by)
  │   ├──── (N) notifications
  │   └──── (N) reports (generated_by / target_user_id)

warehouses (1) ──── (N) inventory
            ├──── (N) orders
            ├──── (N) work_orders
            ├──── (N) inbound_records
            └──── (N) transfer_orders (from / to)

orders (1) ──── (N) order_items
         ├──── (N) order_stages
         └──── (N) work_orders

inventory (1) ──── (N) stocktakes
          └──── (N) inventory_movements

transfer_orders (1) ──── (1) inbound_records
```

---

## 事务与并发策略（必须执行）
1. 接单、调拨申请、调拨审批、确认入库均在数据库事务内完成。
2. 上述流程对涉及的 `inventory` 行执行 `SELECT ... FOR UPDATE` 行级锁。
3. 业务写操作同步写入 `inventory_movements`，保证可审计可追溯。
4. 订单取消属于库存关键路径（涉及预留释放），同样应纳入事务与行级锁策略。

**并发口径说明**：
- 数据一致性由数据库约束体系兜底（CHECK/FK/触发器），确保不会超卖。
- `SELECT ... FOR UPDATE` 主要提升并发体验与性能：减少无效 `UPDATE + ROLLBACK`，更早返回库存不足。
- 不使用 `FOR UPDATE` 也不会突破一致性约束，但在高并发下冲突成本更高。

---

## 索引建议
*(省略了常规的身份与状态索引)*

```sql
-- users 增加技能索引，提升 AI 查询速度
CREATE INDEX idx_users_skills ON users(skill_picking, skill_staging, skill_shipping);

-- inventory 必须维持联合唯一约束
CREATE UNIQUE INDEX idx_inventory_warehouse_product ON inventory(warehouse_id, product_id);

-- 订单并发与熔断扫描优化
CREATE INDEX idx_work_orders_order_status ON work_orders(order_id, status);
CREATE INDEX idx_orders_dispatcher_status_accepted_at ON orders(dispatcher_id, status, accepted_at);
CREATE INDEX idx_orders_in_progress_accepted_at ON orders(accepted_at) WHERE status = 'in_progress';
```