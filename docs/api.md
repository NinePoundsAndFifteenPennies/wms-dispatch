# API 接口文档

后端使用 FastAPI 并在 `/docs` 自动生成了完整的 OpenAPI Swagger 页面。本文档补充记录核心业务 API 的传参与格式规范。

## 统一响应结构

除下载等特殊接口外，系统响应统一约束如下：

```json
{
  "code": 200,
  "message": "ok",
  "data": {}
}
```

- 成功响应：`code = HTTP 状态码`；`message = "ok"`
- 失败响应：`code = HTTP 状态码`；`message = 错误描述`；`data` 可能为 `null` 或校验错误明细

---

## 认证接口 (Auth)

### 登录签发 Token

通过用户名密码验证并获取 JWT。

```http
POST /api/auth/login
```

**请求体 (JSON):**

| 字段 | 类型 | 说明 |
|------|------|------|
| username | string | 登录用户名 |
| password | string | 密码明文 |

**成功响应:** `200 OK`
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@wms.local",
    "role": "admin",
    "warehouse_id": null,
    "is_active": true
  }
}
```

**说明:**
- 失败状态码：`401` 密码错误, `403` 账户被禁用

---

### 获取当前用户信息

提取请求头中的 Token 并解析出登录人员的完整业务信息。

```http
GET /api/auth/me
```

**请求头:** `Authorization: Bearer <token>`

**成功响应:** `200 OK`
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@wms.local",
  "role": "admin",
  "warehouse_id": null,
  "is_active": true
}
```

---

## 管理员模块接口 (Admin)

### 获取用户列表 (带分页与搜索)

获取系统内管理人员、调度员与工人的列表。

```http
GET /api/admin/users
```

**查询参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 当前页码，最小为1 |
| page_size | int | 10 | 页面条数，1~100 之间 |
| search | string | - | 根据用户名或邮箱进行的模糊搜索词 |

**成功响应:** `200 OK`
```json
{
  "items": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@test.com",
      "role": "admin",
      "is_active": true,
      "warehouse_id": null,
      "skill_picking": 0,
      "skill_staging": 0,
      "skill_shipping": 0
    },
    {
      "id": 2,
      "username": "worker_li",
      "email": "li@test.com",
      "role": "worker",
      "is_active": true,
      "warehouse_id": 1,
      "skill_picking": 5,
      "skill_staging": 3,
      "skill_shipping": 1
    }
  ],
  "total": 42
}
```

**字段说明 (items):**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 用户唯一标识 |
| username | string | 用户名 |
| email | string | 邮箱地址 |
| role | string | 用户角色 (admin, dispatcher, worker) |
| is_active | boolean | 当前账户是否允许登录激活 |
| warehouse_id | int | 所属的仓库ID (管理员为 null) |
| skill_picking | int | 拣货技能等级 |
| skill_staging | int | 备货技能等级 |
| skill_shipping| int | 发货技能等级 |

---

### 创建管理人员

新建系统用户。需要符合严格的字段与业务规则校验。

```http
POST /api/admin/users
```

**请求体 (JSON):**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名（全局唯一） |
| email | string(email)| 是 | 邮箱地址（格式严格校验） |
| password | string | 是 | 密码明文 |
| role | string | 是 | 枚举值：admin, dispatcher, worker |
| warehouse_id | int | 否 | 非管理员此项必填 |
| skill_picking | int | 否 | 拣货能力点，默认 0 |
| skill_staging | int | 否 | 备货能力点，默认 0 |
| skill_shipping | int | 否 | 发货能力点，默认 0 |

**成功响应:** `201 Created`
```json
{
  "id": 15,
  "username": "new_worker",
  "email": "new@wms.local",
  "role": "worker",
  "is_active": true,
  "warehouse_id": 2,
  "skill_picking": 2,
  "skill_staging": 0,
  "skill_shipping": 0
}
```

**说明:**
- 邮箱或用户名重复将返回 `400 Bad Request`。
- 非管理员如果 `warehouse_id` 缺失将抛出报错。

---

### 更新用户信息

修改指定用户的属性值，支持局部更新（未传字段将保持原样）。

```http
PUT /api/admin/users/{id}
```

**路径参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| id | int | 要更新的用户ID |

**请求体 (JSON):** 
*(全字段为可选，传什么更新什么)*

| 字段 | 类型 | 说明 |
|------|------|------|
| username | string | 新用户名 |
| email | string(email)| 新邮箱地址 |
| role | string | 角色修改 |
| warehouse_id | int | 仓库归属修改 |
| skill_picking | int | 拣货能力点修改 |
| skill_staging | int | 备货能力点修改 |
| skill_shipping | int | 发货能力点修改 |

**成功响应:** `200 OK`
*(返回更新后的 User 对象，结构同 Create 响应一致)*

---

### 更改用户启停状态

开启或禁用某账号（禁用态下的用户将无法登录系统或执行动作）。

```http
PATCH /api/admin/users/{id}/status
```

**路径参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| id | int | 要封禁或启用的用户ID |

**请求体 (JSON):**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| is_active | boolean | 是 | true 为启用，false 为禁用 |

**成功响应:** `200 OK`
*(返回更新后的 User 对象)*

**说明:**
- **业务规则:** 如果尝试将 `role="admin"` 的人状态设置为 `false`，接口将拦截并返回 `400 Admin account cannot be disabled`。

---

### 获取全部仓储列表

获取用于选项下拉等用途的基础地理仓储网点信息。

```http
GET /api/admin/warehouses
```

**成功响应:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "北京中心周转仓"
  },
  {
    "id": 2,
    "name": "上海分拨调配站"
  }
]
```

**字段说明:**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 仓库唯一编号 |
| name | string | 仓库对外显示名称 |

---

### 客户管理（新增）

```http
GET    /api/admin/customers
POST   /api/admin/customers
PUT    /api/admin/customers/{customer_id}
DELETE /api/admin/customers/{customer_id}
POST   /api/admin/customers/batch-delete
PATCH  /api/admin/customers/{customer_id}/status
```

**说明：**
- `PATCH /status` 请求体：`{"is_active": true|false}`。
- 客户列表返回字段含 `is_active`，前端可展示停用记录并进行恢复。

---

### 产品管理（新增）

```http
GET    /api/admin/products
POST   /api/admin/products
PUT    /api/admin/products/{product_id}
DELETE /api/admin/products/{product_id}
POST   /api/admin/products/batch-delete
PATCH  /api/admin/products/{product_id}/status
POST   /api/admin/products/{product_id}/image
DELETE /api/admin/products/{product_id}/image
```

**图片接口说明：**
- 上传图片：`POST /image`，`multipart/form-data`，字段名为 `image`。
- 移除图片：`DELETE /image`，会将数据库 `cover_image` 清空，并删除服务器文件。
- 更换图片：重复调用上传接口即可，系统会替换 URL 并清理旧图文件。

