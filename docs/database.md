
# 数据库设计文档

## 📊 数据库架构

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
| role | VARCHAR(16) | NOT NULL | 角色：admin / dispatcher / worker |
| warehouse_id | INTEGER | FK → warehouses.id | 所属仓库（调度员和工人必填，管理员为空） |
| avatar | VARCHAR(512) | | 头像URL/路径 |
| description | TEXT | | 用户描述/备注 |
| is_active | BOOLEAN | NOT NULL, DEFAULT true | 账户是否激活（软禁用） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 最后修改时间 |

**关键约束**：
- `role` 通过 CHECK 约束限制为 `'admin'`、`'dispatcher'`、`'worker'`
- `CHECK (role = 'admin' OR warehouse_id IS NOT NULL)` — 调度员和工人必须绑定仓库
- 管理员账号不可被禁用（由业务逻辑层保证）

**设计说明**：
原方案单独设置 `workers` 表，但 workers 仅额外存储 `warehouse_id`，而调度员也需要绑定仓库（"查看本仓库订单"）。
合并后减少一张表和大量 JOIN 查询，调度员和工人统一通过 `warehouse_id` 确定所属仓库。

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

---

### **3️⃣ warehouses（仓库表）**

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
- 分离 address（文本）和坐标（数值），便于地图展示与距离计算
- 经纬度允许为空（地址解析可能失败）

---

### **4️⃣ skill_tag_definitions（技能定义表）**
系统中定义的所有可用技能（统一技能字典）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 技能标签ID |
| name | VARCHAR(64) | UNIQUE, NOT NULL | 技能名称（如"搬运"、"分拣"、"装箱"） |
| description | TEXT | | 技能描述 |

---

### **5️⃣ user_skills（用户技能表）**
多对多：工人拥有的技能

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| user_id | INTEGER | FK → users.id, NOT NULL | 用户ID（role=worker） |
| skill_tag_id | INTEGER | FK → skill_tag_definitions.id, NOT NULL | 技能ID |

**约束**：`PRIMARY KEY (user_id, skill_tag_id)`

---

### **6️⃣ products（产品表）**
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

### **7️⃣ product_required_skills（产品所需技能表）**
多对多：处理某产品需要的技能

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| product_id | INTEGER | FK → products.id, NOT NULL | 产品ID |
| skill_tag_id | INTEGER | FK → skill_tag_definitions.id, NOT NULL | 需要的技能ID |

**约束**：`PRIMARY KEY (product_id, skill_tag_id)`

---

### **8️⃣ inventory（库存表）**
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

**关键业务逻辑**：
```
总库存 = qty_available + qty_reserved
可分配 = qty_available（不能超过此数）
库存预警 = qty_available < qty_threshold
```

---

### **9️⃣ orders（订单表）**
业务订单主表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 订单ID |
| order_no | VARCHAR(32) | UNIQUE, NOT NULL | 订单号（业务编码） |
| customer_id | INTEGER | FK → customers.id, NOT NULL | 客户ID |
| warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 发货仓库 |
| dispatcher_id | INTEGER | FK → users.id | 负责调度员（可为空，管理员创建时可不指定） |
| description | TEXT | | 订单备注 |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | pending / in_progress / completed / cancelled |
| priority | VARCHAR(8) | NOT NULL, DEFAULT 'medium' | high / medium / low |
| total_amount | DECIMAL(12,2) | NOT NULL, DEFAULT 0 | 订单总金额 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |
| completed_at | TIMESTAMP | | 完成时间 |

**注意事项**：
- `total_amount` 应在新增/修改 order_items 时同步更新（通过应用层），避免与明细不一致
- `status` 通过 CHECK 约束限制为 `'pending'`、`'in_progress'`、`'completed'`、`'cancelled'`

---

### **🔟 order_items（订单明细表）**
订单包含的产品明细（一对多）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 明细ID |
| order_id | INTEGER | FK → orders.id, NOT NULL | 所属订单 |
| product_id | INTEGER | FK → products.id, NOT NULL | 产品ID |
| qty | INTEGER | NOT NULL, CHECK (qty > 0) | 数量 |
| unit_price | DECIMAL(10,2) | NOT NULL, CHECK (unit_price >= 0) | 单价 |

**计算**：`line_amount = qty × unit_price`

---

### **1️⃣1️⃣ work_orders（工作订单表）**
分配给工人的具体任务

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 工作单ID |
| order_id | INTEGER | FK → orders.id, NOT NULL | 关联的业务订单 |
| worker_id | INTEGER | FK → users.id, NOT NULL | 分配的工人（应用层校验 role=worker） |
| dispatcher_id | INTEGER | FK → users.id, NOT NULL | 调度员（谁分配的） |
| warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 操作的仓库 |
| task_type | VARCHAR(16) | NOT NULL | picking / staging / shipping |
| status | VARCHAR(16) | NOT NULL, DEFAULT 'pending' | pending / in_progress / completed / cancelled |
| priority | VARCHAR(8) | NOT NULL, DEFAULT 'medium' | high / medium / low |
| deadline | TIMESTAMP | | 截止时间（超过此时间未完成触发告警） |
| description | TEXT | | 任务描述 |
| source | VARCHAR(8) | NOT NULL, DEFAULT 'manual' | manual（人工）/ agent（AI 创建） |
| agent_reason | TEXT | | AI 创建原因说明 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |
| assigned_at | TIMESTAMP | | 分配时间 |
| started_at | TIMESTAMP | | 开始执行时间 |
| completed_at | TIMESTAMP | | 完成时间 |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 更新时间 |

**设计说明**：
- `task_type` 通过 CHECK 约束限制为 `'picking'`、`'staging'`、`'shipping'`
- `status` 通过 CHECK 约束限制为 `'pending'`、`'in_progress'`、`'completed'`、`'cancelled'`
- `deadline` 用于超时告警检测：定时任务扫描 `deadline < NOW() AND status IN ('pending', 'in_progress')` 的工单

---

### **1️⃣2️⃣ work_order_notes（工作单备注表）**
工人提交的完工备注（一个工单可有多条）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 备注ID |
| work_order_id | INTEGER | FK → work_orders.id, NOT NULL | 所属工作单 |
| note_type | VARCHAR(16) | NOT NULL | normal / damaged / qty_mismatch / other |
| content | TEXT | NOT NULL | 备注内容（详细描述） |
| created_by | INTEGER | FK → users.id, NOT NULL | 创建人（工人/调度员/管理员） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |

---

### **1️⃣3️⃣ transfer_orders（调拨单表）**
仓库间的产品调拨

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 调拨单ID |
| product_id | INTEGER | FK → products.id, NOT NULL | 调拨的产品 |
| from_warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 源仓库 |
| to_warehouse_id | INTEGER | FK → warehouses.id, NOT NULL | 目标仓库 |
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

**约束**：`CHECK (from_warehouse_id != to_warehouse_id)` — 源仓库与目标仓库不能相同

---

### **1️⃣4️⃣ notifications（通知表）**
系统消息推送/提醒

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 通知ID |
| user_id | INTEGER | FK → users.id, NOT NULL | 接收用户ID |
| type | VARCHAR(32) | NOT NULL | 通知类型（见下方枚举） |
| title | VARCHAR(256) | NOT NULL | 通知标题 |
| body | TEXT | | 通知内容 |
| related_id | INTEGER | | 关联资源 ID |
| related_type | VARCHAR(32) | | 关联资源类型（work_order / order / transfer_order / inventory） |
| is_read | BOOLEAN | NOT NULL, DEFAULT false | 是否已读 |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 创建时间 |

**通知类型枚举**：

| type 值 | 说明 |
|---------|------|
| work_order_assigned | 任务分配通知（→ 工人） |
| work_order_completed | 任务完成通知（→ 调度员） |
| work_order_timeout | 工单超时未完成告警（→ 调度员 + 管理员） |
| inventory_low | 库存低于阈值预警（→ 调度员 + 管理员） |
| transfer_requested | 调拨申请通知（→ 管理员） |
| transfer_approved | 调拨审批通过通知（→ 申请人） |
| transfer_rejected | 调拨审批驳回通知（→ 申请人） |
| order_completed | 订单完成通知 |

---

### **1️⃣5️⃣ reports（报表表）**
手动触发生成的效率分析报表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | SERIAL | PK | 报表ID |
| generated_by | INTEGER | FK → users.id, NOT NULL | 生成人 |
| target_user_id | INTEGER | FK → users.id | 目标人员（查看某人员的报表时填写） |
| period_start | DATE | NOT NULL | 统计周期开始日期 |
| period_end | DATE | NOT NULL, CHECK (period_end >= period_start) | 统计周期结束日期 |
| stats_json | JSONB | | 统计数据（结构化 JSON） |
| content | TEXT | | 报表内容（Markdown 或 HTML） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | 生成时间 |

---

## 工人状态派生

工人状态不直接存储，通过查询 work_orders 实时派生：

```sql
SELECT
  u.id,
  CASE
    WHEN EXISTS (
      SELECT 1 FROM work_orders wo
      WHERE wo.worker_id = u.id AND wo.status = 'in_progress'
    ) THEN 'busy'          -- 有正在执行的工单 → 忙碌
    WHEN EXISTS (
      SELECT 1 FROM work_orders wo
      WHERE wo.worker_id = u.id AND wo.status = 'pending'
    ) THEN 'assigned'      -- 有待开始的工单 → 已分配
    ELSE 'idle'            -- 无未完成工单 → 空闲
  END AS current_status
FROM users u
WHERE u.role = 'worker' AND u.id = ?;
```

---

## 🔗 关键关系图

```
users (1) ──── (N) orders (dispatcher_id)
  │   ├──── (N) work_orders (worker_id / dispatcher_id)
  │   ├──── (N) notifications
  │   ├──── (N) reports (generated_by / target_user_id)
  │   ├──── (M:N) skill_tag_definitions (via user_skills)
  │   └──── (1) warehouses (warehouse_id)
  │
customers (1) ──── (N) orders

warehouses (1) ──── (N) users (dispatcher / worker)
            ├──── (N) orders
            ├──── (N) inventory
            └──── (N) work_orders

orders (1) ──── (N) order_items
         └──── (N) work_orders

products (M) ──── (M) skill_tag_definitions (via product_required_skills)
          ├──── (N) order_items
          └──── (N) inventory

work_orders (1) ──── (N) work_order_notes

transfer_orders (N) ──── (1) warehouses (from / to)
                 └──── (1) products
```

---

## 📝 索引建议

```sql
-- === 查询性能索引 ===
CREATE INDEX idx_users_warehouse_id ON users(warehouse_id);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_work_orders_worker_id ON work_orders(worker_id);
CREATE INDEX idx_work_orders_order_id ON work_orders(order_id);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_work_orders_worker_status ON work_orders(worker_id, status);
CREATE INDEX idx_work_orders_deadline ON work_orders(deadline) WHERE status IN ('pending', 'in_progress');
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_warehouse_id ON orders(warehouse_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_notifications_user_read ON notifications(user_id, is_read);
CREATE INDEX idx_work_order_notes_work_order_id ON work_order_notes(work_order_id);
CREATE INDEX idx_transfer_orders_status ON transfer_orders(status);

-- === 唯一约束 ===
CREATE UNIQUE INDEX idx_users_username ON users(username);
CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX idx_order_no ON orders(order_no);
CREATE UNIQUE INDEX idx_product_sku ON products(sku);
CREATE UNIQUE INDEX idx_inventory_warehouse_product ON inventory(warehouse_id, product_id);
CREATE UNIQUE INDEX idx_skill_tag_name ON skill_tag_definitions(name);
```

---

## 🔒 安全设计备注

1. **密码存储**：使用 bcrypt 哈希，永远不存储明文密码
2. **AI Agent SQL 访问**：Agent 通过 SQL Tool 查询数据库时，**必须使用只读数据库连接**，
   禁止 Agent 直接执行写操作；所有写操作必须通过应用 API 层执行，确保业务规则和权限检查
3. **软删除**：用户通过 `is_active` 标记禁用，不做物理删除，保留数据关联完整性
4. **数据完整性**：关键数值字段增加 CHECK 约束（库存 ≥ 0、数量 > 0 等），防止无效数据写入

