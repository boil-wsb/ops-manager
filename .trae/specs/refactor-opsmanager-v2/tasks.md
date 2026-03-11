# OpsManager V2 实施任务清单

## 任务概览

本文档包含 OpsManager V2 重构项目的所有实施任务，按照依赖关系和优先级排序。

---

## Phase 1: 基础架构搭建

### Task 1: 后端项目初始化
**描述**: 创建 FastAPI 后端项目基础结构
**优先级**: P0
**依赖**: 无

- [x] SubTask 1.1: 创建项目目录结构
  - 创建 backend/ 目录及子目录 (app/, alembic/, tests/)
  - 创建 __init__.py 文件

- [x] SubTask 1.2: 配置 Python 虚拟环境
  - 创建 requirements/base.txt (FastAPI, SQLAlchemy, Pydantic, Uvicorn)
  - 创建 requirements/dev.txt (pytest, black, ruff)
  - 创建 requirements/prod.txt (gunicorn, uvicorn[standard])

- [x] SubTask 1.3: 创建 FastAPI 应用入口
  - 创建 app/main.py
  - 配置 CORS、异常处理、生命周期事件
  - 创建健康检查端点 /health

- [x] SubTask 1.4: 配置管理
  - 创建 app/config.py (使用 Pydantic Settings)
  - 支持从环境变量读取配置
  - 区分开发/测试/生产环境

- [x] SubTask 1.5: 日志配置
  - 创建 app/core/logging.py
  - 配置结构化日志输出
  - 支持文件和控制台输出

---

### Task 2: 数据库基础配置
**描述**: 配置 PostgreSQL 数据库连接和迁移
**优先级**: P0
**依赖**: Task 1

- [x] SubTask 2.1: 数据库连接配置
  - 创建 app/db/session.py (SQLAlchemy async session)
  - 配置连接池
  - 创建数据库引擎

- [x] SubTask 2.2: 基础模型定义
  - 创建 app/db/base_class.py (DeclarativeBase)
  - 创建 app/models/base.py (基础模型类，包含 id, created_at, updated_at)

- [x] SubTask 2.3: Alembic 迁移配置
  - 初始化 alembic (alembic init)
  - 配置 alembic/env.py 使用异步引擎
  - 配置 alembic.ini

- [ ] SubTask 2.4: 创建数据库初始化脚本
  - 创建 scripts/init-db.sh
  - 支持创建数据库和初始迁移

---

### Task 3: Redis 缓存配置
**描述**: 配置 Redis 连接和缓存工具
**优先级**: P0
**依赖**: Task 1

- [x] SubTask 3.1: Redis 连接配置
  - 创建 app/core/redis.py
  - 配置 Redis 连接池
  - 支持异步操作

- [ ] SubTask 3.2: 缓存装饰器
  - 创建缓存工具函数
  - 支持设置过期时间
  - 支持缓存清除

---

### Task 4: 安全基础组件
**描述**: 实现 JWT、密码加密等安全功能
**优先级**: P0
**依赖**: Task 1

- [x] SubTask 4.1: 密码加密工具
  - 创建 app/core/security.py
  - 实现 get_password_hash (bcrypt)
  - 实现 verify_password

- [x] SubTask 4.2: JWT 工具
  - 实现 create_access_token
  - 实现 create_refresh_token
  - 实现 verify_token

- [x] SubTask 4.3: 异常定义
  - 创建 app/core/exceptions.py
  - 定义业务异常类 (AuthenticationError, PermissionError 等)
  - 配置全局异常处理器

---

## Phase 2: 用户认证与权限

### Task 5: 用户模型与 CRUD
**描述**: 实现用户相关的数据模型和操作
**优先级**: P0
**依赖**: Task 2, Task 4

- [ ] SubTask 5.1: 用户模型
  - 创建 app/models/user.py
  - 定义 User 模型 (id, username, email, hashed_password, is_active, is_superuser)

- [ ] SubTask 5.2: 用户 Schema
  - 创建 app/schemas/user.py
  - 定义 UserCreate, UserUpdate, UserInDB, UserResponse

- [ ] SubTask 5.3: 用户 CRUD
  - 创建 app/crud/crud_user.py
  - 实现 create, get, get_by_username, update, delete

- [ ] SubTask 5.4: 数据库迁移
  - 创建用户表迁移脚本
  - 执行迁移

---

### Task 6: 角色权限模型
**描述**: 实现 RBAC 角色权限系统
**优先级**: P0
**依赖**: Task 5

- [ ] SubTask 6.1: 角色模型
  - 创建 app/models/role.py
  - 定义 Role 模型 (id, name, description, permissions)

- [ ] SubTask 6.2: 用户角色关联
  - 创建 user_roles 关联表
  - 更新 User 模型添加 roles 关系

- [ ] SubTask 6.3: 角色 CRUD
  - 创建 app/crud/crud_role.py
  - 实现角色的增删改查

- [ ] SubTask 6.4: 数据库迁移
  - 创建角色表迁移脚本
  - 执行迁移

---

### Task 7: 认证 API
**描述**: 实现登录、登出、刷新 Token 等认证接口
**优先级**: P0
**依赖**: Task 5, Task 6

- [ ] SubTask 7.1: 认证依赖
  - 创建 app/api/deps.py
  - 实现 get_current_user (从 JWT 获取用户)
  - 实现 get_current_active_user
  - 实现 require_permissions 装饰器

- [ ] SubTask 7.2: 认证路由
  - 创建 app/api/v1/auth.py
  - 实现 POST /auth/login
  - 实现 POST /auth/logout
  - 实现 POST /auth/refresh
  - 实现 GET /auth/me

- [ ] SubTask 7.3: 注册路由
  - 在 app/api/router.py 中聚合路由
  - 配置 API 前缀 /api/v1

---

## Phase 3: 资产管理模块

### Task 8: 资产模型与 CRUD
**描述**: 实现资产相关的数据模型和操作
**优先级**: P1
**依赖**: Task 2, Task 7

- [ ] SubTask 8.1: 资产模型
  - 创建 app/models/asset.py
  - 定义 Asset 模型 (asset_id, name, type, status, ip, idc, hardware info 等)

- [ ] SubTask 8.2: 标签模型
  - 创建 app/models/label.py
  - 定义 Label 模型
  - 创建 asset_labels 关联表

- [ ] SubTask 8.3: 资产 Schema
  - 创建 app/schemas/asset.py
  - 定义 AssetCreate, AssetUpdate, AssetResponse

- [ ] SubTask 8.4: 资产 CRUD
  - 创建 app/crud/crud_asset.py
  - 实现增删改查和筛选功能

- [ ] SubTask 8.5: 资产历史记录
  - 创建 app/models/asset_history.py
  - 实现操作日志记录

- [ ] SubTask 8.6: 数据库迁移
  - 创建资产相关表迁移脚本
  - 执行迁移

---

### Task 9: 资产 API
**描述**: 实现资产管理的 RESTful API
**优先级**: P1
**依赖**: Task 8

- [ ] SubTask 9.1: 资产路由
  - 创建 app/api/v1/assets.py
  - 实现 GET /assets (列表，支持分页筛选)
  - 实现 POST /assets (创建)
  - 实现 GET /assets/{id} (详情)
  - 实现 PUT /assets/{id} (更新)
  - 实现 DELETE /assets/{id} (删除)

- [ ] SubTask 9.2: 资产树形结构
  - 实现 GET /assets/tree
  - 按 IDC/区域/机架组织层级

- [ ] SubTask 9.3: 标签管理
  - 实现标签的增删改查
  - 实现资产标签关联

---

### Task 10: 资产服务层
**描述**: 实现资产业务逻辑
**优先级**: P1
**依赖**: Task 9

- [ ] SubTask 10.1: 资产服务
  - 创建 app/services/asset_service.py
  - 实现批量导入导出
  - 实现资产统计功能

- [ ] SubTask 10.2: 资产变更通知
  - 资产变更时发送通知 (可选)

---

## Phase 4: 运维管理模块

### Task 11: 发布记录管理
**描述**: 实现发布记录功能
**优先级**: P1
**依赖**: Task 2, Task 7

- [ ] SubTask 11.1: 发布记录模型
  - 创建 app/models/deployment.py
  - 定义 Deployment 模型

- [ ] SubTask 11.2: 发布记录 Schema
  - 创建 app/schemas/deployment.py

- [ ] SubTask 11.3: 发布记录 API
  - 创建 app/api/v1/deployments.py
  - 实现 CRUD 接口
  - 支持按项目/环境筛选

- [ ] SubTask 11.4: 数据库迁移
  - 创建发布记录表迁移

---

### Task 12: 巡检任务系统
**描述**: 实现巡检任务和报告
**优先级**: P1
**依赖**: Task 11

- [ ] SubTask 12.1: 巡检任务模型
  - 创建 app/models/inspection.py
  - 定义 InspectionTask 模型
  - 定义 InspectionReport 模型

- [ ] SubTask 12.2: 巡检任务 API
  - 创建 app/api/v1/inspections.py
  - 实现任务 CRUD
  - 实现报告查询

- [ ] SubTask 12.3: 数据库迁移
  - 创建巡检相关表迁移

---

### Task 13: 证书管理
**描述**: 实现 SSL 证书管理
**优先级**: P1
**依赖**: Task 2, Task 7

- [ ] SubTask 13.1: 证书模型
  - 创建 app/models/certificate.py
  - 定义 Certificate 模型
  - 自动计算过期天数

- [ ] SubTask 13.2: 证书 API
  - 创建 app/api/v1/certificates.py
  - 实现 CRUD 接口
  - 实现到期提醒查询

- [ ] SubTask 13.3: 数据库迁移
  - 创建证书表迁移

---

### Task 14: DNS 管理
**描述**: 实现 DNS 记录管理
**优先级**: P2
**依赖**: Task 2, Task 7

- [ ] SubTask 14.1: DNS 记录模型
  - 创建 app/models/dns.py
  - 定义 DNSRecord 模型

- [ ] SubTask 14.2: DNS API
  - 创建 app/api/v1/dns.py
  - 实现 CRUD 接口

- [ ] SubTask 14.3: 数据库迁移
  - 创建 DNS 表迁移

---

## Phase 5: 监控告警模块

### Task 15: 监控项管理
**描述**: 实现监控项配置
**优先级**: P1
**依赖**: Task 2, Task 7

- [ ] SubTask 15.1: 监控项模型
  - 创建 app/models/monitor.py
  - 定义 Monitor 模型 (支持 ping, http, tcp, udp)

- [ ] SubTask 15.2: 监控项 Schema
  - 创建 app/schemas/monitor.py

- [ ] SubTask 15.3: 监控项 API
  - 创建 app/api/v1/monitors.py
  - 实现 CRUD 接口
  - 实现启停监控项

- [ ] SubTask 15.4: 数据库迁移
  - 创建监控项表迁移

---

### Task 16: 告警管理
**描述**: 实现告警事件和规则
**优先级**: P1
**依赖**: Task 15

- [ ] SubTask 16.1: 告警模型
  - 创建 Alert, AlertRule 模型
  - 创建 NotificationChannel 模型

- [ ] SubTask 16.2: 告警 API
  - 创建 app/api/v1/alerts.py
  - 实现告警查询、确认、解决
  - 实现告警规则 CRUD
  - 实现通知渠道配置

- [ ] SubTask 16.3: 数据库迁移
  - 创建告警相关表迁移

---

## Phase 6: 异步任务系统

### Task 17: Celery 配置
**描述**: 配置 Celery 异步任务框架
**优先级**: P1
**依赖**: Task 1, Task 3

- [ ] SubTask 17.1: Celery 应用
  - 创建 app/tasks/celery_app.py
  - 配置 Redis 作为 Broker 和 Backend
  - 配置任务序列化

- [ ] SubTask 17.2: 任务定义
  - 创建 app/tasks/asset_tasks.py
  - 创建 app/tasks/ops_tasks.py
  - 创建 app/tasks/monitor_tasks.py

---

### Task 18: 监控检查任务
**描述**: 实现监控检查异步任务
**优先级**: P1
**依赖**: Task 17, Task 15

- [ ] SubTask 18.1: 检查执行器
  - 实现 ping 检查
  - 实现 http 检查
  - 实现 tcp/udp 检查

- [ ] SubTask 18.2: 告警判定
  - 根据检查结果判定是否触发告警
  - 创建告警记录

- [ ] SubTask 18.3: 定时调度
  - 配置 Celery Beat 定时任务
  - 根据监控项 interval 执行检查

---

### Task 19: 巡检任务执行
**描述**: 实现巡检任务异步执行
**优先级**: P2
**依赖**: Task 17, Task 12

- [ ] SubTask 19.1: 巡检执行器
  - 实现巡检脚本执行
  - 收集检查结果

- [ ] SubTask 19.2: 报告生成
  - 生成巡检报告
  - 保存到数据库

---

### Task 20: 通知服务
**描述**: 实现告警通知功能
**优先级**: P2
**依赖**: Task 16, Task 17

- [ ] SubTask 20.1: 邮件通知
  - 实现邮件发送任务
  - 配置邮件模板

- [ ] SubTask 20.2: 通知记录
  - 记录通知发送状态
  - 支持重试机制

---

## Phase 7: 前端开发

### Task 21: 前端项目初始化
**描述**: 创建 React + TypeScript 前端项目
**优先级**: P0
**依赖**: 无

- [ ] SubTask 21.1: 项目创建
  - 使用 Vite 创建 React + TypeScript 项目
  - 配置 ESLint、Prettier

- [ ] SubTask 21.2: 依赖安装
  - 安装 Ant Design 5.x
  - 安装 React Router 6.x
  - 安装 Zustand、React Query、Axios

- [ ] SubTask 21.3: 项目结构
  - 创建目录结构 (components, pages, hooks, stores, services, utils, types)

- [ ] SubTask 21.4: 基础配置
  - 配置 Vite 代理
  - 配置路径别名
  - 创建环境变量配置

---

### Task 22: 前端基础组件
**描述**: 创建公共组件和布局
**优先级**: P0
**依赖**: Task 21

- [ ] SubTask 22.1: 布局组件
  - 创建 Layout 组件 (Header, Sidebar, Content)
  - 实现响应式布局

- [ ] SubTask 22.2: 通用组件
  - 创建 CommonTable (封装 ProTable)
  - 创建 CommonForm (封装表单)
  - 创建 CommonModal (封装弹窗)

- [ ] SubTask 22.3: 权限组件
  - 创建 Permission 组件
  - 根据权限控制按钮/菜单显示

---

### Task 23: 状态管理
**描述**: 实现前端状态管理
**优先级**: P0
**依赖**: Task 21

- [ ] SubTask 23.1: Auth Store
  - 创建 stores/authStore.ts
  - 管理登录状态和用户信息
  - 持久化存储 Token

- [ ] SubTask 23.2: User Store
  - 创建 stores/userStore.ts
  - 管理用户列表和详情

- [ ] SubTask 23.3: Global Store
  - 创建 stores/globalStore.ts
  - 管理全局状态 (主题、菜单等)

---

### Task 24: API 服务封装
**描述**: 封装后端 API 调用
**优先级**: P0
**依赖**: Task 21

- [ ] SubTask 24.1: Axios 配置
  - 创建 services/api.ts
  - 配置 baseURL、超时、拦截器
  - 自动添加 Authorization Header

- [ ] SubTask 24.2: API 服务
  - 创建 services/auth.ts
  - 创建 services/assets.ts
  - 创建 services/ops.ts
  - 创建 services/monitor.ts

- [ ] SubTask 24.3: 类型定义
  - 创建 types/api.ts (通用响应类型)
  - 创建 types/asset.ts
  - 创建 types/index.ts

---

### Task 25: 登录页面
**描述**: 实现用户登录页面
**优先级**: P0
**依赖**: Task 23, Task 24

- [ ] SubTask 25.1: 登录表单
  - 创建 pages/Login/index.tsx
  - 实现用户名密码表单
  - 表单验证

- [ ] SubTask 25.2: 登录逻辑
  - 调用登录 API
  - 保存 Token 到 Store
  - 登录成功跳转

- [ ] SubTask 25.3: 路由守卫
  - 实现未登录跳转
  - 实现已登录自动跳转首页

---

### Task 26: 仪表盘页面
**描述**: 实现系统仪表盘
**优先级**: P1
**依赖**: Task 25

- [ ] SubTask 26.1: 统计卡片
  - 显示资产总数、告警数等统计

- [ ] SubTask 26.2: 图表组件
  - 资产类型分布图
  - 告警趋势图

---

### Task 27: 资产管理页面
**描述**: 实现资产管理功能页面
**优先级**: P1
**依赖**: Task 25, Task 24

- [ ] SubTask 27.1: 资产列表页
  - 创建 pages/Assets/List/index.tsx
  - 表格展示资产列表
  - 实现搜索、筛选、分页

- [ ] SubTask 27.2: 资产创建/编辑
  - 创建资产表单
  - 支持新增和编辑

- [ ] SubTask 27.3: 资产详情
  - 创建资产详情页
  - 显示资产完整信息

- [ ] SubTask 27.4: 资产树
  - 实现资产树形展示
  - 按 IDC/区域组织

---

### Task 28: 运维管理页面
**描述**: 实现运维管理功能页面
**优先级**: P1
**依赖**: Task 25, Task 24

- [ ] SubTask 28.1: 发布记录页
  - 发布记录列表
  - 创建发布记录

- [ ] SubTask 28.2: 巡检任务页
  - 巡检任务列表
  - 创建/编辑巡检任务
  - 查看巡检报告

- [ ] SubTask 28.3: 证书管理页
  - 证书列表
  - 证书详情
  - 到期提醒展示

- [ ] SubTask 28.4: DNS 管理页
  - DNS 记录列表
  - 创建/编辑 DNS 记录

---

### Task 29: 监控告警页面
**描述**: 实现监控告警功能页面
**优先级**: P1
**依赖**: Task 25, Task 24

- [ ] SubTask 29.1: 监控项配置页
  - 监控项列表
  - 创建/编辑监控项
  - 启停控制

- [ ] SubTask 29.2: 告警事件页
  - 告警列表
  - 告警确认/解决
  - 告警详情

- [ ] SubTask 29.3: 告警规则页
  - 规则列表
  - 创建/编辑规则

- [ ] SubTask 29.4: 通知渠道页
  - 渠道配置
  - 测试发送

---

### Task 30: 系统设置页面
**描述**: 实现系统设置页面
**优先级**: P2
**依赖**: Task 25

- [ ] SubTask 30.1: 用户管理
  - 用户列表
  - 创建/编辑用户

- [ ] SubTask 30.2: 角色管理
  - 角色列表
  - 权限配置

---

## Phase 8: 部署配置

### Task 31: Docker 配置
**描述**: 创建 Docker 镜像配置
**优先级**: P1
**依赖**: Task 1, Task 21

- [ ] SubTask 31.1: 后端 Dockerfile
  - 创建 backend/Dockerfile
  - 多阶段构建优化
  - 配置非 root 用户运行

- [ ] SubTask 31.2: 前端 Dockerfile
  - 创建 frontend/Dockerfile
  - 使用 Nginx 托管静态文件

- [ ] SubTask 31.3: Docker Compose
  - 创建 docker-compose.yml
  - 配置 PostgreSQL、Redis、Backend、Frontend、Nginx
  - 配置网络和卷

---

### Task 32: Nginx 配置
**描述**: 配置 Nginx 反向代理
**优先级**: P1
**依赖**: Task 31

- [ ] SubTask 32.1: HTTP 配置
  - 创建 nginx/nginx.conf
  - 配置前端静态资源服务
  - 配置 API 反向代理

- [ ] SubTask 32.2: 优化配置
  - 配置 gzip 压缩
  - 配置缓存策略

---

### Task 33: 环境配置
**描述**: 创建环境变量配置模板
**优先级**: P1
**依赖**: Task 31

- [ ] SubTask 33.1: 环境变量模板
  - 创建 .env.example
  - 包含所有必要配置项

- [ ] SubTask 33.2: 初始化脚本
  - 创建 scripts/init-db.sh
  - 创建 scripts/create_admin.py

---

## Phase 9: 测试与优化

### Task 34: 后端测试
**描述**: 编写后端单元测试和集成测试
**优先级**: P2
**依赖**: Task 所有后端任务

- [ ] SubTask 34.1: 测试配置
  - 配置 pytest
  - 创建 conftest.py
  - 配置测试数据库

- [ ] SubTask 34.2: 单元测试
  - 测试 models
  - 测试 crud 操作
  - 测试 services

- [ ] SubTask 34.3: API 测试
  - 测试认证 API
  - 测试资产 API
  - 测试运维 API

---

### Task 35: 前端测试
**描述**: 编写前端测试
**优先级**: P2
**依赖**: Task 所有前端任务

- [ ] SubTask 35.1: 组件测试
  - 配置测试环境
  - 测试关键组件

---

### Task 36: 性能优化
**描述**: 系统性能优化
**优先级**: P2
**依赖**: Task 34

- [ ] SubTask 36.1: 后端优化
  - 数据库查询优化
  - 添加必要索引
  - 缓存优化

- [ ] SubTask 36.2: 前端优化
  - 代码分割
  - 懒加载
  - 打包优化

---

## Phase 10: 文档与交付

### Task 37: API 文档
**描述**: 生成和编写 API 文档
**优先级**: P2
**依赖**: 所有 API 开发完成

- [ ] SubTask 37.1: 自动文档
  - FastAPI 自动生成 OpenAPI 文档
  - 配置文档描述

- [ ] SubTask 37.2: 接口文档
  - 编写接口使用说明

---

### Task 38: 部署文档
**描述**: 编写部署文档
**优先级**: P2
**依赖**: Task 32

- [ ] SubTask 38.1: 部署指南
  - 编写部署步骤
  - 编写环境配置说明

- [ ] SubTask 38.2: 运维文档
  - 编写备份恢复指南
  - 编写常见问题处理

---

### Task 39: 开发文档
**描述**: 编写开发文档
**优先级**: P2
**依赖**: 所有开发完成

- [ ] SubTask 39.1: 开发指南
  - 编写本地开发环境搭建
  - 编写代码规范

- [ ] SubTask 39.2: 架构文档
  - 更新架构设计文档
  - 编写模块说明

---

## 任务依赖图

```
Phase 1 (基础架构)
├── Task 1 (后端初始化)
├── Task 2 (数据库配置) ──► Task 5 (用户模型)
├── Task 3 (Redis配置)
└── Task 4 (安全组件)

Phase 2 (用户认证)
├── Task 5 (用户模型) ──► Task 6 (角色权限) ──► Task 7 (认证API)
└── Task 4 (安全组件) ───────────────────────────────►

Phase 3 (资产管理)
└── Task 7 (认证API) ──► Task 8 (资产模型) ──► Task 9 (资产API) ──► Task 10 (资产服务)

Phase 4 (运维管理)
└── Task 7 (认证API) ──► Task 11 (发布记录) ──► Task 12 (巡检任务)
                      ├── Task 13 (证书管理)
                      └── Task 14 (DNS管理)

Phase 5 (监控告警)
└── Task 7 (认证API) ──► Task 15 (监控项) ──► Task 16 (告警管理)

Phase 6 (异步任务)
├── Task 3 (Redis) ──► Task 17 (Celery配置)
├── Task 15 (监控项) ──► Task 18 (监控检查)
├── Task 12 (巡检任务) ──► Task 19 (巡检执行)
└── Task 16 (告警管理) ──► Task 20 (通知服务)

Phase 7 (前端开发)
├── Task 21 (前端初始化)
├── Task 21 ──► Task 22 (基础组件)
├── Task 21 ──► Task 23 (状态管理)
├── Task 21 ──► Task 24 (API服务)
├── Task 23 + Task 24 ──► Task 25 (登录页)
├── Task 25 ──► Task 26 (仪表盘)
├── Task 25 ──► Task 27 (资产管理页)
├── Task 25 ──► Task 28 (运维管理页)
├── Task 25 ──► Task 29 (监控告警页)
└── Task 25 ──► Task 30 (系统设置页)

Phase 8 (部署配置)
├── Task 1 + Task 21 ──► Task 31 (Docker配置)
├── Task 31 ──► Task 32 (Nginx配置)
└── Task 31 ──► Task 33 (环境配置)

Phase 9 (测试优化)
├── 所有后端任务 ──► Task 34 (后端测试)
├── 所有前端任务 ──► Task 35 (前端测试)
└── Task 34 ──► Task 36 (性能优化)

Phase 10 (文档交付)
├── 所有API ──► Task 37 (API文档)
├── Task 32 ──► Task 38 (部署文档)
└── 所有任务 ──► Task 39 (开发文档)
```

---

## 任务优先级说明

- **P0**: 阻塞性任务，必须优先完成
- **P1**: 核心功能任务，影响主流程
- **P2**: 增强功能任务，可后续迭代

---

**文档结束**
