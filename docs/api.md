# API 文档

后端使用 FastAPI，自动生成 OpenAPI 文档。

## 在线文档地址

启动后端后可访问：

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## 统一响应结构

除下载等特殊接口外，统一响应结构为：

```json
{
  "code": 200,
  "message": "ok",
  "data": {}
}
```

- 成功响应：`code = HTTP 状态码`，`message = "ok"`（默认）
- 失败响应：`code = HTTP 状态码`，`message = 错误描述`，`data` 可能为 `null` 或校验错误详情

## 当前基础接口

### `GET /`
- 用途：服务信息
- 响应示例：

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "service": "wms-dispatch-backend",
    "docs": "/docs"
  }
}
```

### `GET /api/health`
- 用途：健康检查
- 响应示例：

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "status": "ok"
  }
}
```

## 认证接口

### `POST /api/auth/login`
- 用途：账号密码登录并签发 JWT
- 请求体：

```json
{
  "username": "admin",
  "password": "your-password"
}
```

- 成功响应示例（`200`）：

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "token": "<JWT_TOKEN>",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@wms.local",
      "role": "admin",
      "warehouse_id": null,
      "is_active": true
    }
  }
}
```

- 失败响应示例：
  - 用户名或密码错误（`401`）
  - 用户被禁用（`403`）

```json
{
  "code": 401,
  "message": "Invalid username or password",
  "data": null
}
```

### `GET /api/auth/me`
- 用途：获取当前登录用户信息
- 请求头：

```http
Authorization: Bearer <JWT_TOKEN>
```

- 成功响应示例（`200`）：

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "id": 1,
    "username": "admin",
    "email": "admin@wms.local",
    "role": "admin",
    "warehouse_id": null,
    "is_active": true
  }
}
```

- 失败响应示例：
  - 未登录/Token 无效（`401`）
  - 用户被禁用（`403`）
