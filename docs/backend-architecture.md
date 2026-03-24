# 后端架构说明 (Backend Architecture)

本项目后端采用基于 FastAPI 和纯异步 SQLAlchemy 2.0 的 **3 层架构**。这一明确的主流设计范式将不同的关注点解耦，确保系统业务逻辑清晰且十分利于长线维护：

## 全局结构划分

- `main.py`：应用入口，注入了全局异常拦截中间件与跨域/JWT 中间件。
- `api/router.py`：全局路由注册中心，挂载所有 `modules` 下的子路由。
- `models/`：全局数据表基类定义，存放了所有 ORM 关联。
- `modules/`：按业务领域（如 `admin`, `auth`, `worker` 等）划分子系统。

其中，复杂领域允许在自身目录下继续做“按业务域分组”的服务拆分。例如 `admin` 已将超长业务服务拆到 `modules/admin/service/` 包内，并通过 `modules/admin/services.py` 保持统一兼容导出。

---

## 核心三层范式

对于系统内的各个领域模块下的请求处理，我们严格划分为以下三块架构。**任何新 API 开发必须遵循这一模式链**：

### 1. Router 层 (路由层)
- **定位**：接受 HTTP 请求、调用处理服务、包裹发还响应。
- **所在文件**：`modules/{domain}/router.py`
- **职责限制**：
  - 定义 API 路径树。
  - **只允许**调用 Service 实例的方法和通过依赖拿到当前上下文。
  - **严禁**在此层写任何包含 `select()`, `commit()` 或是带业务逻辑 `if role == ...` 的处理。它必须轻如鸿毛。

### 2. Service 层 (业务服务层)
- **定位**：系统的核心大脑，全权处理此业务的具体工作。
- **所在文件**：
  - 简单模块：`modules/{domain}/services.py`
  - 复杂模块：`modules/{domain}/service/*.py`（按业务域拆分），并在 `modules/{domain}/services.py` 保留统一入口导出，避免影响 Router/Dependencies 的既有引用
- **职责**：
  - 处理全部的内部应用逻辑验证（如拦截非法权限，排查是否存在重名数据）。
  - 连接数据库依赖，执行完整的 SQLAlchemy 异步 ORM 查询及保存，并手动包裹 try/catch 的 DB 事务。
  - 返回从数据库拿到并组装好的模型实体列表/单例给外层。

#### Admin 模块拆分示例（当前已落地）

- `modules/admin/service/base.py`：基础能力（`AsyncSession` 挂载、公共常量与通用函数）
- `modules/admin/service/work_orders.py`：工单管理
- `modules/admin/service/dashboard.py`：看板聚合统计
- `modules/admin/service/users.py`：用户管理
- `modules/admin/service/warehouses.py`：仓库与库存流转
- `modules/admin/service/customers.py`：客户管理
- `modules/admin/service/orders.py`：订单管理与导出
- `modules/admin/service/products.py`：商品管理
- `modules/admin/service/__init__.py`：组合 `AdminService`（Mixin 聚合）
- `modules/admin/services.py`：兼容导出层（对外继续暴露 `AdminService`）

### 3. Schema 层 (传输对象 DTO/BO)
- **定位**：结构载体转换定义与进出防腐。
- **所在文件**：`modules/{domain}/schemas.py`
- **职责**：
  - 基于 Pydantic 构建纯粹的结构化类。
  - 控制参数接收：如 `UserCreate`, 并可以灵活配置内建校验器（例如：`email: EmailStr` 限定合规邮箱）。
  - 控制输出映射：限制从 Service 模型泄露额外不被允许的字段密码字典等到网络层（比如定义分页响应结构 `UserListResponse`）。

---

## 额外设计约定
- **依赖注入挂载**：每个业务模块可有专属的 `dependencies.py`，用于给 Router 轻松生成相应的 Service 实例，且它通过挂接 SQLAlchemy AsyncSession 保障了每个独立网络请求只会拿到同一份活跃会话，防止了泄漏。
- **静态资源服务**：应用在 `main.py` 中挂载 `/resources` 静态目录，图片等上传资源统一落在项目根 `resources/` 下按业务子目录管理。
- **软删除展示约定**：客户与产品采用 `is_active` 状态开关模型，列表默认返回全部记录（包含停用项），由前端使用状态开关执行启停。

---

## 时间处理约定（新增）

为彻底消除时区歧义，后端统一采用“北京时间语义 + 秒级精度”策略：

1. 业务时间统一为 `Asia/Shanghai`。
2. SQL 写时间推荐使用：`(NOW() AT TIME ZONE 'Asia/Shanghai')::timestamp(0)`。
3. Python 层如需生成业务时间，必须显式使用 `ZoneInfo('Asia/Shanghai')`，并与数据库字段语义保持一致。
4. `TIMESTAMP WITHOUT TIME ZONE` 字段按“北京时间本地时间”理解，禁止混入 UTC 业务时间写入。
5. JWT `exp` 使用 UTC 是认证标准例外，不视为业务时间违规。
