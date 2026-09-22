# OpsManager

现代化的运维管理平台 - 基于 FastAPI + React

OpsManager 提供资产管理、监控告警、运维管理、权限体系、飞书集成等一体化运维能力，同时可作为同网段服务间的 **auth 服务**（工号登录、角色校验、首次登录强制改密）。

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
- 从 Prometheus 自动同步资产

### 2. 运维管理

- 发布记录管理
- 巡检任务配置
- SSL 证书管理（域名到期状态展示，每日 03:00 从 Prometheus 同步）
- DNS 记录管理
- 定时任务管理（查看、编辑、手动执行、执行日志查看）
- 监控主机配置管理（基于 Prometheus 配置仓库）

### 3. 监控告警

- 监控项配置（Ping、HTTP、TCP、UDP）
- 告警事件管理（Alertmanager webhook 接入）
- 告警规则配置
- 通知渠道配置（邮件、飞书、Webhook）
- 告警抑制与静默

### 4. 权限管理

- RBAC 权限模型（用户 / 角色 / 权限）
- 角色支持稳定 ASCII `code` 标识（外部服务可按 code 匹配）
- JWT 认证

### 5. 外部鉴权服务（auth 服务）

对外部服务（同信任网段）提供：

- **工号角色校验** `POST /api/v1/auth-service/verify-role`：传入工号，返回该员工是否属于行政/采购/营销角色及角色标识（name + code）
- **工号登录** `POST /api/v1/auth/external/login`：工号 + 密码登录并签发 JWT
- **首次登录强制改密**：初始密码登录后，除改密/登出/个人信息外一切业务接口被拦截（403），改密后自动解除

> 完整对接说明见 [外部鉴权服务对接文档](./docs/auth-service-role-verification.md)

### 6. 飞书集成

- 飞书用户自动同步（Open ID / Union ID / 工号）
- 卡片通知发送（支持个人和群聊）
- 交互卡片更新（通过 callback_id 验证）
- 飞书回调事件处理（消息接收、卡片交互）
- 通知记录管理与查询

### 7. IT 反馈

- 终端卡顿反馈提交
- 飞书卡片通知 IT 人员
- 处理状态流转（待处理 → 处理中 → 已解决）
- 处理方式记录与反馈

### 8. 匿名建议

- 员工匿名提交意见（通过 6 位 `query_code` 查询进度，对提交者隐藏身份）
- 飞书卡片流转：待审批（橙）→ 已审批（蓝）→ 市场部待执行（蓝）→ 已存档（绿） / 已驳回（灰）
- 部门负责人 / 指派人通过飞书卡片按钮审批通过或驳回
- 市场部通知组接收执行卡片，填写执行结果后存档
- 并发幂等：基于 `UPDATE ... WHERE status='pending'` + `rowcount` 校验，防止重复发卡
- 重试机制：飞书卡片发送/更新 3 次指数退避（1s→2s→4s）；query_code 冲突自动重试
- 详细业务逻辑流程图见 [匿名建议业务逻辑流程图](./docs/anonymous-suggestion-flow.md)

### 9. 其它服务模块

- **CRM 同步**：触发 CRM 增量/全量同步（`/api/v1/crm/sync`）
- **Git 仓库管理**：管理 Prometheus 监控配置仓库（克隆、稀疏检出、远端同步）
- **产物上传**：上传文件产物到 MinIO（`/api/v1/artifacts`）
- **每日健康巡检**：每日 09:00 基于 Prometheus 采集 linux / windows / 终端指标并生成报告、推送飞书
- **IT 巡检报告**：处理 IT 巡检报告（解析、存储、飞书通知）
- **PC 客户端版本**：版本信息同步与管理
- **导航管理 / 用户工具**：Open ID 查询、导航链接管理

## 定时任务

系统内置以下定时任务，通过 APScheduler 调度，支持在前端"运维管理 - 定时任务"页面统一管理：

| 任务名称 | 任务 ID | 分类 | 触发方式 | 功能说明 |
|---------|---------|------|---------|---------|
| 审计日志数据库清理 | cleanup-audit-logs-db | cleanup | 每天 03:00 | 清理过期的审计日志数据库记录 |
| 审计日志文件清理 | cleanup-audit-logs-file | cleanup | 每天 03:30 | 清理过期的审计日志文件 |
| 飞书用户同步 | sync-feishu-users | sync | 每天 02:00 | 从飞书同步用户数据到本地数据库 |
| Prometheus 资产同步 | sync-assets-from-prometheus | sync | 按配置间隔（默认 30 分钟） | 从 Prometheus 自动同步资产数据 |
| Prometheus 证书同步 | sync-certificates-from-prometheus | sync | 每天 03:00 | 从 Prometheus 同步 SSL 证书/域名到期数据 |
| 终端指标同步 | sync-terminal-metrics | sync | 每 5 分钟 | 从 Prometheus 同步终端性能指标（CPU/内存/磁盘）到本地数据库 |
| Ansible Playbook 执行 | execute-ansible-playbook | ops | 按配置时间 | 通过 SSH 执行 Ansible Playbook |
| IT 巡检报告处理 | process-it-report | ops | 每天 09:00 | 处理 IT 系统健康巡检报告并发送飞书通知 |
| 每日健康巡检 | daily-health-check | ops | 每天 09:00 | 基于 Prometheus 采集服务器/终端指标生成巡检报告 |
| Prometheus 监控配置远端同步 | sync-git-prometheus-conf | sync | 每 2 小时 | 与远端 prometheus 仓库同步监控配置（远端较新则拉取到本地） |

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

配置读取**项目根目录**的 `.env`（`backend/app/config.py` 指向 `../.env`），非 backend 目录：

```bash
cd ..  # 回到项目根 ops-manager
cp .env.example .env
# 编辑 .env 文件
```

4. 运行数据库迁移

```bash
cd backend
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

4. 生产构建

```bash
npm run build
```

## 项目结构

```
ops-manager/
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── api/v1/            # API 路由（auth, auth_service, assets, alerts, artifacts 等）
│   │   ├── core/              # 核心模块（security, middleware, auth_middleware, permissions, audit, rate_limit）
│   │   ├── crud/              # 数据库 CRUD 操作
│   │   ├── db/                # 数据库配置与会话管理、初始化数据
│   │   ├── integrations/      # 外部系统集成（feishu）
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   ├── schemas/           # Pydantic 请求/响应模型
│   │   ├── scheduler/         # APScheduler 定时任务调度器
│   │   ├── services/          # 业务逻辑（alerts, prometheus, crm, git_repo, monitor_config）
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
├── docs/                       # 业务流程与对接文档
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

## 业务流程图与对接文档

各核心业务模块的详细流程图（状态机、业务流程、并发幂等、时序图等）与对外对接文档维护在 `docs/` 目录下：

| 业务模块 | 文档 | 主要内容 |
|---|---|---|
| 匿名建议 | [docs/anonymous-suggestion-flow.md](./docs/anonymous-suggestion-flow.md) | 状态机、3 阶段完整业务流程、并发幂等时序图、重试机制、API 端点、ER 图、飞书卡片流转 |
| 外部鉴权服务 | [docs/auth-service-role-verification.md](./docs/auth-service-role-verification.md) | 工号角色校验 / 工号登录 / 首次登录强制改密，接口定义、错误码、调用示例、对接建议 |
| CICD 流水线通知 | [docs/cicd-feishu-flow.md](./docs/cicd-feishu-flow.md) · [流程图 HTML](./docs/cicd-feishu-flow.html) | 流水线开始 → 记录并生成唯一标识 → 判断新建还是更新 → 发出或原地更新飞书卡片 → 结束与卡片操作回调 → 超时盯守；说明为什么由两个角色分工（一方只负责接收与决策、一方只负责投递），以及唯一标识、单卡对应、去重、逐级退让、顺序约束五条关键规则 |

> 新增业务模块时，请在此表追加一行，并将流程图文档统一放置于 `docs/` 目录。

## 数据库模型

### 核心表

- `users` - 用户表（含工号 `employee_id`、待改密标记 `must_change_password`）
- `roles` - 角色表（含稳定 ASCII `code` 标识）
- `assets` - 资产表
- `labels` - 标签表
- `monitors` - 监控项表
- `deployments` - 发布记录表
- `certificates` - 证书/域名到期表
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
- `user_ip_bindings` - 用户 IP 绑定表（飞书账号登录限制）

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