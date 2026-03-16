
# 数据库设计文档（动态更新）

## 📊 数据库架构 V2 

---
## 资源设计：
所有图片等资源都放在根目录resources/下，按类型分子目录：

```resources/
  ├── warehouse_covers/   // 仓库封面图
  ├── product_images/     // 产品图片
  ├── user_avatars/      // 用户头像
  └── other/             // 其他资源,后续自定义
```

### **1️⃣ users（用户表）**
系统中的所有用户（管理员、调度员、工人）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | PK | 用户唯一标识 |
| username | VARCHAR | 登录用户名 |
| password | VARCHAR | 密码（加密存储，如bcrypt） |
| email | VARCHAR | 邮箱地址 |
| role | ENUM | **角色分类**：<br/>• admin（系统管理员）<br/>• dispatcher（调度员）<br/>• worker（仓库工人） |
| avatar | VARCHAR | 头像URL/路径 |
| description | TEXT | 用户描述/备注 |
| is_active | BOOLEAN | 账户是否激活（软删除） |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 最后修改时间 |

**关键点**：角色字段简化为三类，权限通过业务逻辑控制

---

### **2️⃣ customers（客户表）**
订单客户信息

| 字段 | 说明 |
|------|------|
| id | 客户ID |
| name | 客户名称/公司名 |
| contact | 联系方式（电话/邮箱） |
| address | 送货地址 |
| description | 客户备注 |
| created_at | 创建时间 |

**用途**：支持订单生成、地址关联

---

### **3️⃣ warehouses（仓库表）** ⭐ 优化点
从文本location升级为精确坐标定位

| 字段 | 说明 |
|------|------|
| id | 仓库ID |
| name | 仓库名称 |
| address | 仓库地址（文本描述） |
| latitude | 纬度（API定位结果） |
| longitude | 经度（API定位结果） |
| capacity | 仓库容量（最大库存） |
| cover_image | 仓库图片 |
| description | 仓库描述 |
| created_at | 创建时间 |
| updated_at | 更新时间 |

**优化**：
- ✅ 分离address（文本）和坐标（数值）
- ✅ 便于地图展示、距离计算、路线规划
- ✅ 如需历史追踪，可建warehouse_location_history表

---

### **4️⃣ workers（工人表）** ⭐ 设计改进
去掉current_status，通过查询派生

| 字段 | 说明 |
|------|------|
| id | 工人ID |
| user_id | 关联users表 |
| warehouse_id | 所属仓库 |
| description | 工人备注/岗位描述 |
| created_at | 入职时间 |
| updated_at | 更新时间 |

**改进说明**：
```sql
-- 工人状态不直接存，通过查询work_orders派生：

-- 获取工人当前状态
SELECT 
  CASE 
    WHEN COUNT(wo.id) > 0 AND MAX(wo.status) = 'in_progress' THEN 'busy'
    WHEN COUNT(wo.id) > 0 AND MAX(wo.status) = 'pending' THEN 'idle'
    ELSE 'off_duty'  -- 无任务时离职
  END AS current_status
FROM workers w
LEFT JOIN work_orders wo ON w.id = wo.worker_id 
  AND wo.completed_at IS NULL
WHERE w.id = ?
GROUP BY w.id;
```

**优点**：
- ✅ 避免状态不同步问题
- ✅ 状态由work_orders驱动，天然准确
- ✅ 减少update操作

---

### **5️⃣ skill_tag_definitions（技能定义表）**
系统中定义的所有可用技能

| 字段 | 说明 |
|------|------|
| id | 技能标签ID |
| name | 技能名称（如"搬运"、"分拣"、"装箱"） |
| description | 技能描述 |

**示例**：
```
id=1, name="搬运", description="能力搬运较重物品"
id=2, name="分拣", description="按订单快速分拣产品"
id=3, name="装箱打包", description="规范装箱、防损"
```

---

### **6️⃣ worker_skills（工人技能表）**
多对多：工人拥有的技能

| 字段 | 说明 |
|------|------|
| worker_id | 工人ID |
| skill_tag_id | 技能ID |

**示例**：
```
worker_id=5, skill_tag_id=1  // 工人5会搬运
worker_id=5, skill_tag_id=2  // 工人5也会分拣
```

**用途**：
- 匹配工人能力与订单需求
- 任务分配时优先选择技能匹配的工人

---

### **7️⃣ products（产品表）**
产品/SKU主数据

| 字段 | 说明 |
|------|------|
| id | 产品ID |
| sku | SKU编码（唯一） |
| name | 产品名称 |
| category | 产品类别 |
| unit_weight | 单位重量（g） |
| cover_image | 产品图片 |
| description | 产品描述/特殊要求 |
| created_at | 创建时间 |
| updated_at | 更新时间 |

---

### **8️⃣ product_required_skills（产品所需技能表）**
多对多：处理某产品需要的技能

| 字段 | 说明 |
|------|------|
| product_id | 产品ID |
| skill_tag_id | 需要的技能ID |

**示例**：
```
product_id=100, skill_tag_id=3  // 易碎产品需要小心搬运
product_id=100, skill_tag_id=5  // 易碎产品需要特殊包装
```

**用途**：分配work_orders前验证工人是否有所需技能

---

### **9️⃣ inventory（库存表）** 核心运营数据
实时库存管理（频繁更新）

| 字段 | 说明 |
|------|------|
| id | 库存记录ID |
| warehouse_id | 仓库ID |
| product_id | 产品ID |
| qty_available | 可用数量（立即可发） |
| qty_reserved | 已预留数量（已分配待发） |
| qty_threshold | 库存阈值（预警点） |
| updated_at | 最后更新时间 |

**示例**：
```
warehouse=1, product=100
  qty_available=50  (可发50件)
  qty_reserved=20   (已预留20件发货中)
  qty_threshold=10  (库存<10件时预警)
```

**关键业务逻辑**：
```
总库存 = qty_available + qty_reserved
可分配 = qty_available (不能超过此数)
库存预警 = qty_available < qty_threshold
```

---

### **🔟 orders（订单表）** ⭐ 优化版本
业务订单主表

| 字段 | 说明 |
|------|------|
| id | 订单ID |
| order_no | 订单号（业务编码，唯一） |
| customer_id | 客户ID |
| warehouse_id | **发货仓库**（确定谁来处理） |
| dispatcher_id | 调度员ID（users表） |
| description | 订单备注 |
| status | 订单状态（待处理/进行中/已完成/已取消） |
| priority | 优先级（高/中/低） |
| total_amount | **新增**：订单总金额 |
| created_at | 创建时间 |
| updated_at | 更新时间 |
| completed_at | 完成时间 |

**改进**：添加total_amount便于财务统计

---

### **1️⃣1️⃣ order_items（订单明细表）**
订单包含的产品明细（一对多）

| 字段 | 说明 |
|------|------|
| id | 明细ID |
| order_id | 所属订单 |
| product_id | 产品ID |
| qty | 数量 |
| unit_price | 单价 |

**计算**：
```
line_amount = qty × unit_price
```

---

### **1️⃣2️⃣ work_orders（工作订单表）** ⭐ 重点优化
分配给工人的具体任务

| 字段 | 说明 |
|------|------|
| id | 工作单ID |
| order_id | 关联的业务订单 |
| worker_id | 分配的工人ID |
| dispatcher_id | 调度员ID（谁分配的） |
| warehouse_id | 操作的仓库ID |
| task_type | **任务类型**：<br/>• picking（从货架拣货）<br/>• staging（分拣/汇总）<br/>• shipping（装车发货） |
| status | **工作状态**：<br/>• pending（待开始）<br/>• in_progress（进行中）<br/>• completed（已完成）<br/>• cancelled（已取消） |
| priority | 优先级（高/中/低） |
| description | 任务描述 |
| source | **来源**：<br/>• manual（人工创建）<br/>• agent（AI/自动化创建） |
| agent_reason | AI创建原因说明（如"库存充足，自动分配"） |
| assigned_at | 分配时间 |
| started_at | 开始时间 |
| completed_at | 完成时间 |
| updated_at | 更新时间 |

**改进**：
- ✅ 添加started_at区分"分配"和"开始"
- ✅ 去掉completion_note，独立为work_order_notes表
- ✅ status改为明确的四态

---

### **1️⃣3️⃣ work_order_notes（工作单备注表）** ⭐ 新表
替代原来work_orders中的completion_note字段

| 字段 | 说明 |
|------|------|
| id | 备注ID |
| work_order_id | 所属工作单 |
| note_type | **备注类型**：<br/>• normal（正常完成）<br/>• damaged（产品破损）<br/>• qty_mismatch（数量不符）<br/>• other（其他异常） |
| content | 备注内容（详细描述） |
| created_by | 创建人ID（users.id）<br/>• 可以是工人、调度员、管理员 |
| created_at | 创建时间 |

**优点**：
- ✅ 分离关注点（任务状态 vs 完成说明）
- ✅ 支持多条备注（一个work_order可以有多条note）
- ✅ 追踪谁写的备注（审计需要）
- ✅ 灵活的问题记录

**示例**：
```
work_order_id=123, note_type='damaged'
content='左上角凹陷，客户反映易碎品'
created_by=45 (工人45)

work_order_id=123, note_type='other'
content='已协商客户同意原价发货'
created_by=10 (调度员10)
```

---

### **1️⃣4️⃣ transfer_orders（转移单表）**
仓库间的产品转移/调拨

| 字段 | 说明 |
|------|------|
| id | 转移单ID |
| product_id | 转移的产品 |
| from_warehouse_id | 源仓库 |
| to_warehouse_id | 目标仓库 |
| initiating_warehouse_id | **新增**：发起转移的仓库<br/>（可能≠from，用于区分请求方） |
| requested_by | 申请人ID（users.id） |
| approved_by | 批准人ID（users.id） |
| qty | 转移数量 |
| status | 转移状态（待批准/已批准/已执行/已取消） |
| description | 转移原因/说明 |
| agent_reason | AI建议原因<br/>（如"A仓库库存不足，B仓库库存充足"） |
| created_at | 创建时间 |
| updated_at | 更新时间 |
| approved_at | 批准时间 |

**示例**：
```
A仓库库存不足，向B仓库申请转移产品X×100件

from_warehouse_id=2 (B仓库库存)
to_warehouse_id=1   (A仓库缺货)
initiating_warehouse_id=1 (A仓库发起请求)
requested_by=5      (A仓库工作人员)
approved_by=10      (B仓库主管)
agent_reason="A仓库销售订单排队中，库存不足；
              B仓库库存充足，建议转移100件"
```

---

### **1️⃣5️⃣ notifications（通知表）** ⭐ 新增
系统消息推送/提醒

| 字段 | 说明 |
|------|------|
| id | 通知ID |
| user_id | 接收用户ID |
| type | **通知类型**：<br/>• work_order_assigned（任务分配）<br/>• work_order_completed（任务完成）<br/>• inventory_low（库存预警）<br/>• transfer_order_approved（转移批准）<br/>• order_delivered（订单完成）等 |
| title | 通知标题 |
| body | 通知内容 |
| related_id | **关联ID**（哪个资源的通知）<br/>• work_order_id / order_id / transfer_order_id |
| related_type | **关联类型**：<br/>• work_order / order / transfer_order / inventory |
| is_read | 是否已读 |
| created_at | 创建时间 |

**用途**：
- 工人收到新任务提醒
- 调度员收到任务完成通知
- 库存预警通知管理员

---

### **1️⃣6️⃣ reports（报表表）** ⭐ 新增
定期生成的业务报表

| 字段 | 说明 |
|------|------|
| id | 报表ID |
| generated_by | 生成人ID（users.id） |
| period_start | 统计周期开始日期 |
| period_end | 统计周期结束日期 |
| stats_json | **统计数据**（JSON格式）<br/>如：`{"total_orders": 150, "total_amount": 50000, "avg_completion_time": 2.5}` |
| content | 报表内容（markdown或HTML） |
| created_at | 生成时间 |

**示例**：
```json
{
  "total_orders": 150,
  "total_amount": 50000,
  "completed_orders": 145,
  "pending_orders": 5,
  "avg_completion_time_hours": 2.5,
  "top_products": [...],
  "warehouse_performance": {...},
  "worker_efficiency": {...}
}
```

---

## 🔗 关键关系图

```
users (1) ------ (N) workers
  |
  +---- (1) ------- (N) orders (dispatcher_id)
  +---- (1) ------- (N) work_orders (dispatcher_id)
  +---- (1) ------- (N) notifications
  
customers (1) ------ (N) orders

warehouses (1) ------ (N) workers
            +------ (N) orders
            +------ (N) inventory
            +------ (N) work_orders
            
workers (1) ------ (N) work_orders
   |
   +---- (M) ------ (M) skill_tag_definitions (via worker_skills)
   
orders (1) ------ (N) order_items
         +------ (N) work_orders

order_items (N) ------ (1) products
            
products (M) ------ (M) skill_tag_definitions (via product_required_skills)

work_orders (1) ------ (N) work_order_notes

inventory (N) ------ (1) warehouses
         +------ (1) products

transfer_orders (N) ------ (1) warehouses (from_warehouse_id, to_warehouse_id)
                +------ (1) products
```

---


## 📝 索引建议

```sql
-- 频繁查询
CREATE INDEX idx_workers_user_id ON workers(user_id);
CREATE INDEX idx_workers_warehouse_id ON workers(warehouse_id);
CREATE INDEX idx_work_orders_worker_id ON work_orders(worker_id);
CREATE INDEX idx_work_orders_status ON work_orders(status);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_inventory_warehouse_product ON inventory(warehouse_id, product_id);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);

-- 唯一约束
CREATE UNIQUE INDEX idx_order_no ON orders(order_no);
CREATE UNIQUE INDEX idx_product_sku ON products(sku);
CREATE UNIQUE INDEX idx_warehouse_location ON warehouses(latitude, longitude);
```

