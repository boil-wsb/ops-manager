# OpsManager

现代化的运维管理平台 - 基于 FastAPI + React

## 技术栈

### 后端

- **FastAPI 0.104+** - 现代 Python Web 框架
- **SQLAlchemy 2.0** - ORM 框架
- **PostgreSQL 15** - 主数据库
- **Redis 7** - 缓存和消息队列
- **APScheduler 3.x** - 定时任务调度
- **JWT** - 身份认证
- **Alembic** - 数据库迁移
- **lark_oapi** - 飞书开放平台 SDK

### 前端

- **React 18** - UI 框架
- **TypeScript** - 类型安全
- **Ant Design 5.x** - UI 组件库
- **Zustand** - 状态管理
- **React Query** - 数据获取
- **React Router 6** - 路由管理

### 部署

- **Docker** - 容器化
- **Docker Compose** - 编排
- **Nginx** - 反向代理

## 功能模块

### 1. 资产管理

- 资产 CRUD 操作
- 资产分类（服务器、虚拟机、网络设备、存储）
- 资产标签管理
- 资产树形结构展示
- 资产变更历史

### 2. 运维管理

- 发布记录管理
- 巡检任务配置
- SSL 证书管理（到期提醒）
- DNS 记录管理
- 定时任务管理（查看、编辑、手动执行、执行日志查看）

### 3. 监控告警

- 监控项配置（Ping、HTTP、TCP、UDP）
- 告警事件管理
- 告警规则配置
- 通知渠道配置（邮件、飞书、Webhook）
- 告警抑制与静默

### 4. 权限管理

- RBAC 权限模型
- 用户管理
- 角色管理
- JWT 认证

### 5. 飞书集成

- 飞书用户自动同步（Open ID / Union ID）
- 卡片通知发送（支持个人和群聊）
- 交互卡片更新（通过 callback_id 验证）
- 飞书回调事件处理（消息接收、卡片交互）
- 通知记录管理与查询

### 6. IT 反馈

- 终端卡顿反馈提交
- 飞书卡片通知 IT 人员
- 处理状态流转（待处理 → 处理中 → 已解决）
- 处理方式记录与反馈

### 7. 匿名建议

- 员工匿名提交意见（通过 6 位 `query_code` 查询进度，对提交者隐藏身份）
- 飞书卡片流转：待审批（橙）→ 已审批（蓝）→ 市场部待执行（蓝）→ 已存档（绿） / 已驳回（灰）
- 部门负责人 / 指派人通过飞书卡片按钮审批通过或驳回
- 市场部通知组接收执行卡片，填写执行结果后存档
- 并发幂等：基于 `UPDATE ... WHERE status='pending'` + `rowcount` 校验，防止重复发卡
- 重试机制：飞书卡片发送/更新 3 次指数退避（1s→2s→4s）；query_code 冲突自动重试
- 详细业务逻辑流程图见 [匿名建议业务逻辑流程图](./docs/anonymous-suggestion-flow.md)

## 定时任务

系统内置以下定时任务，通过 APScheduler 调度，支持在前端"运维管理 - 定时任务"页面统一管理：

| 任务名称 | 任务 ID | 分类 | 触发方式 | 功能说明 |
|---------|---------|------|---------|---------|
| 审计日志数据库清理 | cleanup-audit-logs-db | cleanup | 每天 03:00 | 清理过期的审计日志数据库记录 |
| 审计日志文件清理 | cleanup-audit-logs-file | cleanup | 每天 03:30 | 清理过期的审计日志文件 |
| 飞书用户同步 | sync-feishu-users | sync | 每天 02:00 | 从飞书同步用户数据到本地数据库 |
| Prometheus 资产同步 | sync-assets-from-prometheus | sync | 按配置间隔 | 从 Prometheus 自动同步资产数据 |
| Prometheus 证书同步 | sync-certificates-from-prometheus | sync | 每天 03:00 | 从 Prometheus 同步 SSL 证书数据 |
| 终端指标同步 | sync-terminal-metrics | sync | 每 5 分钟 | 从 Prometheus 同步终端性能指标（CPU/内存/磁盘）到本地数据库 |
| Ansible Playbook 执行 | execute-ansible-playbook | ops | 按配置时间 | 通过 SSH 执行 Ansible Playbook |

### 终端指标同步

终端指标同步任务（`sync-terminal-metrics`）每 5 分钟执行一次，工作流程：

1. 通过 PrometheusClient 获取所有终端及其性能指标
2. 提取每个终端的 hostname、customer、instance、cpu_usage、memory_usage、disk_usage
3. 获取或创建对应的资产记录
4. 将指标数据写入 terminal_metrics 表

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.12+ (本地开发)
- Node.js 18+ (本地开发)

### 使用 Docker 部署

1. 克隆项目

```bash
git clone <repository-url>
cd ops-manager
```

2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的环境变量
```

3. 启动服务

```bash
docker-compose up -d
```

4. 访问系统

- 前端: <http://localhost:8080>
- API 文档: <http://localhost:8080/docs>

**默认管理员账号：**

- 用户名: `admin`
- 密码: `admin123`

> ⚠️ **安全提示**: 首次登录后请立即修改默认密码！

> **注意**: 后端服务启动时会自动检查数据库并初始化默认数据（包括管理员账号和角色），无需手动执行初始化脚本。

### 本地开发

#### 后端开发

1. 创建虚拟环境

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 安装依赖

```bash
pip install -r requirements/dev.txt
```

3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

4. 运行数据库迁移

```bash
python -m alembic upgrade head
```

5. 启动开发服务器

```bash
uvicorn app.main:app --reload
```

#### 前端开发

1. 安装依赖

```bash
cd frontend
npm install
```

2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

3. 启动开发服务器

```bash
npm run dev
```

## 项目结构

```
ops-manager/
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── api/v1/            # API 路由（auth, assets, alerts, feishu 等）
│   │   ├── core/              # 核心模块（security, middleware, permissions, audit）
│   │   ├── crud/              # 数据库 CRUD 操作
│   │   ├── db/                # 数据库配置与会话管理
│   │   ├── integrations/      # 外部系统集成（feishu）
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── scheduler/         # APScheduler 定时任务调度器
│   │   ├── services/          # 业务逻辑（alerts, prometheus）
│   │   ├── startup/           # 启动初始化
│   │   ├── tasks/             # 定时任务函数实现
│   │   ├── config.py          # 应用配置
│   │   └── main.py            # 应用入口
│   ├── alembic/               # 数据库迁移
│   ├── requirements/          # 依赖管理
│   └── Dockerfile
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── components/        # 通用组件（Layout, PermissionGuard）
│   │   ├── config/            # 前端配置（菜单权限、路由权限、主题）
│   │   ├── hooks/             # 自定义 Hooks（useFormModal, usePermission）
│   │   ├── pages/             # 页面组件（Alerts, Assets, System, Users 等）
│   │   ├── services/          # API 服务层
│   │   ├── stores/            # Zustand 状态管理
│   │   ├── types/             # TypeScript 类型定义
│   │   └── utils/             # 工具函数
│   └── Dockerfile
├── nginx/                      # Nginx 配置
├── docker-compose.yml
├── feishu-notify-api.md        # 飞书通知 API 接口文档
└── README.md
```

## API 文档

启动服务后，访问以下地址查看 API 文档：

- Swagger UI: <http://localhost:8080/docs>
- ReDoc: <http://localhost:8080/redoc>

飞书通知 API 详见 [feishu-notify-api.md](./feishu-notify-api.md)

## 业务流程图

各核心业务模块的详细流程图（状态机、业务流程、并发幂等、数据模型、时序图等）维护在 `docs/` 目录下，按业务模块组织：

| 业务模块 | 文档 | 主要内容 |
|---|---|---|
| 告警处理 | [docs/alert-processing-flow.md](./docs/alert-processing-flow.md) | Alertmanager webhook → 三阶段通知架构（prepare/execute/save）、第一性原理审查（13 个违反点）、并发安全（部分唯一索引 + ON CONFLICT）、多收件人 1:N 卡片一致性、闭环验证 |
| 匿名建议 | [docs/anonymous-suggestion-flow.md](./docs/anonymous-suggestion-flow.md) | 状态机、3 阶段完整业务流程、并发幂等时序图、重试机制、API 端点、ER 图、飞书卡片流转 |

> 新增业务模块时，请在此表追加一行，并将流程图文档统一放置于 `docs/` 目录。

## 数据库模型

### 核心表

- `users` - 用户表
- `roles` - 角色表
- `assets` - 资产表
- `labels` - 标签表
- `monitors` - 监控项表
- `deployments` - 发布记录表
- `certificates` - 证书表
- `dns_records` - DNS 记录表

### 监控告警

- `alert_templates` - 告警模板表
- `alert_receivers` - 告警接收人表
- `alert_history` - 告警历史表

### 飞书与通知

- `notification_records` - 通知记录表（含 chat_id, receive_type, callback_id）
- `notification_groups` - 通知组表
- `notification_group_members` - 通知组成员表

### 定时任务

- `scheduled_tasks` - 定时任务表（任务定义、触发配置、执行状态）
- `task_execution_logs` - 任务执行日志表（执行时间、耗时、结果、错误信息）

### 匿名建议

- `suggestions` - 匿名建议主表（content / status / query_code / submitter_id / market_result / reject_reason）
- `suggestion_assignments` - 建议指派关系表（department_id / assignee_open_id / open_message_id / status）

> 业务流转详见 [匿名建议业务逻辑流程图](./docs/anonymous-suggestion-flow.md)

### 其他

- `it_feedbacks` - IT 反馈表
- `terminal_metrics` - 终端指标表
- `pc_client_versions` - PC 客户端版本表
- `system_configs` - 系统配置表（键值对配置，按分组管理）

## 监控检查类型

- **Ping** - ICMP ping 检查
- **HTTP** - HTTP/HTTPS 请求检查
- **TCP** - TCP 端口检查
- **UDP** - UDP 端口检查

## 告警级别

- **Info** - 信息
- **Warning** - 警告
- **Critical** - 严重

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

[MIT](LICENSE)

## 联系方式

- 项目主页: <https://github.com/your-org/ops-manager-v2>
- 问题反馈: <https://github.com/your-org/ops-manager-v2/issues>
