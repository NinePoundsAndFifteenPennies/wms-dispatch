# 第一步开发计划

> 本文档描述 WMS Dispatch 项目从零到可运行原型的第一阶段开发计划。
> 目标：完成核心后端骨架 + 基础前端页面，实现最小可用系统。

---

## 阶段目标

在第一阶段结束时，系统应具备以下能力：

1. 管理员可以登录系统，管理用户、仓库、商品基础数据
2. 管理员可以创建订单并查看订单列表
3. 调度员可以登录并查看本仓库的订单
4. 工人可以登录并查看分配给自己的工单
5. 基本的权限隔离（三种角色看到不同的页面）

**不包含**：AI Agent 功能、调拨流程、通知推送、效率报告（留到后续阶段）。

---

## 任务拆解

### Sprint 1：项目基础搭建（约 3 天）

#### 1.1 后端项目初始化
- [x] FastAPI 项目骨架、统一响应结构与全局异常处理
- [x] API 路由总线与健康检查接口

#### 1.2 数据库迁移
- [x] Alembic 初始化
- [x] 核心业务表迁移脚本（含约束与索引）

#### 1.3 前端项目初始化
- [x] Vue 3 + Vite + Element Plus + Pinia + Vue Router 初始化

---

### Sprint 2：认证与用户管理（约 3 天）

#### 2.1 后端认证模块
- [x] 实现 `POST /api/auth/login`（用户名 + 密码 → JWT Token）
- [x] 实现 JWT 中间件（解析 Token、注入当前用户信息）
- [x] 实现角色权限装饰器（`@require_role("admin")`）
- [x] 实现 `GET /api/auth/me`（获取当前登录用户信息）

#### 2.2 用户管理 API（管理员）
- [x] `GET /api/admin/users` — 用户列表（分页、搜索）
- [x] `POST /api/admin/users` — 创建用户
- [x] `PUT /api/admin/users/{id}` — 编辑用户
- [x] `PATCH /api/admin/users/{id}/status` — 启用/禁用用户
- [x] 业务规则：管理员账号不可被禁用

#### 2.3 前端认证页面
- [x] 登录页（表单验证、错误提示、Token 存储）
- [x] 路由守卫（未登录跳转登录页、按角色限制路由）
- [x] 路由守卫补充：Token 失效/无效、用户禁用态处理
- [x] 用户管理页面（列表、新增弹窗、编辑弹窗、状态切换，演示数据不落库）
- [x] 登录单入口 + 按角色自动跳转默认页
- [x] 主页面系统状态实时检测（在线/离线）与视觉统一优化

---

### Sprint 3：基础数据管理（约 3 天）

#### 3.1 仓库管理
- [ ] `CRUD /api/admin/warehouses` — 仓库增删改查
- [ ] 前端仓库管理页面（表格 + 表单弹窗）
- [ ] 集成 Nominatim 地理编码（地址 → 经纬度）

#### 3.3 商品管理
- [ ] `CRUD /api/admin/products` — 商品增删改查
- [ ] 商品关联所需技能（多选）
- [ ] 前端商品管理页面

#### 3.4 客户管理
- [ ] `CRUD /api/admin/customers` — 客户增删改查
- [ ] 前端客户管理页面

#### 3.5 人员仓库与技能绑定
- [ ] 创建用户时若角色为 dispatcher 或 worker，需指定所属仓库（数据库 CHECK 约束强制）
- [ ] 工人角色关联技能标签
- [ ] 前端用户编辑页面中嵌入仓库选择和技能标签选择

---

### Sprint 4：订单与工单核心流程（约 4 天）

#### 4.1 库存管理
- [ ] `GET /api/admin/inventory` — 按仓库查看库存
- [ ] `PATCH /api/admin/inventory/{id}` — 盘点修正库存
- [ ] 前端库存管理页面（按仓库筛选、库存修改弹窗）

#### 4.2 订单管理
- [ ] `POST /api/admin/orders` — 创建订单（含明细）
- [ ] `GET /api/admin/orders` — 订单列表（分页、筛选）
- [ ] `GET /api/admin/orders/{id}` — 订单详情（含明细和关联工单）
- [ ] 创建订单时自动预留库存（`qty_available → qty_reserved`）
- [ ] 前端订单管理页面

#### 4.3 调度员 — 订单看板
- [ ] `GET /api/dispatcher/orders` — 本仓库订单列表
- [ ] 前端调度员订单看板页面

#### 4.4 手动工单创建
- [ ] `POST /api/dispatcher/work-orders` — 创建工单（指定工人、任务类型）
- [ ] `GET /api/dispatcher/work-orders` — 工单看板
- [ ] 前端工单创建表单 + 工单看板页面

#### 4.5 工人 — 工单操作
- [ ] `GET /api/worker/work-orders` — 我的工单列表
- [ ] `PATCH /api/worker/work-orders/{id}/start` — 开始执行
- [ ] `PATCH /api/worker/work-orders/{id}/complete` — 完成确认
- [ ] `POST /api/worker/work-orders/{id}/notes` — 提交完工备注
- [ ] 前端工人工单页面

---

### Sprint 5：集成与验收（约 2 天）

- [ ] 端到端流程联调：创建订单 → 创建工单 → 工人执行 → 完成
- [ ] API 错误处理与边界情况测试
- [ ] 基础 UI 走查与修复
- [ ] 编写 API 文档（利用 FastAPI 自动生成的 Swagger UI）

---

## 技术约定

### 后端
- **框架**：FastAPI（异步）
- **ORM**：SQLAlchemy 2.0（声明式映射 + 异步会话）
- **迁移**：Alembic（自动检测模型变更）
- **认证**：JWT（`python-jose[cryptography]` + bcrypt）
- **校验**：Pydantic V2（请求/响应 Schema）
- **项目结构**：按业务模块划分（`modules/admin`、`modules/dispatcher`、`modules/worker`）

### 前端
- **框架**：Vue 3 Composition API
- **路由**：Vue Router 4
- **状态**：Pinia
- **UI 库**：Element Plus（推荐）
- **HTTP**：Axios
- **构建**：Vite

### API 规范
- RESTful 风格
- 统一响应格式：`{ "code": 200, "message": "ok", "data": {...} }`
- 分页参数：`?page=1&page_size=20`
- 认证方式：`Authorization: Bearer <token>`

---

## 风险与依赖

| 风险 | 影响 | 应对 |
|------|------|------|
| Nominatim 地理编码限流 | 仓库创建时无法获取经纬度 | 允许经纬度为空，后台重试；或预留手动输入 |
| 前端 UI 库选型变更 | 已完成页面需重写 | 第一阶段尽早确定 UI 库 |
| 库存并发更新冲突 | 超卖或库存不一致 | 使用数据库行级锁或乐观锁（version 字段） |

---

## 后续阶段预告

| 阶段 | 核心内容 |
|------|----------|
| 第二阶段 | AI 工单调度 Agent + 跨仓调拨 Agent |
| 第三阶段 | 通知推送（WebSocket）+ 告警检测定时任务 |
| 第四阶段 | 效率报告生成 + 地图可视化 |
| 第五阶段 | 性能优化 + 部署方案 + 生产环境安全加固 |
