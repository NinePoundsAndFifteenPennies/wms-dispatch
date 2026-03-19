# WMS Dispatch — 智能仓储调度管理系统

一个面向仓储运营场景的全栈调度管理平台，集成 AI Agent 实现自然语言驱动的工单调度与跨仓调拨，支持多角色协作。

---

## 目录

- [WMS Dispatch — 智能仓储调度管理系统](#wms-dispatch--智能仓储调度管理系统)
  - [目录](#目录)
  - [功能概览](#功能概览)
  - [角色与权限](#角色与权限)
  - [功能详情](#功能详情)
  - [业务规则](#业务规则)
  - [技术栈](#技术栈)
  - [快速开始](#快速开始)
    - [环境要求](#环境要求)
    - [安装](#安装)
    - [环境变量](#环境变量)
  - [项目结构](#项目结构)
  - [安全设计](#安全设计)
  - [License](#license)

---

## 功能概览

| 模块 | 核心能力 |
|------|----------|
| 账号与人员管理 | 多角色账号、工人技能标签、仓库归属（调度员和工人均绑定仓库） |
| 客户管理 | 客户信息维护，订单关联客户 |
| 仓储与商品管理 | 仓库信息（含地理坐标）、商品档案、库存盘点 |
| 订单管理 | 订单创建、调度员接单认领、状态跟踪、明细管理 |
| 工单管理 | 拣货 / 备货 / 发货三类工单，强制串行推进，手动与 AI 双路创建 |
| AI 工单调度 | 自然语言输入，Agent 自动匹配工人与技能，生成工单方案 |
| AI 跨仓调拨 | 自然语言描述库存缺口，Agent 给出调拨建议，走审批流 |
| 效率报告 | 管理员自定义时间范围，LLM 生成图表 + 文字分析报告 |
| 告警通知 | 超时工单、低库存、工单异常备注自动触发站内通知 |

---

## 角色与权限

系统内置三种角色，权限严格隔离：

- **管理员（Admin）**：管理所有账号、仓库、商品、库存、订单；审批跨仓调拨申请；查看效率报告；终止进行中的工单。
- **调度员（Dispatcher）**：查看本仓库订单并认领接单；创建、管理工单；使用 AI Agent 调度工单与发起调拨；接收告警通知。
- **工人（Worker）**：查看分配给自己的工单；更新工单执行状态；提交完工备注。

---

## 功能详情

完整功能模块说明已拆分到文档：

- [功能模块说明](./docs/feature-modules.md)

README 只保留概览与快速开始，详细模块说明请以上述文档为准。

---

## 业务规则

> 详细业务规则说明见 [service_rule.md](./docs/service_rule.md)。

---

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 | Vue 3 |
| 后端 | Python / FastAPI |
| 数据库 | PostgreSQL |
| AI Framework | LangChain |
| LLM | Qwen API |
| 地图渲染 | Leaflet + OpenStreetMap |
| 地理编码 | Nominatim（OpenStreetMap） |
| 通知推送 | WebSocket / Server-Sent Events |

---

## 快速开始

### 环境要求

- Python >= 3.11
- Node.js >= 18
- PostgreSQL >= 15
- 有效的 Qwen API Key

### 安装

```bash
git clone https://github.com/your-org/wms-dispatch.git
cd wms-dispatch
cp .env.example .env
# 填写 .env 中的数据库连接和 API Key

# 启动数据库（需要 Docker）
docker compose up -d

# 后端
cd backend
pip install -r requirements.txt
alembic upgrade head      # 执行数据库迁移
uvicorn main:app --reload # 启动开发服务器

# 前端
cd frontend
npm install
npm run dev
```

### 环境变量

参见 [.env.example](./.env.example)：

```env
DATABASE_URL=postgresql://user:password@localhost:5432/wms
QWEN_API_KEY=your_qwen_api_key
SECRET_KEY=your_secret_key
```

> ⚠️ **安全提示**：`SECRET_KEY` 应使用足够长度的随机字符串（建议 ≥ 32 位），不要使用默认值或弱密钥。

---

## 项目结构

```
wms-dispatch/
├── backend/
│   ├── modules/
│   │   ├── admin/          # 管理员模块
│   │   ├── dispatcher/     # 调度员模块
│   │   ├── worker/         # 工人模块
│   │   └── agent/          # AI Agent 模块
│   ├── shared/             # 公共工具、中间件、依赖注入
│   ├── scheduler/          # 定时任务（告警检测、接单超时检测、入库超时提醒）
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── components/     # 公共组件
│   │   └── stores/         # Pinia 状态管理
│   └── vite.config.js
├── docs/
│   ├── database.md             # 数据库设计文档
│   └── development-plan.md     # 第一步开发计划
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 安全设计

| 安全领域 | 措施 |
|----------|------|
| 身份认证 | JWT Token（python-jose / bcrypt），Token 有效期控制 |
| 权限控制 | 基于角色的访问控制（RBAC），API 层按角色拦截请求 |
| 密码安全 | bcrypt 哈希存储，禁止明文传输和存储 |
| AI Agent 隔离 | Agent SQL Tool 仅限只读事务，写操作必须走应用 API |
| 输入校验 | Pydantic Schema 校验所有 API 入参，防止注入和非法数据 |
| 通信安全 | 生产环境强制 HTTPS，WebSocket 使用 WSS |

> 详细数据库安全设计见 [database.md](./docs/database.md) 中的「安全设计备注」。

---

## License

[MIT](./LICENSE)