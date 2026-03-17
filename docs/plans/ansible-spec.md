# Ansible 集成实施规范

## 项目概述

### 项目名称
OpsManager Ansible 集成模块

### 项目目标
将 Ansible 自动化运维能力集成到 OpsManager 平台，实现对网内设备的统一管理，支持手动触发和定时调度两种执行模式。

### 技术栈
- **后端**: FastAPI + SQLAlchemy + Celery
- **前端**: React + TypeScript + Ant Design
- **数据库**: PostgreSQL 15
- **消息队列**: Redis 7
- **自动化引擎**: Ansible Core

---

## 功能规范

### 1. 凭证管理模块

#### 1.1 功能描述
管理 Ansible 连接设备所需的认证信息，支持 SSH 密钥、SSH 密码、WinRM 三种认证方式。

#### 1.2 数据模型

```python
class CredentialType(str, Enum):
    SSH_KEY = "SSH_KEY"           # SSH 密钥认证
    SSH_PASSWORD = "SSH_PASSWORD" # SSH 密码认证
    WINRM = "WINRM"               # Windows WinRM 认证

class WinRMTransport(str, Enum):
    NTLM = "NTLM"
    KERBEROS = "KERBEROS"
    BASIC = "BASIC"
```

#### 1.3 API 规范

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | /api/v1/ansible/credentials | 创建凭证 | ansible:credential:write |
| GET | /api/v1/ansible/credentials | 获取凭证列表 | ansible:credential:read |
| GET | /api/v1/ansible/credentials/{id} | 获取凭证详情 | ansible:credential:read |
| PUT | /api/v1/ansible/credentials/{id} | 更新凭证 | ansible:credential:write |
| DELETE | /api/v1/ansible/credentials/{id} | 删除凭证 | ansible:credential:delete |
| POST | /api/v1/ansible/credentials/{id}/test | 测试凭证连接 | ansible:credential:read |

#### 1.4 安全要求
- 所有敏感字段（password, private_key, passphrase）必须使用 AES-256 加密存储
- 加密密钥从环境变量 `ANSIBLE_MASTER_KEY` 获取
- API 返回时敏感字段必须脱敏（显示为 `******`）
- 凭证测试时生成的临时文件必须在测试完成后立即删除

#### 1.5 验证规则
- `name`: 必填，最大 100 字符，同一用户下唯一
- `username`: 必填，最大 100 字符
- `cred_type`: 必填，枚举值
- SSH_KEY 类型必须提供 `private_key`
- SSH_PASSWORD 类型必须提供 `password`
- WINRM 类型必须提供 `winrm_transport`

---

### 2. Playbook 管理模块

#### 2.1 功能描述
管理 Ansible Playbook，支持数据库存储和文件系统挂载两种来源。

#### 2.2 数据模型

```python
class PlaybookCategory(str, Enum):
    SYSTEM = "SYSTEM"     # 系统管理
    NETWORK = "NETWORK"   # 网络配置
    DEPLOY = "DEPLOY"     # 应用部署
    CUSTOM = "CUSTOM"     # 自定义

class PlaybookSourceType(str, Enum):
    DATABASE = "DATABASE"       # 存储在数据库
    FILESYSTEM = "FILESYSTEM"   # 挂载自文件系统
```

#### 2.3 API 规范

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | /api/v1/ansible/playbooks | 创建 Playbook | ansible:playbook:write |
| GET | /api/v1/ansible/playbooks | 获取 Playbook 列表 | ansible:playbook:read |
| GET | /api/v1/ansible/playbooks/{id} | 获取 Playbook 详情 | ansible:playbook:read |
| PUT | /api/v1/ansible/playbooks/{id} | 更新 Playbook | ansible:playbook:write |
| DELETE | /api/v1/ansible/playbooks/{id} | 删除 Playbook | ansible:playbook:delete |
| POST | /api/v1/ansible/playbooks/import | 导入文件系统 Playbook | ansible:playbook:write |
| POST | /api/v1/ansible/playbooks/{id}/validate | 验证 Playbook 语法 | ansible:playbook:read |

#### 2.4 验证规则
- `name`: 必填，最大 200 字符
- `category`: 必填，枚举值
- `source_type`: 必填，枚举值
- DATABASE 类型必须提供 `content`
- FILESYSTEM 类型必须提供有效的 `file_path`
- `is_builtin=True` 的 Playbook 不允许删除

#### 2.5 Playbook 内容验证
- 使用 `ansible-playbook --syntax-check` 验证语法
- 验证失败返回详细错误信息

---

### 3. Inventory 管理模块

#### 3.1 功能描述
管理静态 Inventory 文件，支持从文件系统扫描和导入。

#### 3.2 数据模型

```python
class InventoryFile(Base):
    id: UUID
    name: str                    # 显示名称
    file_path: str               # 文件路径
    environment: str | None      # 环境标识
    description: str | None
    is_active: bool
```

#### 3.3 API 规范

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | /api/v1/ansible/inventories | 获取 Inventory 列表 | ansible:job:read |
| GET | /api/v1/ansible/inventories/{id} | 获取 Inventory 详情 | ansible:job:read |
| POST | /api/v1/ansible/inventories/scan | 扫描文件系统 Inventory | ansible:job:read |
| GET | /api/v1/ansible/inventories/{id}/hosts | 获取 Inventory 主机列表 | ansible:job:read |
| POST | /api/v1/ansible/inventories/{id}/test | 测试 Inventory 连接 | ansible:job:read |

#### 3.4 Inventory 扫描规则
- 扫描目录：`/app/ansible/inventory/`
- 识别文件：`hosts`, `host.ini`, `*.ini`, `*.yml`, `*.yaml`
- 自动识别环境：根据目录名（dev, qa, ops, windows, all）

---

### 4. 任务执行模块

#### 4.1 功能描述
执行 Ansible 任务，支持 Playbook 执行和 Ad-hoc 命令，提供实时输出。

#### 4.2 数据模型

```python
class JobType(str, Enum):
    PLAYBOOK = "PLAYBOOK"
    AD_HOC = "AD_HOC"

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
```

#### 4.3 API 规范

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | /api/v1/ansible/jobs | 创建并执行任务 | ansible:job:execute |
| GET | /api/v1/ansible/jobs | 获取任务列表 | ansible:job:read |
| GET | /api/v1/ansible/jobs/{id} | 获取任务详情 | ansible:job:read |
| POST | /api/v1/ansible/jobs/{id}/cancel | 取消任务 | ansible:job:cancel |
| POST | /api/v1/ansible/jobs/{id}/retry | 重试任务 | ansible:job:execute |
| GET | /api/v1/ansible/jobs/{id}/results | 获取任务结果 | ansible:job:read |
| WS | /api/v1/ansible/jobs/{id}/ws | 实时任务输出 | ansible:job:read |

#### 4.4 任务执行流程

```
1. 接收请求 → 验证权限 → 创建任务记录 (PENDING)
2. 发送任务到 Celery 队列 → 返回 Job ID
3. Celery Worker 接收任务 → 更新状态 (RUNNING)
4. 准备执行环境：
   - 解密凭证
   - 写入临时密钥文件
   - 构建 ansible-playbook 命令
5. 执行命令 → 实时推送输出到 WebSocket
6. 解析结果 → 写入数据库 → 更新状态 (SUCCESS/FAILED)
7. 清理临时文件
```

#### 4.5 执行参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| forks | int | 5 | 并发数 |
| timeout | int | 3600 | 超时时间（秒） |
| limit_pattern | str | None | 限制主机模式 |
| tags | str | None | 执行标签 |
| skip_tags | str | None | 跳过标签 |
| extra_vars | dict | {} | 额外变量 |

---

### 5. 定时任务模块

#### 5.1 功能描述
管理 Ansible 定时任务，支持 Cron 表达式调度。

#### 5.2 API 规范

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | /api/v1/ansible/schedules | 创建定时任务 | ansible:schedule:write |
| GET | /api/v1/ansible/schedules | 获取定时任务列表 | ansible:schedule:read |
| GET | /api/v1/ansible/schedules/{id} | 获取定时任务详情 | ansible:schedule:read |
| PUT | /api/v1/ansible/schedules/{id} | 更新定时任务 | ansible:schedule:write |
| DELETE | /api/v1/ansible/schedules/{id} | 删除定时任务 | ansible:schedule:delete |
| POST | /api/v1/ansible/schedules/{id}/toggle | 启用/禁用定时任务 | ansible:schedule:write |
| POST | /api/v1/ansible/schedules/{id}/run | 手动触发定时任务 | ansible:schedule:write |

#### 5.3 Cron 表达式验证
- 支持标准 5 字段 Cron 表达式
- 使用 `croniter` 库验证和计算下次执行时间

---

### 6. Ad-hoc 命令模块

#### 6.1 功能描述
执行 Ansible Ad-hoc 命令，快速执行单个模块。

#### 6.2 API 规范

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | /api/v1/ansible/ad-hoc | 执行 Ad-hoc 命令 | ansible:ad-hoc:execute |
| GET | /api/v1/ansible/modules | 获取可用模块列表 | ansible:ad-hoc:execute |
| GET | /api/v1/ansible/modules/{name}/docs | 获取模块文档 | ansible:ad-hoc:execute |

#### 6.3 常用模块白名单

```python
ALLOWED_MODULES = [
    # 命令执行
    "command", "shell", "raw", "script",
    # 文件操作
    "copy", "file", "template", "fetch", "synchronize",
    # 包管理
    "apt", "yum", "dnf", "pip", "npm",
    # 服务管理
    "service", "systemd", "supervisorctl",
    # 用户管理
    "user", "group",
    # 网络配置
    "hostname", "iptables", "firewalld",
    # 系统信息
    "setup", "debug", "assert", "wait_for",
    # Windows
    "win_command", "win_shell", "win_copy", "win_file",
    "win_service", "win_user", "win_feature",
]
```

---

## 技术规范

### 1. 代码结构

```
backend/
├── app/
│   ├── api/v1/
│   │   └── ansible.py              # Ansible API 路由
│   ├── models/
│   │   └── ansible.py              # Ansible 数据模型
│   ├── schemas/
│   │   └── ansible.py              # Ansible Pydantic 模型
│   ├── crud/
│   │   └── ansible.py              # Ansible CRUD 操作
│   ├── services/
│   │   └── ansible/
│   │       ├── __init__.py
│   │       ├── executor.py         # 任务执行器
│   │       ├── encryption.py       # 凭证加密
│   │       ├── inventory.py        # Inventory 解析
│   │       └── output.py           # 输出处理
│   └── tasks/
│       └── ansible/
│           ├── __init__.py
│           ├── executor.py         # Celery 任务
│           └── scheduler.py        # 定时调度
```

### 2. 数据库迁移

```bash
# 创建迁移文件
alembic revision --autogenerate -m "add ansible tables"

# 执行迁移
alembic upgrade head
```

### 3. 凭证加密实现

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class CredentialEncryption:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        master_key = os.environ.get('ANSIBLE_MASTER_KEY', '').encode()
        if not master_key:
            raise ValueError("ANSIBLE_MASTER_KEY environment variable not set")
        
        salt = b'ops-manager-ansible-salt-v1'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key))
        self.fernet = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        return self.fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        return self.fernet.decrypt(ciphertext.encode()).decode()
```

### 4. WebSocket 实时输出

```python
from fastapi import WebSocket, WebSocketDisconnect
from app.core.redis import get_redis
import asyncio

async def job_output_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    redis = get_redis()
    pubsub = redis.pubsub()
    pubsub.subscribe(f'ansible:job:{job_id}:output')
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                await websocket.send_text(message['data'].decode())
    except WebSocketDisconnect:
        pass
    finally:
        pubsub.unsubscribe(f'ansible:job:{job_id}:output')
```

### 5. Celery 任务配置

```python
from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    'ops_manager',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=7200,  # 2小时硬限制
    task_soft_time_limit=3600,  # 1小时软限制
)

celery_app.conf.beat_schedule = {
    'schedule-ansible-jobs': {
        'task': 'app.tasks.ansible.scheduler.check_scheduled_jobs',
        'schedule': 60.0,  # 每分钟检查
    },
    'cleanup-old-results': {
        'task': 'app.tasks.ansible.cleanup.cleanup_old_results',
        'schedule': crontab(hour=3, minute=0),  # 每天凌晨3点
    },
}
```

---

## 前端规范

### 1. 页面结构

```
frontend/src/pages/Ansible/
├── Credentials/
│   ├── CredentialList.tsx
│   ├── CredentialForm.tsx
│   └── CredentialTest.tsx
├── Playbooks/
│   ├── PlaybookList.tsx
│   ├── PlaybookEditor.tsx
│   └── PlaybookImport.tsx
├── Inventories/
│   ├── InventoryList.tsx
│   └── InventoryDetail.tsx
├── Jobs/
│   ├── JobList.tsx
│   ├── JobDetail.tsx
│   ├── JobOutput.tsx
│   └── JobCreate.tsx
├── Schedules/
│   ├── ScheduleList.tsx
│   └── ScheduleForm.tsx
└── AdHoc/
    ├── AdHocExecute.tsx
    └── ModuleDocs.tsx
```

### 2. 组件规范

- 使用 Ant Design 组件库
- 使用 React Query 进行数据获取
- 使用 Zustand 进行状态管理
- 使用 Monaco Editor 进行 Playbook 编辑

### 3. API 服务

```typescript
// frontend/src/services/ansible.ts
import { api } from './api';

export const ansibleApi = {
  credentials: {
    list: (params) => api.get('/ansible/credentials', { params }),
    get: (id) => api.get(`/ansible/credentials/${id}`),
    create: (data) => api.post('/ansible/credentials', data),
    update: (id, data) => api.put(`/ansible/credentials/${id}`, data),
    delete: (id) => api.delete(`/ansible/credentials/${id}`),
    test: (id) => api.post(`/ansible/credentials/${id}/test`),
  },
  playbooks: {
    list: (params) => api.get('/ansible/playbooks', { params }),
    get: (id) => api.get(`/ansible/playbooks/${id}`),
    create: (data) => api.post('/ansible/playbooks', data),
    update: (id, data) => api.put(`/ansible/playbooks/${id}`, data),
    delete: (id) => api.delete(`/ansible/playbooks/${id}`),
    validate: (id) => api.post(`/ansible/playbooks/${id}/validate`),
    import: () => api.post('/ansible/playbooks/import'),
  },
  jobs: {
    list: (params) => api.get('/ansible/jobs', { params }),
    get: (id) => api.get(`/ansible/jobs/${id}`),
    create: (data) => api.post('/ansible/jobs', data),
    cancel: (id) => api.post(`/ansible/jobs/${id}/cancel`),
    retry: (id) => api.post(`/ansible/jobs/${id}/retry`),
    results: (id) => api.get(`/ansible/jobs/${id}/results`),
  },
  schedules: {
    list: (params) => api.get('/ansible/schedules', { params }),
    get: (id) => api.get(`/ansible/schedules/${id}`),
    create: (data) => api.post('/ansible/schedules', data),
    update: (id, data) => api.put(`/ansible/schedules/${id}`, data),
    delete: (id) => api.delete(`/ansible/schedules/${id}`),
    toggle: (id) => api.post(`/ansible/schedules/${id}/toggle`),
    run: (id) => api.post(`/ansible/schedules/${id}/run`),
  },
};
```

---

## 测试规范

### 1. 单元测试

```python
# tests/test_ansible_services.py
import pytest
from app.services.ansible.encryption import CredentialEncryption

class TestCredentialEncryption:
    def test_encrypt_decrypt(self):
        encryption = CredentialEncryption()
        original = "my-secret-password"
        encrypted = encryption.encrypt(original)
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == original
        assert encrypted != original
    
    def test_encrypt_empty_string(self):
        encryption = CredentialEncryption()
        assert encryption.encrypt("") == ""
        assert encryption.decrypt("") == ""
```

### 2. 集成测试

```python
# tests/test_ansible_api.py
import pytest
from fastapi.testclient import TestClient

def test_create_credential(client: TestClient, auth_headers):
    response = client.post(
        "/api/v1/ansible/credentials",
        json={
            "name": "Test SSH Key",
            "cred_type": "SSH_KEY",
            "username": "root",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\n..."
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test SSH Key"
    assert data["private_key"] == "******"
```

### 3. 测试覆盖率要求

- 最低覆盖率：80%
- 核心模块覆盖率：90%（加密、执行器、调度器）

---

## 部署规范

### 1. 环境变量

```bash
# .env
ANSIBLE_MASTER_KEY=<32-byte-base64-encoded-key>
ANSIBLE_HOST_KEY_CHECKING=False
ANSIBLE_STDOUT_CALLBACK=ansible.builtin.yaml
ANSIBLE_TIMEOUT=30
```

### 2. Docker 配置

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ansible \
    ansible-core \
    sshpass \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# ... 其他配置
```

### 3. 挂载配置

```yaml
# docker-compose.yml
services:
  backend:
    volumes:
      - ansible_data:/root/.ansible
      - /home/shdy/.ansible/inventory:/app/ansible/inventory:ro
      - /home/shdy/.ansible/playbooks:/app/ansible/playbooks:ro
      - /home/shdy/.ansible/role:/app/ansible/roles:ro
      - /home/shdy/.ansible/collections:/app/ansible/collections:ro
```

---

## 验收标准

### 功能验收
- [ ] 凭证管理：创建、编辑、删除、测试连接
- [ ] Playbook 管理：创建、编辑、删除、语法验证、导入
- [ ] Inventory 管理：扫描、查看主机列表、测试连接
- [ ] 任务执行：创建任务、实时输出、取消任务、重试任务
- [ ] 定时任务：创建、编辑、删除、启用/禁用、手动触发
- [ ] Ad-hoc 命令：执行命令、查看模块文档

### 性能验收
- [ ] API 响应时间 < 500ms（P95）
- [ ] 支持 100 个并发任务执行
- [ ] WebSocket 连接稳定，无断连

### 安全验收
- [ ] 凭证加密存储验证
- [ ] 临时文件自动清理验证
- [ ] 权限控制验证
- [ ] 审计日志记录验证

### 文档验收
- [ ] API 文档完整
- [ ] 部署文档完整
- [ ] 用户手册完整
