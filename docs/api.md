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
| page_size | int | 10 | 每页条数，1~100 之间 |
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

### 批量禁用用户

批量将用户设为禁用状态（软禁用，不删除数据）。

```http
POST /api/admin/users/batch-disable
```

**请求体 (JSON):**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ids | int[] | 是 | 需要禁用的用户 ID 列表 |

**成功响应:** `200 OK`
```json
{
  "disabled": 3
}
```

**说明:**
- 管理员账号不会被批量禁用（后端会自动忽略 `role="admin"` 账号）。

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

### 仓库库存管理（新增）

```http
GET    /api/admin/warehouses/{warehouse_id}/inventory
PATCH  /api/admin/warehouses/{warehouse_id}/inventory/{inventory_id}/stocktake
POST   /api/admin/warehouses/{warehouse_id}/inventory/inbound
```

#### 1) 获取仓库库存详情

```http
GET /api/admin/warehouses/{warehouse_id}/inventory?page=1&page_size=10&search=关键词
```

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 当前页码，最小为1 |
| page_size | int | 10 | 每页条数，1~100 之间 |
| search | string | - | 按商品名称 / SKU / 类别模糊搜索 |

**成功响应:** `200 OK`
```json
{
  "warehouse": {
    "id": 1,
    "name": "北京中心周转仓",
    "address": "北京市朝阳区...",
    "cover_image": "/resources/warehouses/w1.png",
    "description": "华北区域主仓",
    "is_active": true
  },
  "items": [
    {
      "id": 21,
      "product_id": 8,
      "sku": "SKU-10086",
      "product_name": "标准纸箱",
      "category": "包装物料",
      "product_cover_image": "/resources/products/p8.png",
      "product_is_active": true,
      "qty_on_hand": 120,
      "qty_reserved": 10,
      "qty_locked": 5,
      "qty_threshold": 30,
      "qty_available": 105
    }
  ],
  "total": 1
}
```

#### 2) 盘点修正库存

```http
PATCH /api/admin/warehouses/{warehouse_id}/inventory/{inventory_id}/stocktake
```

**请求体 (JSON):**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| qty_on_hand | int | 否 | 修正后的现存量（>= 0） |
| qty_threshold | int | 否 | 修正后的库存阈值（>= 0） |
| reason | string | 否 | 修正原因，最长 500 字 |

**说明：**
- `qty_on_hand` 与 `qty_threshold` 至少传一个。
- 当传入 `qty_on_hand` 时，后端会校验：`qty_on_hand >= qty_reserved + qty_locked`。
- 上述校验等价于确保修正后 `qty_available = qty_on_hand - qty_reserved - qty_locked` 不为负。
- `qty_available` 是数据库生成列（`GENERATED ALWAYS AS (qty_on_hand - qty_reserved - qty_locked) STORED`），会随现存量自动重算，接口不会也不能直接写入该字段。
- 禁用仓库与下架商品不允许盘点修正。
- 修正会写入 `stocktakes` 与 `inventory_movements`。

#### 3) 进货入库

```http
POST /api/admin/warehouses/{warehouse_id}/inventory/inbound
```

**请求体 (JSON):**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| product_id | int | 是 | 进货商品 ID |
| qty | int | 是 | 进货数量（> 0） |
| reason | string | 否 | 可选说明，最长 500 字 |

**说明：**
- 若仓库中不存在该商品库存记录，系统会自动创建一条库存记录后再累加入库数量。
- 入库会写入 `stocktakes` 与 `inventory_movements`，用于后续审计与追踪。
- 禁用仓库与下架商品不允许进货。

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

---

### 订单管理（新增）

```http
GET    /api/admin/orders
GET    /api/admin/orders/{order_id}
POST   /api/admin/orders
GET    /api/admin/orders/export
GET    /api/admin/orders/{order_id}/export
```

#### 1) 订单列表

```http
GET /api/admin/orders?page=1&page_size=10&search=关键词&status=in_progress&start_date=2026-03-01&end_date=2026-03-19
```

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 当前页，最小 1 |
| page_size | int | 10 | 每页条数，1~100 |
| search | string | - | 订单号/客户名称模糊搜索 |
| status | string | - | `pending_acceptance \| in_progress \| completed \| cancelled` |
| start_date | string(date) | - | 创建时间起始日期 |
| end_date | string(date) | - | 创建时间结束日期 |

#### 2) 创建订单

```http
POST /api/admin/orders
```

**请求体 (JSON)：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| customer_id | int | 是 | 客户 ID（必须为有效且激活客户） |
| priority | string | 否 | `high \| medium \| low`，默认 `medium` |
| description | string | 否 | 备注 |
| items | array | 是 | 明细数组，至少 1 条 |

`items[]` 字段：
- `product_id`：产品 ID（必须存在且 `is_active=true`）
- `qty`：数量，> 0
- `unit_price`：单价（分），>= 0

#### 3) 订单导出（按当前筛选结果）

```http
GET /api/admin/orders/export?export_format=csv|markdown|pdf
```

**说明：**
- `csv`：`text/csv; charset=utf-8`，内容已带 UTF-8 BOM，Excel 打开中文不乱码。
- `markdown`：`text/markdown; charset=utf-8`。
- `pdf`：`application/pdf`，响应 `data.content_base64` 为 PDF 的 base64 内容。

#### 4) 订单详情 PDF 导出

```http
GET /api/admin/orders/{order_id}/export?export_format=pdf
```

**说明：**
- 返回 `application/pdf`，响应 `data.content_base64` 为订单详情 PDF 的 base64 内容。
