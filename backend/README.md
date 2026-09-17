# OpsManager 后端

运维管理平台后端服务，基于 FastAPI + SQLAlchemy 2.0（异步）+ PostgreSQL。

## 技术栈

- **FastAPI 0.104+** - Web 框架（异步）
- **SQLAlchemy 2.0**（async） - ORM
- **PostgreSQL 15 + asyncpg** - 数据库
- **Redis 7 (redis.asyncio)** - 缓存 / 限流
- **Alembic** - 数据库迁移
- **APScheduler** - 内置定时任务调度
- **PyJWT + Argon2** - 认证与密码哈希
- **lark_oapi** - 飞书开放平台 SDK

## 目录结构

```
backend/
├── app/
│   ├── api/deps.py            # 公共依赖（get_db, get_current_user, require_permissions）
│   ├── api/router.py          # 路由汇总注册
│   ├── api/v1/                # 各业务模块路由
│   ├── core/                  # 核心：security( JWT/Argon2)、auth_middleware(全局鉴权)、
│   │                          #       rate_limit、audit、logging、cache、exceptions
│   ├── crud/                  # 数据访问层
│   ├── db/                    # 会话/连接池、init_db（默认角色权限与管理员初始化）
│   ├── integrations/          # 外部系统（飞书）
│   ├── models/                # SQLAlchemy 模型
│   ├── schemas/               # Pydantic 模型
│   ├── scheduler/             # APScheduler 内置任务注册与执行
│   ├── services/              # 业务服务（prometheus/crm/git_repo/monitor_config 等）
│   ├── tasks/                 # 内置定时任务实现
│   ├── config.py              # 配置（从项目根目录 .env 读取）
│   └── main.py                # 应用入口（含 lifespan 初始化）
├── alembic/versions/          # 数据库迁移脚本（0001 起，revision id 不超过 32 字符）
├── scripts/                   # 临时/辅助脚本
├── requirements/              # 依赖（dev / prod）
└── .venv / venv               # 虚拟环境
```

## 本地开发

```bash
# 1. 环境变量：配置读取【项目根目录】的 .env（config.py 指向 ../.env），而非 backend/.env
cp ../.env.example ../.env

# 2. 安装依赖
pip install -r requirements/dev.txt

# 3. 数据库迁移
python -m alembic upgrade head

# 4. 启动（默认 8000）
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> 首次启动（lifespan）会自动执行 `init_db`：创建缺失表、预置权限与默认角色（superadmin/admin/operator/viewer 等）、创建默认管理员 `admin/admin123`。

## 常用命令

```bash
# 生成迁移（改模型后）
python -m alembic revision --autogenerate -m "描述"

# 应用迁移
python -m alembic upgrade head

# 回滚
python -m alembic downgrade -1

# 测试
pytest

# 覆盖率
coverage run -m pytest && coverage report

# 代码规范
ruff check app

# 安全扫描
bandit -r app
```

## API 文档

- Swagger UI: `http://localhost:8000/docs`（DEBUG 模式）
- 认证：大多数接口需 `Authorization: Bearer <token>`；认证接口位于 `/api/v1/auth/*`（全局鉴权例外前缀）；信任网段 + `AUTH_EXCLUDED_PATHS` 内的接口可免 JWT（如 `/api/v1/auth-service/*`）。

## 关键说明

- **配置读取**：`.env` 位于项目根目录（`backend/app/config.py` 向上三级）；同步部署时注意区分根 `.env` 与 `backend/.env`。
- **全局鉴权中间件**（`core/auth_middleware.py`）：硬编码白名单前缀 + 信任网段放行；token 携带 `pwd_change_required` 标记时（首次登录待改密）拦截一切业务接口返回 403。
- **外部鉴权服务**：工号角色校验 / 工号登录 / 首次登录强制改密，对接见 `docs/auth-service-role-verification.md`。
- **日志**：结构化日志（console/json），审计日志（`@audit_log`）记录操作流水。
- **限流**：slowapi，登录等接口按 IP 限流（`DISABLE_RATE_LIMIT=true` 可关闭）。
- **子进程**：git 操作统一走 `GitRepoService.run_git()`（subprocess.run 带超时），禁止裸 Popen / shell=True。