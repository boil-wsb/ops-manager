# OpsManager V2 重构规范文档

## 变更标识
- **change-id**: refactor-opsmanager-v2
- **版本**: v1.0.0
- **创建日期**: 2026-03-11

---

## 1. Why (重构原因)

原有 Django 运维管理平台存在以下问题，需要进行完全重构：

1. **技术债务严重**: Django 1.11 已停止维护，Python 3.6 无法使用现代语言特性
2. **前端过时**: Layui 框架用户体验差，维护困难
3. **架构混乱**: 缺乏清晰的分层设计，代码耦合严重
4. **安全隐患**: 硬编码密钥、DEBUG 模式开启等安全问题
5. **功能冗余**: 包含大量未使用或低频使用的功能模块

---

## 2. What Changes (变更内容)

### 2.1 技术栈升级

| 层级 | 旧技术栈 | 新技术栈 |
|------|----------|----------|
| 后端框架 | Django 1.11 | FastAPI 0.104+ |
| Python 版本 | 3.6.8 | 3.12+ |
| ORM | Django ORM | SQLAlchemy 2.0 |
| 前端框架 | Layui | React 18 + TypeScript |
| 数据库 | MySQL 5.7 | PostgreSQL 15 |
| 缓存 | 无 | Redis 7 |
| 部署 | 手动部署 | Docker Compose |

### 2.2 功能范围调整

**保留的核心功能**:
- 资产管理 (IDC/虚拟机/网络设备)
- 运维管理 (发布记录/巡检任务/证书/DNS)
- 监控告警 (监控项/告警规则/通知)

**去除的功能**:
- ClickHouse 时序数据库
- 阿里云 SDK 集成
- 企业微信集成
- Prometheus/Grafana 监控栈
- 日志监控层

### 2.3 架构变化

**BREAKING**: 从单体 Django 应用改为前后端分离架构
- 后端: FastAPI 提供 RESTful API
- 前端: React SPA 独立部署
- 通信: HTTP API + JWT 认证

---

## 3. Impact (影响范围)

### 3.1 受影响的能力
- 用户认证与授权 (RBAC 模型)
- 资产的 CRUD 操作
- 运维任务管理
- 监控告警配置

### 3.2 受影响的系统
- 后端 API 服务 (全新开发)
- 前端 Web 应用 (全新开发)
- 数据库 (从 MySQL 迁移到 PostgreSQL)
- 部署方式 (改为容器化)

### 3.3 数据迁移
**注意**: 本次重构不考虑旧项目数据迁移，作为全新系统部署。

---

## 4. ADDED Requirements (新增需求)

### 4.1 Requirement: 后端基础架构

**描述**: 搭建 FastAPI 后端基础框架

#### Scenario: 项目初始化
- **GIVEN** 空项目目录
- **WHEN** 执行初始化命令
- **THEN** 创建完整的后端项目结构
- **AND** 包含配置管理、数据库连接、日志等基础组件

#### Scenario: 数据库连接
- **GIVEN** 正确的数据库配置
- **WHEN** 启动应用
- **THEN** 成功连接到 PostgreSQL 数据库
- **AND** 支持连接池和自动重连

#### Scenario: 健康检查
- **GIVEN** 应用已启动
- **WHEN** 访问 /health 端点
- **THEN** 返回数据库和 Redis 连接状态

### 4.2 Requirement: 用户认证系统

**描述**: 实现基于 JWT 的用户认证系统

#### Scenario: 用户登录
- **GIVEN** 已注册的用户账号
- **WHEN** 提交正确的用户名和密码
- **THEN** 返回 access_token 和 refresh_token
- **AND** token 包含用户ID和角色信息

#### Scenario: Token 刷新
- **GIVEN** 有效的 refresh_token
- **WHEN** 调用刷新接口
- **THEN** 返回新的 access_token
- **AND** 旧 token 失效

#### Scenario: 密码安全
- **GIVEN** 用户注册或修改密码
- **WHEN** 密码长度 >= 8 且包含大小写字母、数字、特殊字符
- **THEN** 使用 bcrypt 加密存储
- **AND** 原始密码不存储在任何位置

### 4.3 Requirement: RBAC 权限系统

**描述**: 实现基于角色的访问控制

#### Scenario: 角色管理
- **GIVEN** 管理员身份
- **WHEN** 创建/编辑/删除角色
- **THEN** 角色信息保存到数据库
- **AND** 支持配置权限列表

#### Scenario: 权限校验
- **GIVEN** 用户已登录
- **WHEN** 访问受保护的 API
- **THEN** 系统检查用户角色权限
- **AND** 无权限时返回 403 Forbidden

### 4.4 Requirement: 资产管理模块

**描述**: 实现资产的全生命周期管理

#### Scenario: 资产 CRUD
- **GIVEN** 用户有 asset:write 权限
- **WHEN** 创建/更新/删除资产
- **THEN** 数据保存到 assets 表
- **AND** 记录操作日志到 asset_history 表

#### Scenario: 资产查询
- **GIVEN** 用户有 asset:read 权限
- **WHEN** 查询资产列表
- **THEN** 支持分页、筛选、排序
- **AND** 支持按类型、状态、IDC、标签筛选

#### Scenario: 资产树形结构
- **GIVEN** 存在多级资产关系
- **WHEN** 获取资产树
- **THEN** 返回层级结构的资产数据

### 4.5 Requirement: 运维管理模块

**描述**: 实现发布记录、巡检任务、证书、DNS 管理

#### Scenario: 发布记录管理
- **GIVEN** 用户有 deploy:write 权限
- **WHEN** 创建发布记录
- **THEN** 保存项目名、版本、环境、状态等信息
- **AND** 支持查看历史发布记录

#### Scenario: 巡检任务
- **GIVEN** 用户有 inspection:write 权限
- **WHEN** 创建定时巡检任务
- **THEN** 使用 Celery Beat 调度执行
- **AND** 生成巡检报告保存到 inspection_reports 表

#### Scenario: 证书到期提醒
- **GIVEN** 存在证书记录
- **WHEN** 证书即将过期 (默认30天内)
- **THEN** 系统生成告警通知
- **AND** 可通过配置调整提醒阈值

### 4.6 Requirement: 监控告警模块

**描述**: 实现监控项配置和告警管理

#### Scenario: 监控项配置
- **GIVEN** 用户有 monitor:write 权限
- **WHEN** 创建监控项
- **THEN** 支持 ping、http、tcp、udp 类型
- **AND** 可配置检查间隔、超时、重试次数

#### Scenario: 告警触发
- **GIVEN** 监控项检查失败
- **WHEN** 达到告警阈值
- **THEN** 创建告警记录到 alerts 表
- **AND** 根据配置发送通知

#### Scenario: 告警处理
- **GIVEN** 存在未处理告警
- **WHEN** 用户确认或解决告警
- **THEN** 更新告警状态
- **AND** 记录处理人和时间

### 4.7 Requirement: 异步任务系统

**描述**: 使用 Celery 处理异步和定时任务

#### Scenario: 异步任务执行
- **GIVEN** 触发异步操作 (如批量资产导入)
- **WHEN** 任务提交到 Celery
- **THEN** Worker 异步执行任务
- **AND** 支持查看任务状态

#### Scenario: 定时任务调度
- **GIVEN** 配置了定时任务
- **WHEN** 到达执行时间
- **THEN** Celery Beat 触发任务
- **AND** 任务执行结果记录到数据库

### 4.8 Requirement: 前端基础架构

**描述**: 搭建 React + TypeScript 前端项目

#### Scenario: 项目初始化
- **GIVEN** 空项目目录
- **WHEN** 执行初始化命令
- **THEN** 创建完整的 React + Vite 项目结构
- **AND** 配置 TypeScript、ESLint、Prettier

#### Scenario: 路由配置
- **GIVEN** 前端项目已初始化
- **WHEN** 配置路由
- **THEN** 支持登录页、仪表盘、各功能模块页面
- **AND** 实现路由守卫，未登录跳转登录页

#### Scenario: 状态管理
- **GIVEN** 用户已登录
- **WHEN** 使用 Zustand 管理状态
- **THEN** 全局存储用户信息、权限
- **AND** 支持持久化存储

### 4.9 Requirement: 前端页面开发

**描述**: 实现各功能模块的前端页面

#### Scenario: 登录页面
- **GIVEN** 用户访问系统
- **WHEN** 未登录时
- **THEN** 显示登录表单
- **AND** 登录成功后跳转到仪表盘

#### Scenario: 资产列表页
- **GIVEN** 用户已登录且有权限
- **WHEN** 访问资产管理页面
- **THEN** 显示资产表格
- **AND** 支持搜索、筛选、分页、导出

#### Scenario: 资产详情/编辑页
- **GIVEN** 用户在资产列表页
- **WHEN** 点击资产名称或编辑按钮
- **THEN** 显示资产详情或编辑表单
- **AND** 支持修改资产信息

### 4.10 Requirement: 容器化部署

**描述**: 使用 Docker Compose 实现一键部署

#### Scenario: 本地开发部署
- **GIVEN** 已安装 Docker 和 Docker Compose
- **WHEN** 执行 docker-compose up
- **THEN** 启动所有服务 (PostgreSQL、Redis、Backend、Frontend、Nginx)
- **AND** 服务之间网络互通

#### Scenario: 生产部署
- **GIVEN** 生产环境服务器
- **WHEN** 配置环境变量并执行部署脚本
- **THEN** 应用以生产模式运行
- **AND** Nginx 作为反向代理

---

## 5. MODIFIED Requirements (修改需求)

无 - 本次为全新项目，不涉及现有功能修改。

---

## 6. REMOVED Requirements (移除需求)

### 6.1 Requirement: 旧 Django 项目功能
**原因**: 完全重写，旧项目不再维护
**迁移**: 作为独立系统运行，数据不迁移

### 6.2 Requirement: ClickHouse 集成
**原因**: 简化架构，当前数据量不需要时序数据库
**迁移**: 监控数据存储在 PostgreSQL

### 6.3 Requirement: 阿里云 SDK 集成
**原因**: 简化外部依赖
**迁移**: 如需云服务管理，后续单独开发

### 6.4 Requirement: 企业微信集成
**原因**: 简化通知渠道
**迁移**: 仅保留邮件通知，其他渠道后续按需添加

### 6.5 Requirement: Prometheus/Grafana
**原因**: 简化监控栈
**迁移**: 使用自建监控模块

---

## 7. 技术规范

### 7.1 后端规范

**代码风格**:
- 遵循 PEP 8
- 使用 Black 格式化 (line-length: 100)
- 使用 Ruff 进行代码检查

**项目结构**:
```
backend/
├── app/
│   ├── api/          # API 路由
│   ├── core/         # 核心模块 (安全、配置、异常)
│   ├── models/       # SQLAlchemy 模型
│   ├── schemas/      # Pydantic 模型
│   ├── services/     # 业务逻辑
│   ├── crud/         # 数据库操作
│   ├── db/           # 数据库配置
│   ├── tasks/        # Celery 任务
│   └── utils/        # 工具函数
├── alembic/          # 数据库迁移
└── tests/            # 测试
```

**API 规范**:
- RESTful 设计
- 统一响应格式: `{"code": 0, "message": "", "data": {}}`
- 使用 HTTP 状态码表示结果
- JWT Token 放在 Authorization Header

### 7.2 前端规范

**代码风格**:
- TypeScript 严格模式
- ESLint + Prettier
- 组件使用函数式 + Hooks

**项目结构**:
```
frontend/src/
├── components/       # 公共组件
├── pages/           # 页面组件
├── hooks/           # 自定义 Hooks
├── stores/          # Zustand 状态
├── services/        # API 服务
├── utils/           # 工具函数
└── types/           # TypeScript 类型
```

### 7.3 Git 规范

**分支策略**:
- main: 生产分支
- develop: 开发分支
- feature/*: 功能分支
- hotfix/*: 紧急修复

**提交规范** (Conventional Commits):
```
feat: 新增功能
fix: 修复 bug
docs: 文档更新
style: 代码格式
refactor: 重构
test: 测试
chore: 构建/工具
```

---

## 8. 验收标准

### 8.1 功能验收
- [ ] 用户可正常登录/登出
- [ ] 可创建/编辑/删除资产
- [ ] 可创建发布记录
- [ ] 可配置巡检任务并生成报告
- [ ] 可配置监控项和告警规则
- [ ] 告警可正常触发和通知

### 8.2 性能验收
- [ ] API P99 响应时间 < 200ms
- [ ] 页面首屏加载 < 2s
- [ ] 支持 500+ 并发用户

### 8.3 安全验收
- [ ] 密码使用 bcrypt 加密
- [ ] JWT Token 有有效期
- [ ] API 有权限校验
- [ ] 敏感配置使用环境变量

### 8.4 部署验收
- [ ] docker-compose up 可一键启动
- [ ] 所有服务健康检查通过
- [ ] 日志正常输出

---

## 9. 附录

### 9.1 参考文档
- [architecture-design.md](../../docs/design/architecture-design.md) - 架构设计文档

### 9.2 术语表
| 术语 | 说明 |
|------|------|
| RBAC | 基于角色的访问控制 |
| JWT | JSON Web Token |
| ORM | 对象关系映射 |
| CRUD | 增删改查 |

---

**文档结束**
