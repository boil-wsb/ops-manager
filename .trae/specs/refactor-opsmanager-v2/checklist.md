# OpsManager V2 验收检查清单

本文档包含所有需要验证的检查点，确保项目按照规范实现。

---

## Phase 1: 基础架构验收

### Backend Infrastructure

- [ ] **Backend 项目结构正确**
  - 目录结构符合设计文档
  - 所有 __init__.py 文件存在
  - 配置文件分离 (base/dev/prod)

- [ ] **FastAPI 应用正常运行**
  - `uvicorn app.main:app --reload` 可启动
  - 访问 `/docs` 显示 Swagger 文档
  - 访问 `/health` 返回健康状态

- [ ] **配置管理正确**
  - 使用 Pydantic Settings
  - 支持从环境变量读取
  - 敏感信息不硬编码

- [ ] **日志配置正确**
  - 日志格式统一
  - 支持文件和控制台输出
  - 日志级别可配置

### Database

- [ ] **数据库连接正常**
  - 可连接到 PostgreSQL
  - 连接池配置正确
  - 支持异步操作

- [ ] **基础模型定义正确**
  - Base 模型包含 id, created_at, updated_at
  - 使用 SQLAlchemy 2.0 语法

- [ ] **Alembic 迁移正常**
  - `alembic init` 配置正确
  - `alembic revision --autogenerate` 可生成迁移
  - `alembic upgrade head` 可执行迁移

### Redis

- [ ] **Redis 连接正常**
  - 可连接到 Redis
  - 连接池配置正确
  - 支持异步操作

- [ ] **缓存工具可用**
  - 缓存装饰器工作正常
  - 过期时间设置正确

### Security

- [ ] **密码加密正确**
  - 使用 bcrypt 算法
  - cost factor >= 12
  - 验证密码功能正常

- [ ] **JWT 功能正常**
  - Token 生成正常
  - Token 验证正常
  - Token 包含正确信息 (user_id, exp)

- [ ] **异常处理正确**
  - 自定义异常类定义
  - 全局异常处理器工作
  - 错误响应格式统一

---

## Phase 2: 用户认证与权限验收

### User Model

- [ ] **User 模型字段完整**
  - id, username, email, hashed_password
  - is_active, is_superuser
  - last_login, created_at, updated_at

- [ ] **User Schema 正确**
  - UserCreate 包含必要字段
  - UserUpdate 字段可选
  - UserResponse 不包含密码

- [ ] **User CRUD 正常**
  - 可创建用户
  - 可查询用户 (by id, by username)
  - 可更新用户
  - 可删除用户

### Role & Permission

- [ ] **Role 模型正确**
  - id, name, description
  - permissions (JSONB)

- [ ] **用户角色关联正确**
  - user_roles 关联表存在
  - 可多对多关联

- [ ] **角色 CRUD 正常**
  - 可创建/查询/更新/删除角色

### Auth API

- [ ] **登录接口正常**
  - POST /api/v1/auth/login
  - 正确用户名密码返回 token
  - 错误密码返回 401

- [ ] **登出接口正常**
  - POST /api/v1/auth/logout
  - Token 失效

- [ ] **刷新 Token 正常**
  - POST /api/v1/auth/refresh
  - 返回新的 access_token

- [ ] **获取当前用户正常**
  - GET /api/v1/auth/me
  - 返回当前登录用户信息

### Auth Dependencies

- [ ] **get_current_user 正常**
  - 从 JWT 解析用户
  - Token 无效返回 401

- [ ] **权限检查正常**
  - @require_permissions 装饰器工作
  - 无权限返回 403

---

## Phase 3: 资产管理验收

### Asset Model

- [ ] **Asset 模型字段完整**
  - asset_id (唯一), name, asset_type, status
  - ip_address, private_ip, mac_address
  - cpu_cores, memory_gb, disk_gb
  - os_type, os_version
  - idc, region, rack
  - labels (JSONB), description
  - owner_id

- [ ] **Label 模型正确**
  - id, name (唯一), color, description

- [ ] **资产标签关联正确**
  - asset_labels 关联表存在
  - 可多对多关联

- [ ] **资产历史记录正确**
  - asset_history 表存在
  - 记录操作类型和变更内容

### Asset API

- [ ] **资产列表接口正常**
  - GET /api/v1/assets
  - 支持分页 (page, page_size)
  - 支持筛选 (type, status, idc, keyword)
  - 支持排序

- [ ] **资产创建接口正常**
  - POST /api/v1/assets
  - 必填字段验证
  - 返回创建的资产

- [ ] **资产详情接口正常**
  - GET /api/v1/assets/{id}
  - 返回完整资产信息

- [ ] **资产更新接口正常**
  - PUT /api/v1/assets/{id}
  - 部分更新支持
  - 记录变更历史

- [ ] **资产删除接口正常**
  - DELETE /api/v1/assets/{id}
  - 软删除或记录删除历史

- [ ] **资产树接口正常**
  - GET /api/v1/assets/tree
  - 按层级组织返回

---

## Phase 4: 运维管理验收

### Deployment

- [ ] **Deployment 模型正确**
  - project_name, version, environment
  - status, deployer, approver
  - deploy_time, duration_seconds
  - log_output, rollback_reason

- [ ] **发布记录 API 正常**
  - 列表、创建、详情、更新接口工作
  - 支持按项目/环境筛选

### Inspection

- [ ] **InspectionTask 模型正确**
  - name, task_type, cron_expression
  - target_assets, check_items
  - is_enabled, last_run_at, next_run_at

- [ ] **InspectionReport 模型正确**
  - task_id, status
  - total_checks, passed_checks, failed_checks, warning_checks
  - summary, details

- [ ] **巡检任务 API 正常**
  - 任务 CRUD 接口工作
  - 报告查询接口工作

### Certificate

- [ ] **Certificate 模型正确**
  - domain, issuer, subject, serial_number
  - valid_from, valid_until, days_until_expiry (自动计算)
  - alert_threshold_days, is_auto_renewal
  - cert_content, key_content, status

- [ ] **证书 API 正常**
  - CRUD 接口工作
  - 到期提醒查询正常

### DNS

- [ ] **DNSRecord 模型正确**
  - domain, record_type, host, value
  - ttl, priority, is_active, provider

- [ ] **DNS API 正常**
  - CRUD 接口工作

---

## Phase 5: 监控告警验收

### Monitor

- [ ] **Monitor 模型正确**
  - name, monitor_type (ping/http/tcp/udp), target
  - interval_seconds, timeout_seconds, retry_count
  - http_method, http_headers, http_body
  - expected_status_code, expected_response_content
  - threshold_warning, threshold_critical
  - is_enabled, current_status, last_check_at, last_check_result

- [ ] **监控项 API 正常**
  - CRUD 接口工作
  - 启停控制正常

### Alert

- [ ] **Alert 模型正确**
  - monitor_id, alert_rule_id
  - severity, status, title, message
  - metric_name, metric_value, threshold_value
  - started_at, acknowledged_at, acknowledged_by
  - resolved_at, resolved_by
  - notification_sent, notification_channels

- [ ] **AlertRule 模型正确**
  - name, description, condition_expression
  - duration_seconds, severity
  - notification_channels, notification_template
  - suppress_interval_minutes, is_enabled

- [ ] **NotificationChannel 模型正确**
  - name, channel_type, config
  - is_enabled, last_test_at, last_test_status

- [ ] **告警 API 正常**
  - 告警列表、确认、解决接口工作
  - 告警规则 CRUD 工作
  - 通知渠道配置工作

---

## Phase 6: 异步任务验收

### Celery

- [ ] **Celery 配置正确**
  - 使用 Redis 作为 Broker 和 Backend
  - Worker 可正常启动
  - Beat 可正常启动

- [ ] **任务定义正确**
  - 资产相关任务
  - 运维相关任务
  - 监控相关任务

### Monitor Tasks

- [ ] **监控检查任务正常**
  - ping 检查可执行
  - http 检查可执行
  - tcp/udp 检查可执行

- [ ] **告警判定逻辑正确**
  - 检查失败触发告警
  - 告警记录创建正确

- [ ] **定时调度正常**
  - 按 interval 执行检查
  - Celery Beat 调度正确

### Inspection Tasks

- [ ] **巡检任务执行正常**
  - 定时触发巡检
  - 报告生成正确

### Notification

- [ ] **邮件通知正常**
  - 邮件可发送
  - 模板渲染正确

- [ ] **通知记录正确**
  - 发送状态记录
  - 失败可重试

---

## Phase 7: 前端验收

### Project Setup

- [ ] **前端项目结构正确**
  - 目录结构符合设计
  - TypeScript 配置正确
  - ESLint + Prettier 配置正确

- [ ] **依赖安装完整**
  - React 18+
  - Ant Design 5.x
  - React Router 6.x
  - Zustand, React Query, Axios

### Components

- [ ] **布局组件正常**
  - Layout 显示正确
  - Header, Sidebar, Content 布局正常
  - 响应式适配

- [ ] **通用组件正常**
  - CommonTable 功能完整
  - CommonForm 功能完整
  - CommonModal 功能完整

### State Management

- [ ] **Auth Store 正常**
  - 登录状态管理
  - Token 持久化

- [ ] **User Store 正常**
  - 用户信息管理

- [ ] **Global Store 正常**
  - 全局状态管理

### API Integration

- [ ] **Axios 配置正确**
  - baseURL 配置
  - 拦截器工作正常
  - Token 自动添加

- [ ] **API 服务正常**
  - 各模块 API 调用正常
  - 错误处理正确

### Pages

- [ ] **登录页面正常**
  - 表单显示正确
  - 登录逻辑正常
  - 路由守卫工作

- [ ] **仪表盘页面正常**
  - 统计显示正确
  - 图表展示正常

- [ ] **资产管理页面正常**
  - 列表页功能完整
  - 创建/编辑功能正常
  - 详情页显示正确
  - 资产树展示正常

- [ ] **运维管理页面正常**
  - 发布记录功能完整
  - 巡检任务功能完整
  - 证书管理功能完整
  - DNS 管理功能完整

- [ ] **监控告警页面正常**
  - 监控项配置完整
  - 告警事件处理正常
  - 告警规则配置正常
  - 通知渠道配置正常

---

## Phase 8: 部署验收

### Docker

- [ ] **后端 Dockerfile 正确**
  - 可构建镜像
  - 多阶段构建优化
  - 非 root 用户运行

- [ ] **前端 Dockerfile 正确**
  - 可构建镜像
  - Nginx 托管正常

- [ ] **Docker Compose 配置正确**
  - 所有服务定义完整
  - 依赖关系正确
  - 网络和卷配置正确

### Nginx

- [ ] **Nginx 配置正确**
  - HTTP 服务正常
  - 前端静态资源服务正常
  - API 反向代理正常
  - gzip 压缩启用

### Deployment

- [ ] **一键部署正常**
  - `docker-compose up -d` 可启动所有服务
  - 服务健康检查通过
  - 日志正常输出

- [ ] **初始化脚本正常**
  - 数据库初始化脚本工作
  - 管理员创建脚本工作

---

## Phase 9: 测试与优化验收

### Backend Tests

- [ ] **单元测试覆盖**
  - Models 测试
  - CRUD 测试
  - Services 测试

- [ ] **API 测试覆盖**
  - 认证 API 测试
  - 资产 API 测试
  - 运维 API 测试
  - 监控 API 测试

### Frontend Tests

- [ ] **组件测试覆盖**
  - 关键组件有测试

### Performance

- [ ] **后端性能达标**
  - API P99 < 200ms
  - 数据库查询 < 50ms

- [ ] **前端性能达标**
  - 首屏加载 < 2s
  - 代码分割生效

---

## Phase 10: 文档验收

### API Documentation

- [ ] **OpenAPI 文档完整**
  - 所有 API 有文档
  - 参数描述清晰
  - 响应示例完整

### Deployment Documentation

- [ ] **部署文档完整**
  - 部署步骤清晰
  - 环境配置说明完整
  - 常见问题处理

### Development Documentation

- [ ] **开发文档完整**
  - 本地开发环境搭建
  - 代码规范说明
  - 架构设计文档

---

## 最终验收标准

### 功能完整性
- [ ] 所有 P0 任务完成
- [ ] 所有 P1 任务完成
- [ ] 核心功能可正常使用

### 性能指标
- [ ] API P99 响应时间 < 200ms
- [ ] 页面首屏加载 < 2s
- [ ] 支持 500+ 并发用户

### 安全性
- [ ] 密码使用 bcrypt 加密
- [ ] JWT Token 有有效期
- [ ] API 有权限校验
- [ ] 敏感配置使用环境变量

### 部署
- [ ] docker-compose up 可一键启动
- [ ] 所有服务健康检查通过
- [ ] 日志正常输出

### 文档
- [ ] API 文档完整
- [ ] 部署文档完整
- [ ] 开发文档完整

---

**检查清单结束**
