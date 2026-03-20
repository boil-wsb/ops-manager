# OpsManager V2 项目优化方案

## 目标
对项目进行全面优化，解决结构、依赖、安全和架构问题。

## 项目概述
- **后端**: FastAPI + PostgreSQL + Redis + Celery
- **前端**: React 19 + Ant Design 6 + TanStack Query + Zustand
- **部署**: Docker Compose + Nginx

---

## 第一阶段：问题清理 (P1 - 高优先级)

### 1.1 清理重复 Migration 文件
**问题**: `backend/alembic/versions/` 存在重复 migration
- `20260319_0904_be2745244769_add_client_ip_to_it_feedback.py`
- `20260319_1413_bf7b8f22ad21_add_owner_name_to_asset.py`
- `20260319_1421_9370668b55fe_add_owner_name_to_asset.py`

**操作**:
1. 检查 migration 顺序和依赖关系
2. 删除已被后续 migration 覆盖的重复文件
3. 保留包含最新 schema 状态的 migration

**预期结果**: 只保留必要的 migration 文件

### 1.2 清理重复 Prometheus 同步模块
**问题**: `app/services/prometheus/` 存在重复文件
- `asset_sync.py`
- `asset_sync_optimized.py`

**操作**:
1. 确定哪个是当前使用的版本
2. 删除废弃版本
3. 统一使用一个文件

**预期结果**: 只保留一个同步模块

### 1.3 清理测试脚本
**问题**: `backend/scripts/test_*.py` 散落大量测试脚本

**操作**:
1. 创建 `backend/tests/` 目录
2. 将相关测试脚本移动到 `tests/`
3. 无效脚本标记为废弃或删除

**预期结果**: 测试代码统一管理

---

## 第二阶段：依赖升级 (P1 - 高优先级)

### 2.1 后端依赖升级
**当前版本**:
- `pydantic==2.5.0` → 升级到 `2.10.5`
- `pydantic-settings==2.1.0` → 升级到 `2.7.1`
- `fastapi==0.104.1` → 升级到 `0.115.12`
- `uvicorn[standard]==0.24.0` → 升级到 `0.34.0`

**操作**:
1. 更新 `backend/requirements/base.txt`
2. 运行 `pip install -r requirements/base.txt`
3. 验证应用启动

**风险**: 需要测试 Pydantic v2.10 兼容性

### 2.2 前端依赖升级
**当前版本**:
- `antd@6.3.2` → 升级到 `6.7.8`
- `@tanstack/react-query@5.90.21` → 升级到 `5.67.3`
- `react@19.2.0` → 保持 (最新)
- `zustand@5.0.11` → 升级到 `5.0.3`

**操作**:
1. 更新 `frontend/package.json`
2. 运行 `npm install`
3. 验证构建

### 2.3 添加缺失依赖
**后端**:
- `pytest==8.3.5`
- `pytest-asyncio==0.25.2`
- `httpx` (已有)

**前端**:
- `eslint-config-prettier`
- `@types/axios`

---

## 第三阶段：安全加固 (P1 - 高优先级)

### 3.1 API 限流中间件
**操作**:
1. 安装 `slowapi==0.1.9`
2. 在 `app/core/middleware.py` 添加限流逻辑
3. 配置默认限流规则 (100req/min)
4. 对登录接口单独限流 (5req/min)

**预期结果**: 防止暴力破解和 DDoS

### 3.2 密钥配置强化
**问题**: `config.py` 中 `secret_key` 有默认值

**操作**:
1. 检查环境变量是否设置 `SECRET_KEY`
2. 如果未设置，抛出异常而非使用默认值
3. 在 `.env.example` 中添加明确注释

### 3.3 CORS 配置优化
**问题**: CORS 配置可能过于宽松

**操作**:
1. 在生产环境明确指定允许的域名
2. 添加环境变量 `CORS_ALLOWED_ORIGINS`
3. 开发环境使用 `localhost`，生产环境使用正式域名

---

## 第四阶段：代码质量 (P2 - 中优先级)

### 4.1 前端 TypeScript 问题修复

#### 4.1.1 修复未使用导入 (TS6133)
**操作**:
1. 运行 `npm run lint` 检查所有文件
2. 修复 `AssetDiscovery.tsx` 中的导入问题
3. 确保所有导入都被使用

#### 4.1.2 修复类型断言 (TS1484)
**问题**: Ant Design Menu items 需要类型断言

**操作**:
1. 检查 `Layout.tsx` 中的 Menu items
2. 添加 `items={items as MenuProps['items']}`

#### 4.1.3 修复命名问题 (TS2551)
**问题**: API 返回 snake_case 但前端期望 camelCase

**操作**:
1. 统一在 service 层进行转换
2. 检查 `utils/transform.ts` 是否被使用

### 4.2 后端代码组织

#### 4.2.1 统一错误处理
**操作**:
1. 创建 `app/core/exceptions.py`
2. 定义 `AppException` 基类
3. 为每种错误类型创建具体异常
4. 添加全局异常处理中间件

#### 4.2.2 目录结构优化
**操作**:
1. 将 `services/prometheus.py` 合并到 `services/prometheus/__init__.py`
2. 确保 `core/permissions.py` 重命名或合并到 `authorization`

---

## 第五阶段：测试与 CI/CD (P2 - 中优先级)

### 5.1 建立测试框架
**操作**:
1. 创建 `backend/tests/` 目录结构
2. 添加 `conftest.py` 配置 pytest-asyncio
3. 创建基础测试用例
4. 配置 GitHub/GitLab CI

### 5.2 CI/CD 改进
**当前 .gitlab-ci.yml 需要添加**:
```yaml
test:
  script:
    - pytest tests/ --cov=app --cov-report=xml
  coverage: '/(?i)total.*\s(\d+\.\d+\%)/'

security:
  script:
    - safety check
    - bandit -r app/
```

---

## 第六阶段：架构优化 (P3 - 低优先级)

### 6.1 前端目录重构
**建议结构**:
```
frontend/src/pages/
├── Assets/
│   ├── components/     # 资产相关子组件
│   ├── AssetList.tsx
│   ├── AssetDetail.tsx
│   └── AssetDiscovery.tsx
└── Dashboard/
    └── index.tsx      # 仪表盘组件
```

### 6.2 添加 i18n 支持
**操作**:
1. 安装 `react-i18next` 和 `i18next`
2. 创建 `src/locales/` 目录
3. 提取中文文本到翻译文件

---

## 执行顺序

| 阶段 | 任务 | 优先级 | 风险 |
|-----|------|--------|------|
| 1.1 | 清理重复 Migration | P1 | 中 |
| 1.2 | 清理重复 Prometheus 模块 | P1 | 低 |
| 1.3 | 整理测试脚本 | P1 | 低 |
| 2.1 | 升级后端依赖 | P1 | 中 |
| 2.2 | 升级前端依赖 | P1 | 中 |
| 3.1 | 添加 API 限流 | P1 | 低 |
| 3.2 | 密钥配置强化 | P1 | 低 |
| 3.3 | CORS 配置优化 | P1 | 低 |
| 4.1 | 前端 TS 问题修复 | P2 | 低 |
| 4.2 | 后端代码组织 | P2 | 低 |
| 5.1 | 建立测试框架 | P2 | 中 |
| 5.2 | CI/CD 改进 | P2 | 低 |
| 6.1 | 前端目录重构 | P3 | 中 |
| 6.2 | 添加 i18n | P3 | 中 |

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| Pydantic 升级破坏性变更 | 高 | 先在测试环境验证 |
| Ant Design 升级 API 变化 | 中 | 查阅 CHANGELOG |
| Migration 删除导致数据丢失 | 高 | 先备份数据库 |
| 前端重构影响现有功能 | 中 | 保持路由兼容 |

---

## 成功标准

1. ✅ 所有重复文件清理完成
2. ✅ 依赖版本升级到最新稳定版
3. ✅ API 限流正常工作
4. ✅ TypeScript 编译无错误
5. ✅ Lint 检查通过
6. ✅ 测试覆盖率 > 80%