# OpsManager

现代化的运维管理平台 - 基于 FastAPI + React

## 技术栈

### 后端

- **FastAPI 0.104+** - 现代 Python Web 框架
- **SQLAlchemy 2.0** - ORM 框架
- **PostgreSQL 15** - 主数据库
- **Redis 7** - 缓存和消息队列
- **Celery 5.3+** - 异步任务和定时任务
- **JWT** - 身份认证
- **Alembic** - 数据库迁移

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

### 3. 监控告警

- 监控项配置（Ping、HTTP、TCP、UDP）
- 告警事件管理
- 告警规则配置
- 通知渠道配置（邮件、Webhook）

### 4. 权限管理

- RBAC 权限模型
- 用户管理
- 角色管理
- JWT 认证

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

1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的环境变量
```

1. 启动服务

```bash
docker-compose up -d
```

1. 访问系统

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

1. 安装依赖

```bash
pip install -r requirements/dev.txt
```

1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

1. 运行数据库迁移

```bash
alembic upgrade head
```

1. 启动开发服务器

```bash
uvicorn app.main:app --reload
```

#### 前端开发

1. 安装依赖

```bash
cd frontend
npm install
```

1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

1. 启动开发服务器

```bash
npm run dev
```

## 项目结构

```
ops-manager/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心模块
│   │   ├── crud/           # 数据库操作
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic 模型
│   │   ├── services/       # 业务逻辑
│   │   ├── tasks/          # Celery 任务
│   │   └── main.py         # 应用入口
│   ├── alembic/            # 数据库迁移
│   ├── requirements/       # 依赖管理
│   └── Dockerfile
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── components/     # 组件
│   │   ├── pages/          # 页面
│   │   ├── services/       # API 服务
│   │   ├── stores/         # 状态管理
│   │   └── types/          # TypeScript 类型
│   └── Dockerfile
├── nginx/                  # Nginx 配置
├── docker-compose.yml
└── README.md
```

## API 文档

启动服务后，访问以下地址查看 API 文档：

- Swagger UI: <http://localhost:8080/docs>
- ReDoc: <http://localhost:8080/redoc>

## 数据库模型

### 核心表

- `users` - 用户表
- `roles` - 角色表
- `assets` - 资产表
- `labels` - 标签表
- `monitors` - 监控项表
- `alerts` - 告警表
- `deployments` - 发布记录表
- `certificates` - 证书表
- `dns_records` - DNS 记录表

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

