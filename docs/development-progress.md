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

---

## 下一步任务（仅一个功能）

### 功能：后端认证模块

- [ ] 实现 `POST /api/auth/login`（用户名 + 密码 → JWT Token）
- [ ] 实现 JWT 中间件（解析 Token、注入当前用户信息）
- [ ] 实现角色权限装饰器（`@require_role("admin")`）
- [ ] 实现 `GET /api/auth/me`（获取当前登录用户信息）
