
# 数据库设计文档（动态更新）

## 📊 数据库架构 V3

> **V3 更新说明**：修复了 V2 中存在的多项设计漏洞，包括工人状态派生 SQL 逻辑错误、缺失的唯一约束、
> 缺少的字段、不合理的索引、以及安全相关的审计日志设计。具体变更见各表的 **⚠️ V3 修复** 标注。

---

## 资源设计

所有图片等资源都放在根目录 `resources/` 下，按类型分子目录：

```
resources/
  ├── warehouse_covers/   // 仓库封面图
  ├── product_images/     // 产品图片
  ├── user_avatars/       // 用户头像
  └── other/              // 其他资源，后续自定义
```

---

### **1️⃣ users（用户表）**
系统中的所有用户（管理员、调度员、工人）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 用户唯一标识 |
| username | VARCHAR(64) | UNIQUE, NOT NULL | 登录用户名 |
| password | VARCHAR(255) | NOT NULL | 密码（bcrypt 哈希存储） |
| email | VARCHAR(128) | UNIQUE, NOT NULL | 邮箱地址 |
| role | VARCHAR(16) | NOT NULL | **角色分类**：admin / dispatcher / worker |
| avatar | VARCHAR(512) | | 头像URL/路径 |
| description | TEXT | | 用户描述/备注 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 账户是否激活（软禁用） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 最后修改时间 |

**关键约束**：
- `username` 和 `email` 均为 UNIQUE，防止重复注册
- `role` 通过 CHECK 约束限制为 `'admin'`、`'dispatcher'`、`'worker'` 三个值
- 管理员账号不可被禁用（由业务逻辑层保证）

---

### **2️⃣ customers（客户表）**
订单客户信息

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 客户ID |
| name | VARCHAR(128) | NOT NULL | 客户名称/公司名 |
| contact | VARCHAR(128) | NOT NULL | 联系方式（电话/邮箱） |
| address | TEXT | | 送货地址 |
| description | TEXT | | 客户备注 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 最后修改时间 |

> **⚠️ V3 修复**：补全了列类型和约束定义（V2 中缺少类型列）；新增 `updated_at` 字段以支持修改追踪。

---

### **3️⃣ warehouses（仓库表）**
从文本 location 升级为精确坐标定位

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 仓库ID |
| name | VARCHAR(128) | UNIQUE, NOT NULL | 仓库名称 |
| address | TEXT | NOT NULL | 仓库地址（文本描述） |
| latitude | DECIMAL(9,6) | | 纬度（Nominatim 定位结果） |
| longitude | DECIMAL(9,6) | | 经度（Nominatim 定位结果） |
| capacity | INTEGER | NOT NULL, DEFAULT 0 | 仓库容量（最大库存单位数） |
| cover_image | VARCHAR(512) | | 仓库封面图路径 |
| description | TEXT | | 仓库描述 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

**设计说明**：
- ✅ 分离 address（文本）和坐标（数值），便于地图展示与距离计算
- ✅ 经纬度允许为空（地址解析可能失败）

> **⚠️ V3 修复**：移除了 `(latitude, longitude)` 的 UNIQUE 索引（见下方索引章节说明）。

---

### **4️⃣ workers（工人表）**
去掉 current_status，通过查询派生

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 工人ID |
| user_id | INTEGER | FK → users.id, UNIQUE, NOT NULL | 关联 users 表 |
| warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 所属仓库 |
| description | TEXT | | 工人备注/岗位描述 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 入职时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

**工人状态派生查询**：

> **⚠️ V3 修复**：原 V2 使用 `MAX(wo.status)` 做字符串比较来判断状态，存在逻辑错误——
> 按字母序 `'pending' > 'in_progress'`，导致有进行中工单时仍可能返回 `'idle'`。
> 此外 V2 中 ELSE 分支注释为"无任务时**离职**"，语义不正确。以下为修正后的查询：

```sql
-- 获取工人当前状态（修正版）
SELECT
  w.id,
  CASE
    WHEN EXISTS (
      SELECT 1 FROM work_orders wo
      WHERE wo.worker_id = w.id AND wo.status = 'in_progress'
    ) THEN 'busy'          -- 有正在执行的工单 → 忙碌
    WHEN EXISTS (
      SELECT 1 FROM work_orders wo
      WHERE wo.worker_id = w.id AND wo.status = 'pending'
    ) THEN 'assigned'      -- 有待开始的工单但未在执行 → 已分配
    ELSE 'idle'            -- 无未完成工单 → 空闲
  END AS current_status
FROM workers w
WHERE w.id = ?;
```

**优点**：
- ✅ 避免状态不同步问题，状态由 work_orders 驱动
- ✅ 使用 EXISTS 子查询代替 MAX 字符串比较，逻辑正确且高效
- ✅ 减少 UPDATE 操作

---

### **5️⃣ skill_tag_definitions（技能定义表）**
系统中定义的所有可用技能

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 技能标签ID |
| name | VARCHAR(64) | UNIQUE, NOT NULL | 技能名称（如"搬运"、"分拣"、"装箱"） |
| description | TEXT | | 技能描述 |

**示例**：
```
id=1, name="搬运", description="能力搬运较重物品"
id=2, name="分拣", description="按订单快速分拣产品"
id=3, name="装箱打包", description="规范装箱、防损"
```

---

### **6️⃣ worker_skills（工人技能表）**
多对多：工人拥有的技能

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| worker_id | INTEGER | FK → workers.id, NOT NULL | 工人ID |
| skill_tag_id | INTEGER | FK → skill_tag_definitions.id, NOT NULL | 技能ID |

**约束**：`PRIMARY KEY (worker_id, skill_tag_id)`

> **⚠️ V3 修复**：新增复合主键，防止同一工人重复关联同一技能。

**示例**：
```
worker_id=5, skill_tag_id=1  -- 工人5会搬运
worker_id=5, skill_tag_id=2  -- 工人5也会分拣
```

---

### **7️⃣ products（产品表）**
产品/SKU 主数据

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 产品ID |
| sku | VARCHAR(64) | UNIQUE, NOT NULL | SKU编码 |
| name | VARCHAR(128) | NOT NULL | 产品名称 |
| category | VARCHAR(64) | | 产品类别 |
| unit_weight | DECIMAL(10,2) | | 单位重量（克） |
| cover_image | VARCHAR(512) | | 产品图片路径 |
| description | TEXT | | 产品描述/特殊要求 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

---

### **8️⃣ product_required_skills（产品所需技能表）**
多对多：处理某产品需要的技能

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| product_id | INTEGER | FK → products.id, NOT NULL | 产品ID |
| skill_tag_id | INTEGER | FK → skill_tag_definitions.id, NOT NULL | 需要的技能ID |

**约束**：`PRIMARY KEY (product_id, skill_tag_id)`

> **⚠️ V3 修复**：新增复合主键，防止重复关联。

**示例**：
```
product_id=100, skill_tag_id=3  -- 易碎产品需要小心搬运
product_id=100, skill_tag_id=5  -- 易碎产品需要特殊包装
```

---

### **9️⃣ inventory（库存表）**
实时库存管理（频繁更新）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 库存记录ID |
| warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 仓库ID |
| product_id | INTEGER | FK → products.id, NOT NULL | 产品ID |
| qty_available | INTEGER | NOT NULL, DEFAULT 0, CHECK (qty_available >= 0) | 可用数量（立即可发） |
| qty_reserved | INTEGER | NOT NULL, DEFAULT 0, CHECK (qty_reserved >= 0) | 已预留数量（已分配待发） |
| qty_threshold | INTEGER | NOT NULL, DEFAULT 0, CHECK (qty_threshold >= 0) | 库存阈值（预警点） |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 最后更新时间 |

**约束**：`UNIQUE (warehouse_id, product_id)` — 每个仓库每种产品只有一条库存记录

> **⚠️ V3 修复**：新增 `(warehouse_id, product_id)` 唯一约束，防止同仓同产品出现多条记录导致库存计算错误。
> 新增 `CHECK >= 0` 约束防止库存数量出现负数。

**关键业务逻辑**：
```
总库存 = qty_available + qty_reserved
可分配 = qty_available（不能超过此数）
库存预警 = qty_available < qty_threshold
```

---

### **🔟 orders（订单表）**
业务订单主表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 订单ID |
| order_no | VARCHAR(32) | UNIQUE, NOT NULL | 订单号（业务编码） |
| customer_id | INTEGER | FK → customers.id, NOT NULL | 客户ID |
| warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 发货仓库 |
| dispatcher_id | INTEGER | FK → users.id | 负责调度员（可为空，管理员创建时可不指定） |
| description | TEXT | | 订单备注 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | 待处理 / 进行中 / 已完成 / 已取消 |
| priority | VARCHAR(8) | NOT NULL, DEFAULT 'medium' | high / medium / low |
| total_amount | DECIMAL(12,2) | NOT NULL, DEFAULT 0 | 订单总金额 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |
| completed_at | TIMESTAMP | | 完成时间 |

**注意事项**：
- `total_amount` 应在新增/修改 order_items 时同步更新（通过应用层或数据库触发器），避免与明细不一致
- `dispatcher_id` 可为空：管理员创建订单时可能尚未指定调度员
- `status` 通过 CHECK 约束限制为 `'pending'`、`'in_progress'`、`'completed'`、`'cancelled'`

---

### **1️⃣1️⃣ order_items（订单明细表）**
订单包含的产品明细（一对多）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 明细ID |
| order_id | INTEGER | FK → orders.id, NOT NULL | 所属订单 |
| product_id | INTEGER | FK → products.id, NOT NULL | 产品ID |
| qty | INTEGER | NOT NULL, CHECK (qty > 0) | 数量 |
| unit_price | DECIMAL(10,2) | NOT NULL, CHECK (unit_price >= 0) | 单价 |

**计算**：`line_amount = qty × unit_price`

> **⚠️ V3 修复**：新增 `CHECK > 0`（qty）和 `CHECK >= 0`（unit_price）约束防止无效数据。

---

### **1️⃣2️⃣ work_orders（工作订单表）**
分配给工人的具体任务

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 工作单ID |
| order_id | INTEGER | FK → orders.id, NOT NULL | 关联的业务订单 |
| worker_id | INTEGER | FK → workers.id, NOT NULL | 分配的工人 |
| dispatcher_id | INTEGER | FK → users.id, NOT NULL | 调度员（谁分配的） |
| warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 操作的仓库 |
| task_type | VARCHAR(16) | NOT NULL | picking / staging / shipping |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | pending / in_progress / completed / cancelled |
| priority | VARCHAR(8) | NOT NULL, DEFAULT 'medium' | high / medium / low |
| description | TEXT | | 任务描述 |
| source | VARCHAR(8) | NOT NULL, DEFAULT 'manual' | manual（人工）/ agent（AI 创建） |
| agent_reason | TEXT | | AI 创建原因说明 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| assigned_at | TIMESTAMP | | 分配时间 |
| started_at | TIMESTAMP | | 开始执行时间 |
| completed_at | TIMESTAMP | | 完成时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

> **⚠️ V3 修复**：新增 `created_at` 字段（V2 中缺失，无法记录工单创建时间）。

**设计说明**：
- `task_type` 通过 CHECK 约束限制为 `'picking'`、`'staging'`、`'shipping'`
- `status` 通过 CHECK 约束限制为 `'pending'`、`'in_progress'`、`'completed'`、`'cancelled'`
- `source` 通过 CHECK 约束限制为 `'manual'`、`'agent'`

---

### **1️⃣3️⃣ work_order_notes（工作单备注表）**
替代原来 work_orders 中的 completion_note 字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 备注ID |
| work_order_id | INTEGER | FK → work_orders.id, NOT NULL | 所属工作单 |
| note_type | VARCHAR(16) | NOT NULL | normal / damaged / qty_mismatch / other |
| content | TEXT | NOT NULL | 备注内容（详细描述） |
| created_by | INTEGER | FK → users.id, NOT NULL | 创建人（工人/调度员/管理员） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |

**优点**：
- ✅ 分离关注点（任务状态 vs 完成说明）
- ✅ 支持多条备注（一个 work_order 可以有多条 note）
- ✅ 追踪谁写的备注（审计需要）

---

### **1️⃣4️⃣ transfer_orders（调拨单表）**
仓库间的产品调拨

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 调拨单ID |
| product_id | INTEGER | FK → products.id, NOT NULL | 调拨的产品 |
| from_warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 源仓库 |
| to_warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 目标仓库 |
| initiating_warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 发起调拨的仓库（可能 ≠ from） |
| requested_by | INTEGER | FK → users.id, NOT NULL | 申请人 |
| approved_by | INTEGER | FK → users.id | 批准人（审批后填写） |
| qty | INTEGER | NOT NULL, CHECK (qty > 0) | 调拨数量 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | pending / approved / rejected / executed / cancelled |
| description | TEXT | | 调拨原因/说明 |
| rejection_reason | TEXT | | 驳回原因（驳回时填写） |
| agent_reason | TEXT | | AI 建议原因 |
| source | VARCHAR(8) | NOT NULL, DEFAULT 'manual' | manual / agent |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |
| approved_at | TIMESTAMP | | 审批时间（通过或驳回） |

> **⚠️ V3 修复**：
> - 新增 `rejection_reason` 字段（README 中提到"驳回时可填写原因"，V2 缺少此字段）
> - 新增 `source` 字段（区分人工发起与 AI 建议的调拨）
> - `status` 新增 `'rejected'` 状态（V2 只有 待批准/已批准/已执行/已取消，无法表示驳回）
> - `from_warehouse_id` 和 `to_warehouse_id` 增加 CHECK 约束：`from_warehouse_id != to_warehouse_id`

---

### **1️⃣5️⃣ notifications（通知表）**
系统消息推送/提醒

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 通知ID |
| user_id | INTEGER | FK → users.id, NOT NULL | 接收用户ID |
| type | VARCHAR(32) | NOT NULL | 通知类型（见下方枚举） |
| title | VARCHAR(256) | NOT NULL | 通知标题 |
| body | TEXT | | 通知内容 |
| related_id | INTEGER | | 关联资源 ID |
| related_type | VARCHAR(32) | | 关联资源类型 |
| is_read | BOOLEAN | NOT NULL, DEFAULT false | 是否已读 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |

**通知类型枚举**：

| type 值 | 说明 |
|---------|------|
| work_order_assigned | 任务分配通知（→ 工人） |
| work_order_completed | 任务完成通知（→ 调度员） |
| work_order_timeout | 工单超时未完成告警（→ 调度员） |
| inventory_low | 库存低于阈值预警（→ 调度员 + 管理员） |
| transfer_requested | 调拨申请通知（→ 管理员） |
| transfer_approved | 调拨审批通过通知（→ 申请人） |
| transfer_rejected | 调拨审批驳回通知（→ 申请人） |
| order_completed | 订单完成通知 |

> **⚠️ V3 修复**：
> - 新增 `work_order_timeout` 类型（README 中描述了超时工单告警，V2 通知类型中遗漏）
> - 新增 `transfer_requested`、`transfer_rejected` 类型以完整覆盖审批流程
> - `related_id` + `related_type` 属于多态关联模式，无法建立数据库级外键约束；
>   数据完整性需由应用层保证，查询时务必同时过滤 `related_type`

---

### **1️⃣6️⃣ reports（报表表）**
手动触发生成的效率分析报表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 报表ID |
| generated_by | INTEGER | FK → users.id, NOT NULL | 生成人 |
| target_user_id | INTEGER | FK → users.id | 目标人员（查看某人员的报表时填写） |
| period_start | DATE | NOT NULL | 统计周期开始日期 |
| period_end | DATE | NOT NULL | 统计周期结束日期 |
| stats_json | JSONB | | 统计数据（结构化 JSON） |
| content | TEXT | | 报表内容（Markdown 或 HTML） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 生成时间 |

> **⚠️ V3 修复**：
> - 新增 `target_user_id` 字段（README 中提到"选择查看某人员的全部历史数据"，V2 中无此字段）
> - `stats_json` 类型改为 `JSONB`（PostgreSQL 原生 JSON 类型，支持索引和查询）
> - 增加 CHECK 约束：`period_start <= period_end`

---

### **1️⃣7️⃣ audit_logs（审计日志表）** ⭐ V3 新增
记录系统中的关键操作，满足仓储场景的审计追溯需求

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGSERIAL | PK | 日志ID |
| user_id | INTEGER | FK → users.id | 操作人（系统自动操作时可为空） |
| action | VARCHAR(64) | NOT NULL | 操作类型（如 `create_order`、`approve_transfer`、`update_inventory`） |
| resource_type | VARCHAR(32) | NOT NULL | 操作对象类型（如 `order`、`work_order`、`inventory`） |
| resource_id | INTEGER | | 操作对象 ID |
| detail | JSONB | | 操作详情（变更前后的关键字段快照） |
| ip_address | VARCHAR(45) | | 操作者 IP 地址 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 操作时间 |

**用途**：
- ✅ 库存变更追溯（谁在什么时候修改了库存数量）
- ✅ 订单状态变更记录
- ✅ 审批操作留痕
- ✅ 安全事件审计（异常登录、越权操作尝试等）

> 该表为只写追加表，不允许 UPDATE 或 DELETE。建议设置表级 RULE 或策略禁止修改。

---

## 🔗 关键关系图

```
users (1) ──── (0..1) workers
  │
  ├── (1) ───── (N) orders (dispatcher_id)
  ├── (1) ───── (N) work_orders (dispatcher_id)
  ├── (1) ───── (N) notifications
  ├── (1) ───── (N) reports (generated_by)
  └── (1) ───── (N) audit_logs

customers (1) ──── (N) orders

warehouses (1) ──── (N) workers
            ├──── (N) orders
            ├──── (N) inventory
            └──── (N) work_orders

workers (1) ──── (N) work_orders
   │
   └── (M) ──── (M) skill_tag_definitions (via worker_skills)

orders (1) ──── (N) order_items
         └──── (N) work_orders

order_items (N) ──── (1) products

products (M) ──── (M) skill_tag_definitions (via product_required_skills)
          └──── (N) inventory

work_orders (1) ──── (N) work_order_notes

inventory (N) ──── (1) warehouses
           └──── (1) products

transfer_orders (N) ──── (1) warehouses (from / to / initiating)
                 └──── (1) products
```

---

## 📝 索引建议

```sql
-- === 查询性能索引 ===
CREATE INDEX idx_workers_user_id ON workers(user_id);
CREATE INDEX idx_workers_warehouse_id ON workers(warehouse_id);
CREATE INDEX idx_work_orders_worker_id ON work_orders(worker_id);
CREATE INDEX idx_work_orders_order_id ON work_orders(order_id);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_worker_status ON work_orders(worker_id, status);  -- 工人状态派生查询优化
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_warehouse_id ON orders(warehouse_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_notifications_user_read ON notifications(user_id, is_read);   -- 用户未读通知查询
CREATE INDEX idx_notifications_created_at ON notifications(created_at);
CREATE INDEX idx_work_order_notes_work_order_id ON work_order_notes(work_order_id);
CREATE INDEX idx_transfer_orders_status ON transfer_orders(status);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- === 唯一约束 ===
CREATE UNIQUE INDEX idx_users_username ON users(username);
CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX idx_order_no ON orders(order_no);
CREATE UNIQUE INDEX idx_product_sku ON products(sku);
CREATE UNIQUE INDEX idx_inventory_warehouse_product ON inventory(warehouse_id, product_id);
CREATE UNIQUE INDEX idx_skill_tag_name ON skill_tag_definitions(name);
```

> **⚠️ V3 修复 — 移除 `idx_warehouse_location`**：
> V2 中对 `(latitude, longitude)` 建立了 UNIQUE 索引，存在以下问题：
> 1. 浮点数比较不可靠，微小的精度差异可能导致误判
> 2. 同一地点（如物流园区）可能有多个仓库
> 3. 经纬度可以为空值（地址解析失败时），UNIQUE 索引对 NULL 的处理因数据库而异
>
> 如需按地理位置查询仓库，建议使用 PostGIS 扩展的空间索引。

> **⚠️ V3 修复 — 优化通知索引**：
> V2 中 `idx_notifications_is_read` 单独对 `is_read` 建立索引，实际查询几乎总是配合 `user_id`
> 使用（如"获取某用户的未读通知"），单独的布尔字段索引选择性极差。已改为复合索引
> `(user_id, is_read)`。

---

## 🔒 安全设计备注

1. **密码存储**：使用 bcrypt 哈希，永远不存储明文密码
2. **AI Agent SQL 访问**：Agent 通过 SQL Tool 查询数据库时，**必须使用只读数据库连接**（`READ ONLY` 事务或只读副本），
   禁止 Agent 直接执行写操作；所有写操作必须通过应用 API 层执行，确保业务规则和权限检查
3. **审计日志**：通过 `audit_logs` 表记录关键操作，不可修改、不可删除
4. **软删除**：用户通过 `is_active` 标记禁用，不做物理删除，保留数据关联完整性
5. **数据完整性**：关键数值字段增加 CHECK 约束（库存 ≥ 0、数量 > 0 等），防止无效数据写入

