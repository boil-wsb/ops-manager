# 项目审查发现文档

## 一、项目结构概览

### 1.1 后端结构 (Backend)
```
backend/
├── alembic/versions/          # 数据库迁移文件 (10个)
├── app/
│   ├── api/v1/               # API 端点 (11个模块)
│   ├── core/                 # 核心功能
│   │   ├── audit/            # 审计日志
│   │   ├── exceptions.py      # 异常定义
│   │   ├── logging.py        # 日志配置
│   │   ├── middleware.py      # 中间件
│   │   ├── permissions.py    # 权限
│   │   ├── redis.py          # Redis
│   │   ├── responses.py      # 响应格式
│   │   └── security.py       # 安全
│   ├── crud/                 # CRUD 操作 (6个)
│   ├── db/                   # 数据库
│   ├── models/               # SQLAlchemy 模型 (9个)
│   ├── schemas/              # Pydantic schemas (9个)
│   ├── services/             # 业务服务
│   │   └── prometheus/       # Prometheus 集成
│   └── tasks/                # Celery 任务 (6个)
├── requirements/             # 依赖文件 (3个)
└── scripts/                  # 工具脚本 (20+个)
```

### 1.2 前端结构 (Frontend)
```
frontend/
├── src/
│   ├── components/            # 通用组件 (3个)
│   ├── config/                # 配置 (2个)
│   ├── hooks/                 # 自定义 hooks (3个)
│   ├── pages/                 # 页面 (15个)
│   ├── services/              # API 服务 (9个)
│   ├── stores/                # 状态管理 (2个)
│   ├── types/                 # 类型定义 (1个)
│   └── utils/                 # 工具函数 (1个)
├── public/                    # 静态资源
├── eslint.config.js           # ESLint 配置
└── package.json
```

---

## 二、详细问题清单

### 2.1 Migration 文件问题

| 文件名 | 日期 | 功能 | 状态 |
|--------|------|------|------|
| `20250312_0001_initial_migration.py` | 2025-03-12 | 初始迁移 | ✅ 保留 |
| `20250313_0002_add_audit_logs.py` | 2025-03-13 | 审计日志 | ✅ 保留 |
| `20250313_0003_add_prometheus_sync_fields.py` | 2025-03-13 | Prometheus字段 | ✅ 保留 |
| `20250316_0004_create_navigation_links.py` | 2025-03-16 | 导航链接 | ✅ 保留 |
| `20250316_0005_add_terminal_fields.py` | 2025-03-16 | 终端字段 | ✅ 保留 |
| `20250317_0006_add_terminal_enum.py` | 2025-03-17 | 终端枚举 | ✅ 保留 |
| `20260318_0007_add_it_feedback.py` | 2026-03-18 | IT反馈 | ✅ 保留 |
| `20260319_0904_be2745244769_add_client_ip_to_it_feedback.py` | 2026-03-19 | 客户端IP | ⚠️ 可能重复 |
| `20260319_1413_bf7b8f22ad21_add_owner_name_to_asset.py` | 2026-03-19 | 资产所有者 | ⚠️ 可能重复 |
| `20260319_1421_9370668b55fe_add_owner_name_to_asset.py` | 2026-03-19 | 资产所有者 | ⚠️ 可能重复 |

**分析**: 最后三个 migration 文件都是 2026-03-19 创建，且有两个是相同功能 (add_owner_name_to_asset)，需要确认依赖关系。

### 2.2 Prometheus 服务文件

| 文件 | 大小 | 说明 |
|------|------|------|
| `services/prometheus.py` | 单文件 | 旧版入口 |
| `services/prometheus/__init__.py` | - | 目录入口 |
| `services/prometheus/asset_sync.py` | - | 同步模块 |
| `services/prometheus/asset_sync_optimized.py` | - | 优化版本? |
| `services/prometheus/client.py` | - | Prometheus 客户端 |

**分析**: `asset_sync.py` 和 `asset_sync_optimized.py` 需要确认哪个是活跃使用的。

### 2.3 依赖版本分析

#### 后端依赖 (base.txt)
```diff
- fastapi==0.104.1        # 最新: 0.115.12
- uvicorn[standard]==0.24.0  # 最新: 0.34.0
- pydantic==2.5.0          # 最新: 2.10.5
- pydantic-settings==2.1.0  # 最新: 2.7.1
- sqlalchemy[asyncio]==2.0.23  # 最新: 2.0.36
- alembic==1.12.1          # 最新: 1.13.3
```

#### 前端依赖 (package.json)
```diff
- antd: ^6.3.2             # 最新: 6.7.8
- @tanstack/react-query: ^5.90.21  # 最新: 5.67.3
- react: ^19.2.0           # ✅ 最新
- zustand: ^5.0.11         # ✅ 最新
```

### 2.4 TypeScript 问题

| 文件 | 问题 | 规则代码 |
|------|------|----------|
| `AssetDiscovery.tsx` | 可能有未使用导入 | TS6133 |
| `App.tsx` | Menu items 需类型断言 | TS1484 |
| `services/*.ts` | snake_case 命名 | TS2551 |

---

## 三、安全问题分析

### 3.1 配置安全
- `SECRET_KEY` 默认值: `"your-secret-key-change-in-production"`
- CORS: 使用配置字符串解析，需确认生产环境设置

### 3.2 API 安全
- 无 API 限流中间件
- 无请求大小限制
- 无请求超时配置

### 3.3 密码安全
- 使用 `passlib[bcrypt]` ✅
- 使用 `argon2-cffi` ✅

---

## 四、代码组织问题

### 4.1 Backend
1. `core/permissions.py` 与 `core/security.py` 功能重叠
2. `services/prometheus.py` 散落在多个位置
3. 测试脚本分散在 `scripts/` 目录

### 4.2 Frontend
1. `pages/Dashboard.tsx` 未在 `Dashboard/` 子目录
2. 无统一的 Loading/Error 组件
3. 无统一的 Empty 状态组件

---

## 五、容器化问题

### 5.1 Docker Compose
- Celery 使用 `-B` 参数 (已废弃)
- Nginx 端口 8080 硬编码
- 无 healthcheck for backend

### 5.2 Dockerfile
- 前端多阶段构建需确认
- 后端无 requirements 安装步骤

---

## 六、测试覆盖

### 6.1 Backend
- `pyproject.toml` 配置了 pytest
- 但无 `tests/` 目录
- 只有散落的 `scripts/test_*.py`

### 6.2 Frontend
- 只有 lint 脚本
- 无 Jest/Vitest 配置
- 无测试用例

---

## 七、CI/CD 现状

`.gitlab-ci.yml` 存在，需确认包含:
- ✅ Lint
- ✅ Build
- ❌ Test
- ❌ Security Scan
- ❌ Coverage

---

## 八、环境变量检查

### 必须设置的环境变量
```bash
# Security (生产环境必须)
SECRET_KEY=                    # 必须设置复杂密钥
DATABASE_URL=                  # 数据库连接
REDIS_URL=                     # Redis 连接

# 可选 (有默认值)
APP_NAME=OpsManager V2
DEBUG=false
LOG_LEVEL=INFO
```

### .env.example 覆盖情况
✅ 已有 `.env.example`
⚠️ 需确认所有敏感变量都有说明