# API 文档

后端使用 FastAPI，自动生成 OpenAPI 文档。

## 在线文档地址

启动后端后可访问：

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## 当前基础接口

### `GET /`
- 用途：服务信息
- 响应示例：

```json
{
  "service": "wms-dispatch-backend",
  "docs": "/docs"
}
```

### `GET /api/health`
- 用途：健康检查
- 响应示例：

```json
{
  "status": "ok"
}
```
