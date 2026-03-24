# WMS Dispatch Frontend

WMS Dispatch 前端基于 Vue 3 + Vite，面向仓储调度场景。当前代码结构已按角色职责重构，重点保障管理员与调度员业务解耦，避免跨角色直接依赖。

## 技术栈

- Vue 3（Composition API + `<script setup>`）
- Vite
- Vue Router 4
- Pinia
- Element Plus
- Axios

## 启动与构建

```bash
# 安装依赖
npm install

# 启动开发环境
npm run dev

# 生产构建
npm run build

# 本地预览构建结果
npm run preview
```

默认开发地址：`http://localhost:5173`

## 环境变量

- `VITE_API_BASE_URL`

默认值为 `/api`，通过 Vite 代理转发到后端服务。

## 目录结构（重构后）

```text
frontend/
├─ src/
│  ├─ api/
│  │  ├─ admin/                        # 管理员域 API
│  │  │  ├─ customers.js
│  │  │  ├─ dashboard.js
│  │  │  ├─ orders.js
│  │  │  ├─ products.js
│  │  │  ├─ users.js
│  │  │  ├─ warehouses.js              # 含库存流水趋势/节点详情接口
│  │  │  └─ workOrders.js
│  │  ├─ dispatcher/                   # 调度员域 API
│  │  │  ├─ inventory.js               # 含本仓流水趋势/节点详情接口
│  │  │  ├─ orders.js
│  │  │  └─ transfers.js
│  │  ├─ worker/
│  │  │  └─ workOrders.js
│  │  └─ common/
│  │     ├─ auth.js
│  │     └─ http.js
│  │
│  ├─ components/
│  │  ├─ admin/
│  │  │  └─ dashboard/                 # 管理控制台图表组件
│  │  ├─ dispatcher/
│  │  └─ shared/                       # 跨角色复用组件
│  │     ├─ DetailInfoBlock.vue
│  │     ├─ InventoryFlowLineChart.vue
│  │     ├─ InventoryFlowNodeDetailDialog.vue
│  │     └─ OrderSearchBox.vue
│  │
│  ├─ layouts/
│  │  ├─ AdminLayout.vue
│  │  ├─ DispatcherLayout.vue
│  │  └─ WorkerLayout.vue
│  │
│  ├─ modules/
│  │  └─ dispatcher/
│  │     └─ mock/
│  │        └─ dispatcher.js
│  │
│  ├─ router/
│  │  ├─ guards/
│  │  │  └─ authGuard.js
│  │  ├─ routes/
│  │  │  ├─ admin.js
│  │  │  ├─ dispatcher.js
│  │  │  ├─ public.js
│  │  │  └─ worker.js
│  │  └─ index.js
│  │
│  ├─ stores/
│  │  ├─ auth.js
│  │  └─ dispatcher.js
│  │
│  ├─ utils/
│  │  └─ cnTime.js
│  │
│  ├─ views/
│  │  ├─ LoginView.vue
│  │  ├─ admin/
│  │  │  ├─ CustomersView.vue
│  │  │  ├─ DashboardView.vue
│  │  │  ├─ InventoryFlowRecordsView.vue     # 管理员多仓流水记录
│  │  │  ├─ OrdersView.vue
│  │  │  ├─ ProductsView.vue
│  │  │  ├─ UsersView.vue
│  │  │  ├─ WarehouseInventoryView.vue
│  │  │  ├─ WarehousesView.vue
│  │  │  └─ WorkOrdersView.vue
│  │  ├─ dispatcher/
│  │  │  ├─ DispatcherFlowRecordsView.vue    # 调度员本仓流水记录
│  │  │  ├─ DispatcherInventoryView.vue
│  │  │  ├─ DispatcherMyOrderDetailView.vue
│  │  │  ├─ DispatcherMyOrdersView.vue
│  │  │  ├─ DispatcherOrderDetailView.vue
│  │  │  ├─ DispatcherOrdersView.vue
│  │  │  ├─ DispatcherTransfersView.vue
│  │  │  ├─ DispatcherWorkbenchView.vue
│  │  │  └─ DispatcherWorkOrdersView.vue
│  │  └─ worker/
│  │     ├─ WorkerWorkOrderDetailView.vue
│  │     └─ WorkerWorkOrdersView.vue
│  │
│  ├─ App.vue
│  ├─ main.js
│  └─ style.css
│
├─ index.html
├─ package.json
└─ vite.config.js
```

## 新增页面与组件（库存流水）

1. 管理员：`InventoryFlowRecordsView.vue`
2. 调度员：`DispatcherFlowRecordsView.vue`
3. 公共图表：`InventoryFlowLineChart.vue`
4. 公共节点详情：`InventoryFlowNodeDetailDialog.vue`

说明：
流水统计口径已统一为仅 `delta_on_hand != 0` 的真实库存变化；节点详情支持展示业务化关联说明。

## 角色解耦规范

1. 不同角色业务页面必须物理隔离。

- 管理员页面只能放在 `views/admin`。
- 调度员页面只能放在 `views/dispatcher`。
- 工人页面只能放在 `views/worker`。
- 公共页面（如登录）放在 `views` 根目录。

1. 路由按角色拆分，不在单文件混写。

- 管理员：`router/routes/admin.js`
- 工人：`router/routes/worker.js`
- 调度员：`router/routes/dispatcher.js`
- 公共：`router/routes/public.js`

1. API 按角色域组织。

- 管理员接口在 `api/admin/*`
- 工人接口在 `api/worker/*`
- 调度员接口在 `api/dispatcher/*`
- 公共鉴权与请求基座在 `api/common/*`

1. 角色域内 mock/配置不得污染全局。

- 调度员 mock 统一放在 `modules/dispatcher/mock`。

## 命名规范

- 布局组件使用明确角色前缀：`AdminLayout`、`WorkerLayout`、`DispatcherLayout`。
- 路由文件以角色命名：`admin.js`、`worker.js`、`dispatcher.js`、`public.js`。
- 视图文件在角色目录中保持业务语义命名（如 `OrdersView.vue`）。

## 权限与跳转

- 全局鉴权守卫：`router/guards/authGuard.js`
- 登录后默认跳转规则：`stores/auth.js` 中 `getDefaultPathByRole()`
- 未登录访问受保护路由会跳转到 `/login`


## 开发约定

1. 新增页面前先确认角色归属，再创建到对应角色目录。
2. 新增接口前先确认角色归属，再创建到对应 `api` 子目录。
3. 跨角色复用逻辑应抽到公共层（`api/common`、通用组件或工具模块），禁止直接引用其他角色页面/模块。
4. 提交前至少进行一次本地路由与权限流程自测（登录、刷新、越权访问、登出）。
