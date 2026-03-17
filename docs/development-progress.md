# 开发进展记录（单功能推进范式）

> 范式说明：每次只推进一个功能块，记录分为两段：
> 1) 已完成任务（仅记录已落地且可验证项，同时注意从development-plan.md中移除已经完成的部分）
> 2) 下一步任务（以模块的形式呈现）

---

## 已完成任务

- 完成 Alembic 第 1 批迁移：创建核心表 `warehouses`、`users`、`customers`、`products`、`inventory`
- 完成 Alembic 第 2 批迁移：创建其余业务表 `inventory_movements`、`orders`、`order_items`、`order_stages`、`work_orders`、`work_order_notes`、`transfer_orders`、`inbound_records`、`notifications`、`reports`
- 按文档增加约束：数量非负/大于零、状态值约束、角色约束、仓库差异约束、周期日期约束、联合唯一约束等
- 增加技能查询索引：`idx_users_skills`（`skill_picking`, `skill_staging`, `skill_shipping`）
- 完成数据库初始化验证：当前库已存在 16 张表（含 `alembic_version`）
- 完成后端认证主链路：
  - `POST /api/auth/login`（用户名密码登录签发 JWT）
  - JWT 中间件（解析 Token 并注入 `request.state.current_user`）
  - `@require_role("admin")` 角色权限装饰器
  - `GET /api/auth/me`（返回当前登录用户）
- 完成前端认证与权限控制：
  - 登录页对接真实接口（表单校验、错误提示、loading）
  - Pinia 会话持久化（`token + currentUser`）
  - 路由守卫：未登录拦截、Token 失效处理、用户禁用处理、按角色限制回退
  - 登录后按角色自动分流到默认页（admin/dispatcher/worker）
- 完成管理员用户管理页面（纯前端演示，不落库）：用户列表、新增/编辑弹窗、状态切换
- 完成主页面系统状态可视化：左下角实时探测后端健康状态（在线/离线），离线降频轮询
- 完成登录页与主页面视觉统一优化：图标、信息标签、卡片层次与背景样式统一

---

## 下一步任务（仅一个功能）

### 功能：管理员用户管理 API（落库版）

- [ ] `GET /api/admin/users` — 用户列表（分页、搜索）
- [ ] `POST /api/admin/users` — 创建用户
- [ ] `PUT /api/admin/users/{id}` — 编辑用户
- [ ] `PATCH /api/admin/users/{id}/status` — 启用/禁用用户
- [ ] 业务规则：管理员账号不可被禁用
