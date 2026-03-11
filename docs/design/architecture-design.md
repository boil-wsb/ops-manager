# OpsManager V2 架构设计文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.1.0 |
| 创建日期 | 2026-03-11 |
| 更新日期 | 2026-03-11 |
| 作者 | 开发团队 |
| 状态 | 已更新 |

---

## 1. 项目概述

### 1.1 项目背景

OpsManager V2 是对原有 Django 运维管理平台的完全重构项目。原系统存在以下问题：

- Django 1.11 版本已停止维护，存在安全漏洞
- Python 版本老旧，无法使用现代语言特性
- 前端 Layui 框架过时，用户体验差
- 代码结构混乱，缺乏分层设计
- 安全设置不当（硬编码密钥、DEBUG模式开启）

### 1.2 重构目标

- 采用现代化技术栈，提升开发效率和系统性能
- 前后端分离架构，支持独立开发和部署
- 完善的安全机制，符合企业安全标准
- 清晰的代码分层，便于维护和扩展
- 容器化部署，简化运维流程

### 1.3 核心功能范围

本次重构仅保留三大核心模块：

1. **资产管理**：IDC物理服务器、虚拟机、网络设备统一管理
2. **运维管理**：发布记录、巡检任务、证书管理、DNS管理
3. **监控告警**：监控项配置、告警规则、通知渠道

### 1.4 设计约束

- 去除 ClickHouse 时序数据库
- 去除阿里云 SDK、企业微信等外部集成
- 去除 Prometheus、Grafana 监控栈
- 优先使用 HTTP，后续可过渡到 HTTPS
- 不考虑旧项目数据迁移

---

## 2. 架构设计

### 2.1 整体架构（简化版）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户层 (User Layer)                             │
│                              Browser / Mobile                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              接入层 (Access Layer)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                          │
│  │   Nginx     │  │  Rate Limit │  │   JWT Auth  │                          │
│  │  (反向代理)  │  │  (限流防护)  │  │  (认证鉴权)  │                          │
│  └─────────────┘  └─────────────┘  └─────────────┘                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│     前端层 (Frontend)  │  │     API 网关层         │  │    静态资源层         │
│  ┌─────────────────┐  │  │  ┌─────────────┐      │  │  ┌─────────────┐     │
│  │   React 18      │  │  │  │   FastAPI   │      │  │  │   MinIO     │     │
│  │  TypeScript     │◄─┼──┼─►│   (主应用)   │      │  │  │  (文件存储)  │     │
│  │  Ant Design Pro │  │  │  │  - REST API │      │  │  └─────────────┘     │
│  │  Zustand (状态)  │  │  │  │  - 自动文档  │      │  │                      │
│  │  React Query    │  │  │  └─────────────┘      │  │                      │
│  └─────────────────┘  │  │                      │  │                      │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│    服务层 (Services)   │  │    任务队列层          │  │    缓存层             │
│  ┌─────────────────┐  │  │  ┌─────────────┐      │  │  ┌─────────────┐     │
│  │  Asset Service  │  │  │  │   Celery    │      │  │  │    Redis    │     │
│  │  (资产管理)      │  │  │  │   Worker    │      │  │  │  - 会话缓存  │     │
│  ├─────────────────┤  │  │  │  - 异步任务  │      │  │  │  - 热点数据  │     │
│  │   Ops Service   │  │  │  │  - 定时任务  │      │  │  │  - 分布式锁  │     │
│  │  (运维管理)      │  │  │  └─────────────┘      │  │  └─────────────┘     │
│  ├─────────────────┤  │  │  ┌─────────────┐      │  │                      │
│  │ Monitor Service │  │  │  │ Celery Beat │      │  │                      │
│  │  (监控告警)      │  │  │  │  (定时调度)  │      │  │                      │
│  ├─────────────────┤  │  │  └─────────────┘      │  │                      │
│  │  Auth Service   │  │  │                      │  │                      │
│  │  (认证授权)      │  │  │                      │  │                      │
│  ├─────────────────┤  │  │                      │  │                      │
│  │ Notify Service  │  │  │                      │  │                      │
│  │  (消息通知)      │  │  │                      │  │                      │
│  └─────────────────┘  │  │                      │  │                      │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据层 (Data Layer)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        PostgreSQL 15+                               │   │
│  │              (主数据库 - SQLAlchemy 2.0 + Alembic)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈选型

#### 2.2.1 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.12+ | 编程语言 |
| FastAPI | 0.104+ | Web框架 |
| SQLAlchemy | 2.0+ | ORM框架 |
| Pydantic | v2 | 数据验证 |
| PostgreSQL | 15+ | 主数据库 |
| Redis | 7+ | 缓存/消息队列 |
| Celery | 5.3+ | 异步任务 |
| Alembic | 1.12+ | 数据库迁移 |
| Uvicorn | 0.24+ | ASGI服务器 |
| Pytest | 7.4+ | 测试框架 |
| Ruff | 0.1+ | 代码检查 |
| Black | 23+ | 代码格式化 |

#### 2.2.2 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18+ | UI框架 |
| TypeScript | 5.0+ | 类型系统 |
| Vite | 5.x | 构建工具 |
| Ant Design | 5.x | UI组件库 |
| Zustand | 4.x | 状态管理 |
| React Query | 5.x | 数据获取 |
| Axios | 1.6+ | HTTP客户端 |
| React Router | 6.x | 路由管理 |

#### 2.2.3 部署运维

| 技术 | 版本 | 用途 |
|------|------|------|
| Docker | 24+ | 容器化 |
| Docker Compose | 2.20+ | 编排工具 |
| Nginx | 1.24+ | 反向代理 |

---

## 3. 项目结构

```
ops-manager-v2/
├── README.md
├── docker-compose.yml
├── Makefile
├── .env.example
├── .gitignore
│
├── backend/                          # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI 应用入口
│   │   ├── config.py                 # 配置管理 (Pydantic Settings)
│   │   │
│   │   ├── api/                      # API 路由层
│   │   │   ├── __init__.py
│   │   │   ├── deps.py               # 依赖注入 (认证、数据库等)
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py           # 认证相关 API
│   │   │   │   ├── assets.py         # 资产管理 API
│   │   │   │   ├── ops.py            # 运维管理 API
│   │   │   │   ├── monitor.py        # 监控告警 API
│   │   │   │   ├── tasks.py          # 任务管理 API
│   │   │   │   └── users.py          # 用户管理 API
│   │   │   └── router.py             # 路由聚合
│   │   │
│   │   ├── core/                     # 核心模块
│   │   │   ├── __init__.py
│   │   │   ├── security.py           # JWT、密码加密
│   │   │   ├── exceptions.py         # 自定义异常
│   │   │   ├── middleware.py         # 中间件 (日志、CORS等)
│   │   │   └── events.py             # 生命周期事件
│   │   │
│   │   ├── models/                   # 数据库模型 (SQLAlchemy)
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # 基础模型
│   │   │   ├── user.py               # 用户模型
│   │   │   ├── asset.py              # 资产模型
│   │   │   ├── ops.py                # 运维模型
│   │   │   └── monitor.py            # 监控模型
│   │   │
│   │   ├── schemas/                  # Pydantic 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # 基础 Schema
│   │   │   ├── user.py               # 用户 Schema
│   │   │   ├── asset.py              # 资产 Schema
│   │   │   ├── ops.py                # 运维 Schema
│   │   │   └── monitor.py            # 监控 Schema
│   │   │
│   │   ├── services/                 # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # 基础 Service
│   │   │   ├── user_service.py       # 用户服务
│   │   │   ├── asset_service.py      # 资产服务
│   │   │   ├── ops_service.py        # 运维服务
│   │   │   ├── monitor_service.py    # 监控服务
│   │   │   └── ansible_service.py    # Ansible 执行服务
│   │   │
│   │   ├── crud/                     # 数据库操作层
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # 基础 CRUD
│   │   │   ├── crud_user.py
│   │   │   ├── crud_asset.py
│   │   │   └── ...
│   │   │
│   │   ├── db/                       # 数据库配置
│   │   │   ├── __init__.py
│   │   │   ├── session.py            # 数据库会话
│   │   │   └── base_class.py         # 声明基类
│   │   │
│   │   ├── tasks/                    # Celery 任务
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py         # Celery 配置
│   │   │   ├── asset_tasks.py        # 资产相关任务
│   │   │   ├── ops_tasks.py          # 运维相关任务
│   │   │   └── monitor_tasks.py      # 监控相关任务
│   │   │
│   │   ├── utils/                    # 工具函数
│   │   │   ├── __init__.py
│   │   │   ├── datetime.py           # 时间处理
│   │   │   ├── crypto.py             # 加密工具
│   │   │   └── validators.py         # 验证器
│   │   │
│   │   └── integrations/             # 外部集成（简化）
│   │       ├── __init__.py
│   │       ├── ansible/              # Ansible 封装
│   │       └── notify/               # 邮件/短信通知服务
│   │
│   ├── alembic/                      # 数据库迁移
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   │
│   ├── tests/                        # 测试
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_api/
│   │   └── test_services/
│   │
│   ├── requirements/
│   │   ├── base.txt                  # 基础依赖
│   │   ├── dev.txt                   # 开发依赖
│   │   └── prod.txt                  # 生产依赖
│   │
│   ├── Dockerfile
│   ├── entrypoint.sh
│   └── pyproject.toml
│
├── frontend/                         # React 前端
│   ├── public/
│   ├── src/
│   │   ├── components/               # 公共组件
│   │   │   ├── CommonTable/          # 通用表格
│   │   │   ├── CommonForm/           # 通用表单
│   │   │   ├── CommonModal/          # 通用弹窗
│   │   │   └── Layout/               # 布局组件
│   │   │
│   │   ├── pages/                    # 页面
│   │   │   ├── Login/                # 登录页
│   │   │   ├── Dashboard/            # 仪表盘
│   │   │   ├── Assets/               # 资产管理
│   │   │   │   ├── List/
│   │   │   │   ├── Detail/
│   │   │   │   └── Tree/
│   │   │   ├── Ops/                  # 运维管理
│   │   │   │   ├── Deploy/
│   │   │   │   ├── Inspection/
│   │   │   │   └── Certificate/
│   │   │   ├── Monitor/              # 监控告警
│   │   │   │   ├── Dashboard/
│   │   │   │   ├── Alerts/
│   │   │   │   └── Config/
│   │   │   └── System/               # 系统设置
│   │   │
│   │   ├── hooks/                    # 自定义 Hooks
│   │   │   ├── useAuth.ts
│   │   │   ├── useTable.ts
│   │   │   └── useRequest.ts
│   │   │
│   │   ├── stores/                   # 状态管理 (Zustand)
│   │   │   ├── authStore.ts
│   │   │   ├── userStore.ts
│   │   │   └── globalStore.ts
│   │   │
│   │   ├── services/                 # API 服务
│   │   │   ├── api.ts                # Axios 配置
│   │   │   ├── auth.ts
│   │   │   ├── assets.ts
│   │   │   ├── ops.ts
│   │   │   └── monitor.ts
│   │   │
│   │   ├── utils/                    # 工具函数
│   │   │   ├── request.ts            # 请求封装
│   │   │   ├── storage.ts            # 本地存储
│   │   │   └── constants.ts          # 常量
│   │   │
│   │   ├── types/                    # TypeScript 类型
│   │   │   ├── api.ts
│   │   │   ├── asset.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── routes.tsx                # 路由配置
│   │
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── nginx.conf
│
├── nginx/                            # Nginx 配置
│   └── nginx.conf
│
├── scripts/                          # 部署脚本
│   ├── init-db.sh
│   ├── backup.sh
│   └── deploy.sh
│
└── docs/                             # 文档
    ├── api/                          # API 文档
    ├── deployment/                   # 部署文档
    └── development/                  # 开发文档
```

---

## 4. 数据库设计

### 4.1 ER 图

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    users    │       │    roles    │       │ permissions │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────┤ id (PK)     │       │ id (PK)     │
│ username    │   M:N │ name        │       │ name        │
│ email       │       │ description │       │ resource    │
│ password    │       └─────────────┘       │ action      │
│ is_active   │                             └─────────────┘
│ created_at  │
└──────┬──────┘
       │ 1:N
       ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   assets    │◄──────┤ asset_labels│──────►│   labels    │
├─────────────┤   M:N ├─────────────┤   M:N ├─────────────┤
│ id (PK)     │       │ asset_id    │       │ id (PK)     │
│ asset_id    │       │ label_id    │       │ name        │
│ name        │       └─────────────┘       │ color       │
│ asset_type  │                             └─────────────┘
│ ip_address  │
│ status      │       ┌─────────────┐
│ idc         │◄──────┤   monitors  │
│ owner_id    │   1:N ├─────────────┤
└─────────────┘       │ id (PK)     │
                      │ name        │
                      │ target      │
                      │ interval    │
                      │ asset_id    │
                      └──────┬──────┘
                             │ 1:N
                             ▼
                      ┌─────────────┐
                      │   alerts    │
                      ├─────────────┤
                      │ id (PK)     │
                      │ severity    │
                      │ status      │
                      │ message     │
                      │ monitor_id  │
                      └─────────────┘

┌─────────────┐       ┌─────────────┐
│deployments  │       │inspection_  │
├─────────────┤       │tasks        │
│ id (PK)     │       ├─────────────┤
│ project_name│       │ id (PK)     │
│ version     │       │ name        │
│ environment │       │ task_type   │
│ status      │       │ cron_expr   │
│ deployer    │       │ is_enabled  │
└─────────────┘       └──────┬──────┘
                             │ 1:N
                             ▼
                      ┌─────────────┐
                      │inspection_  │
                      │reports      │
                      ├─────────────┤
                      │ id (PK)     │
                      │ status      │
                      │ summary     │
                      │ details     │
                      │ task_id     │
                      └─────────────┘
```

### 4.2 数据表结构

#### 4.2.1 用户认证模块

```sql
-- 用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 角色表
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    permissions JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 用户角色关联表
CREATE TABLE user_roles (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- 登录日志表
CREATE TABLE login_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50),
    ip_address INET,
    user_agent TEXT,
    login_status VARCHAR(20), -- success, failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

#### 4.2.2 资产管理模块

```sql
-- 资产表
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    asset_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    asset_type VARCHAR(50) NOT NULL, -- server, vm, network, storage
    status VARCHAR(20) DEFAULT 'active', -- active, offline, maintenance, retired
    
    -- 网络信息
    ip_address INET,
    private_ip INET,
    mac_address MACADDR,
    
    -- 硬件信息
    cpu_cores INTEGER,
    memory_gb INTEGER,
    disk_gb INTEGER,
    os_type VARCHAR(50),
    os_version VARCHAR(100),
    
    -- 位置信息
    idc VARCHAR(100),
    region VARCHAR(100),
    rack VARCHAR(50),
    
    -- 元数据
    labels JSONB DEFAULT '{}',
    description TEXT,
    
    -- 关联
    owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 资产标签表
CREATE TABLE labels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    color VARCHAR(7) DEFAULT '#1890ff',
    description VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 资产标签关联表
CREATE TABLE asset_labels (
    asset_id INTEGER REFERENCES assets(id) ON DELETE CASCADE,
    label_id INTEGER REFERENCES labels(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (asset_id, label_id)
);

-- 资产变更历史表
CREATE TABLE asset_history (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER REFERENCES assets(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL, -- create, update, delete
    changes JSONB,
    operator_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_assets_status ON assets(status);
CREATE INDEX idx_assets_type ON assets(asset_type);
CREATE INDEX idx_assets_idc ON assets(idc);
CREATE INDEX idx_assets_ip ON assets(ip_address);
CREATE INDEX idx_assets_owner ON assets(owner_id);
```

#### 4.2.3 运维管理模块

```sql
-- 发布记录表
CREATE TABLE deployments (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    environment VARCHAR(20) NOT NULL, -- dev, test, staging, prod
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, success, failed, rolled_back
    deployer VARCHAR(50),
    approver VARCHAR(50),
    deploy_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    log_output TEXT,
    rollback_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 巡检任务表
CREATE TABLE inspection_tasks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    task_type VARCHAR(50) NOT NULL, -- daily, weekly, monthly, custom
    cron_expression VARCHAR(100),
    target_assets JSONB DEFAULT '[]',
    check_items JSONB DEFAULT '[]',
    is_enabled BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 巡检报告表
CREATE TABLE inspection_reports (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES inspection_tasks(id) ON DELETE CASCADE,
    status VARCHAR(20), -- running, completed, failed
    total_checks INTEGER DEFAULT 0,
    passed_checks INTEGER DEFAULT 0,
    failed_checks INTEGER DEFAULT 0,
    warning_checks INTEGER DEFAULT 0,
    summary JSONB,
    details JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 证书信息表
CREATE TABLE certificates (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    issuer VARCHAR(200),
    subject VARCHAR(500),
    serial_number VARCHAR(100),
    valid_from TIMESTAMP WITH TIME ZONE,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    days_until_expiry INTEGER GENERATED ALWAYS AS (
        EXTRACT(DAY FROM (valid_until - CURRENT_TIMESTAMP))
    ) STORED,
    alert_threshold_days INTEGER DEFAULT 30,
    is_auto_renewal BOOLEAN DEFAULT FALSE,
    cert_content TEXT,
    key_content TEXT,
    status VARCHAR(20) DEFAULT 'valid', -- valid, expired, warning
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- DNS 记录表
CREATE TABLE dns_records (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    record_type VARCHAR(10) NOT NULL, -- A, AAAA, CNAME, MX, TXT, NS
    host VARCHAR(255) NOT NULL,
    value TEXT NOT NULL,
    ttl INTEGER DEFAULT 600,
    priority INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    provider VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_deployments_project ON deployments(project_name);
CREATE INDEX idx_deployments_status ON deployments(status);
CREATE INDEX idx_deployments_time ON deployments(deploy_time);
CREATE INDEX idx_certificates_expiry ON certificates(valid_until);
CREATE INDEX idx_certificates_status ON certificates(status);
```

#### 4.2.4 监控告警模块

```sql
-- 监控项表
CREATE TABLE monitors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    monitor_type VARCHAR(50) NOT NULL, -- ping, http, tcp, udp, custom
    target VARCHAR(500) NOT NULL,
    
    -- 检查配置
    interval_seconds INTEGER DEFAULT 60,
    timeout_seconds INTEGER DEFAULT 30,
    retry_count INTEGER DEFAULT 3,
    
    -- HTTP 特有配置
    http_method VARCHAR(10), -- GET, POST, PUT, DELETE
    http_headers JSONB,
    http_body TEXT,
    expected_status_code INTEGER,
    expected_response_content TEXT,
    
    -- 阈值配置
    threshold_warning INTEGER,
    threshold_critical INTEGER,
    
    -- 状态
    is_enabled BOOLEAN DEFAULT TRUE,
    current_status VARCHAR(20) DEFAULT 'unknown', -- up, down, unknown
    last_check_at TIMESTAMP WITH TIME ZONE,
    last_check_result JSONB,
    
    -- 关联
    asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL,
    
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 告警事件表
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    monitor_id INTEGER REFERENCES monitors(id) ON DELETE CASCADE,
    alert_rule_id INTEGER,
    
    -- 告警信息
    severity VARCHAR(20) NOT NULL, -- info, warning, critical
    status VARCHAR(20) DEFAULT 'firing', -- firing, acknowledged, resolved
    title VARCHAR(500),
    message TEXT,
    
    -- 触发值
    metric_name VARCHAR(100),
    metric_value VARCHAR(255),
    threshold_value VARCHAR(255),
    
    -- 时间
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- 通知状态
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_channels JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 告警规则表
CREATE TABLE alert_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- 条件
    condition_expression TEXT NOT NULL, -- 例如: cpu_usage > 80
    duration_seconds INTEGER DEFAULT 300,
    
    -- 告警级别
    severity VARCHAR(20) DEFAULT 'warning',
    
    -- 通知配置
    notification_channels JSONB DEFAULT '[]', -- email, sms, webhook
    notification_template TEXT,
    
    -- 抑制配置
    suppress_interval_minutes INTEGER DEFAULT 30,
    
    is_enabled BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 通知渠道表
CREATE TABLE notification_channels (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    channel_type VARCHAR(50) NOT NULL, -- email, sms, webhook
    
    -- 配置
    config JSONB NOT NULL,
    
    -- 状态
    is_enabled BOOLEAN DEFAULT TRUE,
    last_test_at TIMESTAMP WITH TIME ZONE,
    last_test_status VARCHAR(20),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 通知记录表
CREATE TABLE notification_logs (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES alerts(id) ON DELETE CASCADE,
    channel_id INTEGER REFERENCES notification_channels(id) ON DELETE SET NULL,
    channel_type VARCHAR(50),
    recipient VARCHAR(255),
    content TEXT,
    status VARCHAR(20), -- sent, failed, pending
    error_message TEXT,
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_monitors_status ON monitors(current_status);
CREATE INDEX idx_monitors_asset ON monitors(asset_id);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_monitor ON alerts(monitor_id);
CREATE INDEX idx_alerts_time ON alerts(started_at);
```

---

## 5. API 设计

### 5.1 认证相关 API

```yaml
# 认证模块
paths:
  /api/v1/auth/login:
    post:
      summary: 用户登录
      tags: [认证]
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                username:
                  type: string
                password:
                  type: string
              required: [username, password]
      responses:
        200:
          description: 登录成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  token_type:
                    type: string
                    default: bearer
                  expires_in:
                    type: integer
        401:
          description: 认证失败

  /api/v1/auth/logout:
    post:
      summary: 用户登出
      tags: [认证]
      security:
        - bearerAuth: []
      responses:
        200:
          description: 登出成功

  /api/v1/auth/refresh:
    post:
      summary: 刷新 Token
      tags: [认证]
      security:
        - bearerAuth: []
      responses:
        200:
          description: 刷新成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  expires_in:
                    type: integer

  /api/v1/auth/me:
    get:
      summary: 获取当前用户信息
      tags: [认证]
      security:
        - bearerAuth: []
      responses:
        200:
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
```

### 5.2 资产管理 API

```yaml
paths:
  /api/v1/assets:
    get:
      summary: 获取资产列表
      tags: [资产管理]
      security:
        - bearerAuth: []
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: page_size
          in: query
          schema:
            type: integer
            default: 20
        - name: asset_type
          in: query
          schema:
            type: string
        - name: status
          in: query
          schema:
            type: string
        - name: idc
          in: query
          schema:
            type: string
        - name: keyword
          in: query
          schema:
            type: string
      responses:
        200:
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  total:
                    type: integer
                  items:
                    type: array
                    items:
                      $ref: '#/components/schemas/Asset'

    post:
      summary: 创建资产
      tags: [资产管理]
      security:
        - bearerAuth: []
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AssetCreate'
      responses:
        201:
          description: 创建成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Asset'

  /api/v1/assets/{asset_id}:
    get:
      summary: 获取资产详情
      tags: [资产管理]
      security:
        - bearerAuth: []
      parameters:
        - name: asset_id
          in: path
          required: true
          schema:
            type: integer
      responses:
        200:
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AssetDetail'

    put:
      summary: 更新资产
      tags: [资产管理]
      security:
        - bearerAuth: []
      parameters:
        - name: asset_id
          in: path
          required: true
          schema:
            type: integer
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AssetUpdate'
      responses:
        200:
          description: 更新成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Asset'

    delete:
      summary: 删除资产
      tags: [资产管理]
      security:
        - bearerAuth: []
      parameters:
        - name: asset_id
          in: path
          required: true
          schema:
            type: integer
      responses:
        204:
          description: 删除成功

  /api/v1/assets/tree:
    get:
      summary: 获取资产树形结构
      tags: [资产管理]
      security:
        - bearerAuth: []
      responses:
        200:
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      type: object
```

### 5.3 数据模型定义

```yaml
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    # 用户模型
    User:
      type: object
      properties:
        id:
          type: integer
        username:
          type: string
        email:
          type: string
        full_name:
          type: string
        is_active:
          type: boolean
        is_superuser:
          type: boolean
        created_at:
          type: string
          format: date-time

    # 资产模型
    Asset:
      type: object
      properties:
        id:
          type: integer
        asset_id:
          type: string
        name:
          type: string
        asset_type:
          type: string
          enum: [server, vm, network, storage]
        status:
          type: string
          enum: [active, offline, maintenance, retired]
        ip_address:
          type: string
        private_ip:
          type: string
        idc:
          type: string
        region:
          type: string
        owner:
          $ref: '#/components/schemas/User'
        labels:
          type: array
          items:
            type: object
        created_at:
          type: string
          format: date-time

    AssetCreate:
      type: object
      required: [asset_id, name, asset_type]
      properties:
        asset_id:
          type: string
        name:
          type: string
        asset_type:
          type: string
        ip_address:
          type: string
        idc:
          type: string
        labels:
          type: array
          items:
            type: integer

    AssetUpdate:
      type: object
      properties:
        name:
          type: string
        status:
          type: string
        ip_address:
          type: string
        labels:
          type: array
          items:
            type: integer

    # 统一响应格式
    ApiResponse:
      type: object
      properties:
        code:
          type: integer
        message:
          type: string
        data:
          type: object
```

---

## 6. 安全设计

### 6.1 认证机制

- **JWT Token**: 使用 HS256 算法签名，包含用户ID、角色、过期时间
- **Token 有效期**: Access Token 8小时，Refresh Token 7天
- **密码策略**: 最小8位，必须包含大小写字母、数字、特殊字符
- **密码加密**: 使用 bcrypt 算法，cost factor 12

### 6.2 授权机制

- **RBAC 模型**: 基于角色的访问控制
- **权限粒度**: 支持资源级别的权限控制（查看、创建、编辑、删除）
- **API 权限**: 使用装饰器 `@require_permissions(['asset:read'])`

### 6.3 安全防护

| 防护措施 | 实现方式 |
|----------|----------|
| HTTP/HTTPS | 优先使用 HTTP，后续可配置 HTTPS |
| CORS | 白名单配置，仅允许指定域名 |
| CSRF | 使用 JWT，天然免疫 CSRF |
| SQL 注入 | SQLAlchemy ORM，参数化查询 |
| XSS | 前端转义输出，CSP 策略 |
| 限流 | SlowAPI 限流，每分钟 100 请求 |
| 敏感数据加密 | 数据库密码字段加密存储 |

### 6.4 安全配置

```python
# 环境变量配置，不硬编码
SECRET_KEY=${SECRET_KEY}  # 32位随机字符串
DATABASE_URL=${DATABASE_URL}  # 数据库连接字符串
REDIS_URL=${REDIS_URL}  # Redis 连接字符串

# 生产环境配置
DEBUG=False
ALLOWED_HOSTS=["ops.example.com"]
CORS_ORIGINS=["http://ops.example.com"]  # 根据实际协议配置
```

---

## 7. 部署架构

### 7.1 Docker Compose 部署（简化版）

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: ops-postgres
    environment:
      POSTGRES_USER: ${DB_USER:-opsmanager}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME:-opsmanager}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-opsmanager}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - ops-network

  redis:
    image: redis:7-alpine
    container_name: ops-redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - ops-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ops-backend
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-opsmanager}:${DB_PASSWORD}@postgres:5432/${DB_NAME:-opsmanager}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/2
    volumes:
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - ops-network

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ops-celery-worker
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-opsmanager}:${DB_PASSWORD}@postgres:5432/${DB_NAME:-opsmanager}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/2
    volumes:
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    command: celery -A app.tasks.celery_app worker -l info -c 4
    networks:
      - ops-network

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ops-celery-beat
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-opsmanager}:${DB_PASSWORD}@postgres:5432/${DB_NAME:-opsmanager}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/2
    volumes:
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    command: celery -A app.tasks.celery_app beat -l info
    networks:
      - ops-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: ops-frontend
    depends_on:
      - backend
    networks:
      - ops-network

  nginx:
    image: nginx:alpine
    container_name: ops-nginx
    ports:
      - "80:80"
      # - "443:443"  # 后续启用 HTTPS 时取消注释
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf
      # - ./ssl:/etc/nginx/ssl  # 后续启用 HTTPS 时取消注释
    depends_on:
      - frontend
      - backend
    networks:
      - ops-network

volumes:
  postgres_data:
  redis_data:

networks:
  ops-network:
    driver: bridge
```

### 7.2 Nginx 配置（HTTP 版本）

```nginx
server {
    listen 80;
    server_name localhost;
    client_max_body_size 100M;

    # 前端静态资源
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 静态文件
    location /static/ {
        alias /app/static/;
    }
}
```

### 7.3 部署流程

```bash
# 1. 克隆代码
git clone https://github.com/your-org/ops-manager-v2.git
cd ops-manager-v2

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置数据库密码、密钥等

# 3. 启动服务
docker-compose up -d

# 4. 执行数据库迁移
docker-compose exec backend alembic upgrade head

# 5. 创建初始管理员用户
docker-compose exec backend python -m app.scripts.create_admin

# 6. 检查服务状态
docker-compose ps
```

---

## 8. 开发规范

### 8.1 代码规范

- **Python**: 遵循 PEP 8，使用 Black 格式化，Ruff 检查
- **TypeScript**: 使用 ESLint + Prettier，严格模式
- **Git**: 使用 Conventional Commits 规范

### 8.2 提交规范

```
feat: 新增功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整
refactor: 重构代码
test: 测试相关
chore: 构建/工具相关
```

### 8.3 分支策略

```
main: 生产分支
develop: 开发分支
feature/*: 功能分支
hotfix/*: 紧急修复分支
release/*: 发布分支
```

---

## 9. 性能指标

### 9.1 目标性能

| 指标 | 目标值 |
|------|--------|
| API 响应时间 (P99) | < 200ms |
| 页面首屏加载 | < 2s |
| 并发用户数 | 500+ |
| 数据库查询 (单条) | < 50ms |

### 9.2 优化策略

- 数据库：合理索引、连接池、查询优化
- 缓存：Redis 缓存热点数据
- 前端：代码分割、懒加载、CDN
- 异步：Celery 处理耗时任务

---

## 10. 风险评估

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 功能遗漏 | 中 | 详细需求梳理、测试覆盖 |
| 性能不达标 | 中 | 压力测试、性能优化 |
| 团队学习成本 | 低 | 技术培训、文档完善 |

---

## 11. 附录

### 11.1 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 文档](https://docs.sqlalchemy.org/)
- [React 官方文档](https://react.dev/)
- [Ant Design Pro](https://pro.ant.design/)

### 11.2 术语表

| 术语 | 说明 |
|------|------|
| RBAC | 基于角色的访问控制 |
| JWT | JSON Web Token |
| ORM | 对象关系映射 |
| API | 应用程序接口 |
| CRUD | 增删改查操作 |

---

### 11.3 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0.0 | 2026-03-11 | 初始版本 | 开发团队 |
| v1.1.0 | 2026-03-11 | 简化架构：去除 ClickHouse、Prometheus/Grafana、阿里云 SDK、企业微信集成；调整为 HTTP 优先；去除数据迁移计划 | 开发团队 |

---

**文档结束**
