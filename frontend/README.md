# WMS Dispatch Frontend

WMS Dispatch 前端基于 Vue 3 + Vite，已完成第一阶段前端初始化：

- 路由：Vue Router 4
- 状态管理：Pinia
- UI 框架：Element Plus
- HTTP：Axios（统一鉴权 Header、统一错误提示）
- 基础布局：侧边栏 + 顶部导航栏 + 内容区

## 环境要求

- Node.js 18+
- npm 9+

## 快速启动

```bash
npm install
npm run dev
```

默认访问地址：`http://localhost:5173`

## 后端联调说明

后端服务运行在 `http://localhost:8000`。

开发环境通过 Vite 代理将 `/api` 请求转发到后端：

- 前端请求：`/api/...`
- 实际转发：`http://localhost:8000/api/...`

如需直连其它地址，可设置环境变量 `VITE_API_BASE_URL`。

## 目录结构

```text
src/
	api/
		http.js              # Axios 实例与拦截器
	layouts/
		BaseLayout.vue       # 基础布局（侧边栏 + 顶栏 + 内容区）
	router/
		index.js             # 路由配置与登录守卫
	stores/
		auth.js              # Pinia 认证状态（Token 持久化）
	views/
		LoginView.vue        # 登录页（当前为示例登录）
		DashboardView.vue    # 控制台占位页
		OrdersView.vue       # 订单页占位
		WorkOrdersView.vue   # 工单页占位
	App.vue                # 应用根组件
	main.js                # 应用入口（挂载 Pinia/Router/Element Plus）
	style.css              # 全局样式
```

## Axios 规范

`src/api/http.js` 已完成以下约定：

- 请求拦截器自动注入 `Authorization: Bearer <token>`
- 响应错误统一弹出 Element Plus 错误提示
- 默认 `baseURL`：`/api`

## 可用脚本

```bash
npm run dev      # 本地开发
npm run build    # 生产构建
npm run preview  # 预览构建产物
```
