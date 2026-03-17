# Ansible 集成设计文档

## 一、概述

### 1.1 背景

OpsManager 是一个基于 FastAPI + React 的运维管理平台，已具备资产管理、监控告警、RBAC 权限等核心功能。本设计旨在将 Ansible 自动化能力集成到平台中，实现对网内设备的统一管理。

### 1.2 目标

- 通过 Docker 容器内嵌 Ansible，实现全功能自动化运维
- 支持手动触发和定时调度两种执行模式
- 兼容现有静态 Inventory 和 Playbook 资源
- 统一凭证管理，加密存储敏感信息
- 完整的任务执行记录和审计追踪

### 1.3 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| Ansible 执行环境 | 容器内嵌 | 部署简单，与现有架构融合 |
| 任务调度 | Celery | 复用现有任务队列 |
| 凭证存储 | PostgreSQL + AES 加密 | 统一数据管理，安全可靠 |
| 实时输出 | WebSocket | 用户体验友好 |
| Inventory | 静态文件 | 兼容现有配置 |

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Docker Container                              │
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   FastAPI    │    │    Celery    │    │      Ansible         │  │
│  │   Backend    │◄──►│    Worker    │◄──►│    Controller        │  │
│  │              │    │              │    │                      │  │
│  │ - REST API   │    │ - 任务执行   │    │ - ansible-playbook   │  │
│  │ - WebSocket  │    │ - 定时调度   │    │ - ansible-runner     │  │
│  │ - 权限控制   │    │ - 结果处理   │    │ - 模块执行           │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
│         │                   │                       │               │
│         ▼                   ▼                       ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  PostgreSQL  │    │    Redis     │    │   挂载目录           │  │
│  │              │    │              │    │                      │  │
│  │ - 凭证(加密) │    │ - 任务队列   │    │ /app/ansible/        │  │
│  │ - Playbook   │    │ - 缓存       │    │ ├── inventory/       │  │
│  │ - 任务记录   │    │ - WebSocket  │    │ ├── playbooks/       │  │
│  │ - 审计日志   │    │              │    │ ├── roles/           │  │
│  └──────────────┘    └──────────────┘    │ └── collections/     │  │
│                                          └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                          SSH/WinRM │
                                    ▼
                    ┌───────────────────────────────┐
                    │       被管设备 (Inventory)     │
                    │                               │
                    │  ┌─────────┐  ┌─────────┐    │
                    │  │ Linux   │  │ Windows │    │
                    │  │ SSH     │  │ WinRM   │    │
                    │  └─────────┘  └─────────┘    │
                    └───────────────────────────────┘
```

### 2.2 组件职责

| 组件 | 职责 |
|------|------|
| FastAPI Backend | 提供 REST API、WebSocket 实时输出、权限控制 |
| Celery Worker | 异步任务执行、定时调度、结果处理 |
| Ansible Controller | 执行 ansible-playbook、ansible 命令行工具 |
| PostgreSQL | 存储凭证、Playbook、任务记录、审计日志 |
| Redis | 任务队列、缓存、WebSocket 消息 |

### 2.3 数据流

```
┌─────────────────────────────────────────────────────────────────────┐
│                          执行流程                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 用户发起请求                                                     │
│     ┌─────────┐      ┌─────────────┐      ┌─────────────┐          │
│     │ 前端    │ ───► │ REST API    │ ───► │ 权限校验    │          │
│     └─────────┘      └─────────────┘      └─────────────┘          │
│                                                                      │
│  2. 创建任务                                                         │
│     ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      │
│     │ 写入数据库  │ ───► │ 发送 Redis  │ ───► │ 返回 Job ID │      │
│     │ (PENDING)   │      │ 任务队列    │      │             │      │
│     └─────────────┘      └─────────────┘      └─────────────┘      │
│                                                                      │
│  3. Celery 执行                                                      │
│     ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      │
│     │ Worker 接收 │ ───► │ 更新状态    │ ───► │ 准备执行    │      │
│     │ 任务        │      │ (RUNNING)   │      │ 环境        │      │
│     └─────────────┘      └─────────────┘      └─────────────┘      │
│                                                                      │
│  4. Ansible 执行                                                     │
│     ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      │
│     │ 解密凭证    │ ───► │ 写入临时    │ ───► │ 执行        │      │
│     │             │      │ 密钥文件    │      │ Playbook    │      │
│     └─────────────┘      └─────────────┘      └─────────────┘      │
│                                                                      │
│  5. 实时输出                                                         │
│     ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      │
│     │ 读取 stdout │ ───► │ Redis Pub   │ ───► │ WebSocket   │      │
│     │             │      │ /Sub        │      │ 推送前端    │      │
│     └─────────────┘      └─────────────┘      └─────────────┘      │
│                                                                      │
│  6. 结果处理                                                         │
│     ┌─────────────┐      ┌─────────────┐      ┌─────────────┐      │
│     │ 解析结果    │ ───► │ 写入数据库  │ ───► │ 清理临时    │      │
│     │             │      │             │      │ 文件        │      │
│     └─────────────┘      └─────────────┘      └─────────────┘      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、数据库设计

### 3.1 新增表结构

#### 3.1.1 凭证表 (credentials)

```sql
CREATE TABLE credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    cred_type VARCHAR(20) NOT NULL,  -- SSH_KEY, SSH_PASSWORD, WINRM
    username VARCHAR(100) NOT NULL,
    password TEXT,                    -- AES 加密存储
    private_key TEXT,                 -- AES 加密存储
    passphrase TEXT,                  -- AES 加密存储
    winrm_transport VARCHAR(20),      -- NTLM, KERBEROS, BASIC
    winrm_port INTEGER DEFAULT 5986,
    owner_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_cred_type CHECK (cred_type IN ('SSH_KEY', 'SSH_PASSWORD', 'WINRM'))
);

CREATE INDEX idx_credentials_owner ON credentials(owner_id);
CREATE INDEX idx_credentials_type ON credentials(cred_type);
```

#### 3.1.2 Playbook 表 (playbooks)

```sql
CREATE TABLE playbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(20) NOT NULL,    -- SYSTEM, NETWORK, DEPLOY, CUSTOM
    source_type VARCHAR(20) NOT NULL, -- DATABASE, FILESYSTEM
    content TEXT,                     -- YAML 内容 (source_type=DATABASE)
    file_path VARCHAR(500),           -- 文件路径 (source_type=FILESYSTEM)
    variables JSONB,                  -- 默认变量
    is_template BOOLEAN DEFAULT FALSE,
    is_builtin BOOLEAN DEFAULT FALSE, -- 系统内置，不可删除
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_source_type CHECK (source_type IN ('DATABASE', 'FILESYSTEM')),
    CONSTRAINT chk_category CHECK (category IN ('SYSTEM', 'NETWORK', 'DEPLOY', 'CUSTOM'))
);

CREATE INDEX idx_playbooks_category ON playbooks(category);
CREATE INDEX idx_playbooks_source ON playbooks(source_type);
```

#### 3.1.3 Inventory 文件表 (inventory_files)

```sql
CREATE TABLE inventory_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    environment VARCHAR(50),          -- dev, qa, ops, windows, all
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_inventory_env ON inventory_files(environment);
```

#### 3.1.4 Ansible 任务表 (ansible_jobs)

```sql
CREATE TABLE ansible_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    job_type VARCHAR(20) NOT NULL,    -- PLAYBOOK, AD_HOC
    playbook_id UUID REFERENCES playbooks(id),
    ad_hoc_module VARCHAR(100),       -- 临时命令模块名
    ad_hoc_args JSONB,                -- 临时命令参数
    inventory_file_id UUID REFERENCES inventory_files(id),
    inventory_path VARCHAR(500),      -- 直接指定路径
    credential_id UUID REFERENCES credentials(id),
    extra_vars JSONB,                 -- 额外变量
    limit_pattern VARCHAR(500),       -- 限制执行的主机模式
    tags VARCHAR(500),                -- 执行标签
    skip_tags VARCHAR(500),           -- 跳过标签
    forks INTEGER DEFAULT 5,          -- 并发数
    timeout INTEGER DEFAULT 3600,     -- 超时时间（秒）
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    duration FLOAT,                   -- 执行时长（秒）
    trigger_type VARCHAR(20) NOT NULL, -- MANUAL, SCHEDULED
    schedule_id UUID REFERENCES ansible_schedules(id),
    triggered_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_job_type CHECK (job_type IN ('PLAYBOOK', 'AD_HOC')),
    CONSTRAINT chk_status CHECK (status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'CANCELLED', 'TIMEOUT')),
    CONSTRAINT chk_trigger_type CHECK (trigger_type IN ('MANUAL', 'SCHEDULED'))
);

CREATE INDEX idx_ansible_jobs_status ON ansible_jobs(status);
CREATE INDEX idx_ansible_jobs_triggered_by ON ansible_jobs(triggered_by);
CREATE INDEX idx_ansible_jobs_created_at ON ansible_jobs(created_at DESC);
```

#### 3.1.5 Ansible 任务结果表 (ansible_job_results)

```sql
CREATE TABLE ansible_job_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES ansible_jobs(id) ON DELETE CASCADE,
    asset_id UUID REFERENCES assets(id),
    host_name VARCHAR(255) NOT NULL,
    host_ip VARCHAR(50),
    status VARCHAR(20) NOT NULL,      -- OK, CHANGED, FAILED, UNREACHABLE, SKIPPED
    changed BOOLEAN DEFAULT FALSE,
    failed BOOLEAN DEFAULT FALSE,
    unreachable BOOLEAN DEFAULT FALSE,
    skipped BOOLEAN DEFAULT FALSE,
    stdout TEXT,
    stderr TEXT,
    rc INTEGER,                       -- 返回码
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_result_status CHECK (status IN ('OK', 'CHANGED', 'FAILED', 'UNREACHABLE', 'SKIPPED'))
);

CREATE INDEX idx_job_results_job ON ansible_job_results(job_id);
CREATE INDEX idx_job_results_asset ON ansible_job_results(asset_id);
CREATE INDEX idx_job_results_status ON ansible_job_results(status);
```

#### 3.1.6 Ansible 定时任务表 (ansible_schedules)

```sql
CREATE TABLE ansible_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    playbook_id UUID REFERENCES playbooks(id),
    inventory_file_id UUID REFERENCES inventory_files(id),
    credential_id UUID REFERENCES credentials(id),
    extra_vars JSONB,
    limit_pattern VARCHAR(500),
    tags VARCHAR(500),
    skip_tags VARCHAR(500),
    forks INTEGER DEFAULT 5,
    timeout INTEGER DEFAULT 3600,
    cron_expression VARCHAR(100) NOT NULL,
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
    is_enabled BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    last_run_status VARCHAR(20),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_schedules_enabled ON ansible_schedules(is_enabled);
CREATE INDEX idx_schedules_next_run ON ansible_schedules(next_run_at);
```

### 3.2 资产表扩展

```sql
ALTER TABLE assets ADD COLUMN credential_id UUID REFERENCES credentials(id);
ALTER TABLE assets ADD COLUMN ansible_host VARCHAR(255);
ALTER TABLE assets ADD COLUMN ansible_port INTEGER;
ALTER TABLE assets ADD COLUMN ansible_user VARCHAR(100);
ALTER TABLE assets ADD COLUMN ansible_connection VARCHAR(20) DEFAULT 'ssh';
ALTER TABLE assets ADD COLUMN ansible_become BOOLEAN DEFAULT FALSE;
ALTER TABLE assets ADD COLUMN ansible_become_method VARCHAR(20);
ALTER TABLE assets ADD COLUMN ansible_become_user VARCHAR(100);

CREATE INDEX idx_assets_credential ON assets(credential_id);
```

### 3.3 实体关系图

```
                    ┌─────────────┐
                    │    User     │
                    └──────┬──────┘
                           │ owns
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ Credential  │ │  Playbook   │ │  Schedule   │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           │               │               │
           ▼               ▼               ▼
    ┌───────────────────────────────────────────┐
    │              AnsibleJob                   │
    │  - playbook_id                            │
    │  - credential_id                          │
    │  - inventory_file_id                      │
    │  - schedule_id                            │
    └───────────────────┬───────────────────────┘
                        │ produces
                        ▼
              ┌─────────────────┐
              │ AnsibleJobResult│
              │  - asset_id     │
              └─────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │     Asset       │
              │  - credential_id│
              └─────────────────┘
```

---

## 四、API 设计

### 4.1 凭证管理 API

```
POST   /api/v1/ansible/credentials          创建凭证
GET    /api/v1/ansible/credentials          获取凭证列表
GET    /api/v1/ansible/credentials/{id}     获取凭证详情
PUT    /api/v1/ansible/credentials/{id}     更新凭证
DELETE /api/v1/ansible/credentials/{id}     删除凭证
POST   /api/v1/ansible/credentials/{id}/test 测试凭证连接
```

### 4.2 Playbook 管理 API

```
POST   /api/v1/ansible/playbooks            创建 Playbook
GET    /api/v1/ansible/playbooks            获取 Playbook 列表
GET    /api/v1/ansible/playbooks/{id}       获取 Playbook 详情
PUT    /api/v1/ansible/playbooks/{id}       更新 Playbook
DELETE /api/v1/ansible/playbooks/{id}       删除 Playbook
POST   /api/v1/ansible/playbooks/import     导入文件系统 Playbook
POST   /api/v1/ansible/playbooks/{id}/validate 验证 Playbook 语法
```

### 4.3 Inventory 管理 API

```
GET    /api/v1/ansible/inventories          获取 Inventory 列表
GET    /api/v1/ansible/inventories/{id}     获取 Inventory 详情
POST   /api/v1/ansible/inventories/scan     扫描文件系统 Inventory
GET    /api/v1/ansible/inventories/{id}/hosts 获取 Inventory 主机列表
POST   /api/v1/ansible/inventories/{id}/test 测试 Inventory 连接
```

### 4.4 任务执行 API

```
POST   /api/v1/ansible/jobs                 创建并执行任务
GET    /api/v1/ansible/jobs                 获取任务列表
GET    /api/v1/ansible/jobs/{id}            获取任务详情
POST   /api/v1/ansible/jobs/{id}/cancel     取消任务
POST   /api/v1/ansible/jobs/{id}/retry      重试任务
GET    /api/v1/ansible/jobs/{id}/results    获取任务结果
GET    /api/v1/ansible/jobs/{id}/output     获取任务输出（SSE/WebSocket）
```

### 4.5 定时任务 API

```
POST   /api/v1/ansible/schedules            创建定时任务
GET    /api/v1/ansible/schedules            获取定时任务列表
GET    /api/v1/ansible/schedules/{id}       获取定时任务详情
PUT    /api/v1/ansible/schedules/{id}       更新定时任务
DELETE /api/v1/ansible/schedules/{id}       删除定时任务
POST   /api/v1/ansible/schedules/{id}/toggle 启用/禁用定时任务
POST   /api/v1/ansible/schedules/{id}/run   手动触发定时任务
```

### 4.6 Ad-hoc 命令 API

```
POST   /api/v1/ansible/ad-hoc               执行 Ad-hoc 命令
GET    /api/v1/ansible/modules              获取可用模块列表
GET    /api/v1/ansible/modules/{name}/docs  获取模块文档
```

### 4.7 WebSocket 实时输出

```
WS     /api/v1/ansible/jobs/{id}/ws         实时任务输出
```

---

## 五、安全设计

### 5.1 凭证加密

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class CredentialEncryption:
    def __init__(self, master_key: bytes = None):
        if master_key is None:
            master_key = os.environ.get('ANSIBLE_MASTER_KEY', '').encode()
        
        salt = b'ops-manager-ansible-salt'
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key))
        self.fernet = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        return self.fernet.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        return self.fernet.decrypt(ciphertext.encode()).decode()
```

### 5.2 临时文件处理

```python
import tempfile
import os
import shutil

class SecureTempFile:
    def __init__(self):
        self.temp_dir = None
        self.files = []
    
    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp(prefix='ansible_')
        os.chmod(self.temp_dir, 0o700)
        return self
    
    def write_key(self, private_key: str, passphrase: str = None) -> str:
        key_path = os.path.join(self.temp_dir, 'id_rsa')
        with open(key_path, 'w') as f:
            os.chmod(key_path, 0o600)
            f.write(private_key)
        self.files.append(key_path)
        return key_path
    
    def __exit__(self, *args):
        for f in self.files:
            if os.path.exists(f):
                os.remove(f)
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
```

### 5.3 权限控制

| 权限代码 | 描述 |
|----------|------|
| `ansible:credential:read` | 查看凭证 |
| `ansible:credential:write` | 创建/编辑凭证 |
| `ansible:credential:delete` | 删除凭证 |
| `ansible:playbook:read` | 查看 Playbook |
| `ansible:playbook:write` | 创建/编辑 Playbook |
| `ansible:playbook:delete` | 删除 Playbook |
| `ansible:job:execute` | 执行任务 |
| `ansible:job:read` | 查看任务记录 |
| `ansible:job:cancel` | 取消任务 |
| `ansible:schedule:read` | 查看定时任务 |
| `ansible:schedule:write` | 创建/编辑定时任务 |
| `ansible:schedule:delete` | 删除定时任务 |
| `ansible:ad-hoc:execute` | 执行 Ad-hoc 命令 |

### 5.4 审计日志

所有 Ansible 操作都记录到审计日志：

| 操作类型 | 模块 | 详情 |
|----------|------|------|
| CREATE | credential | 凭证创建（不记录敏感信息） |
| UPDATE | credential | 凭证更新 |
| DELETE | credential | 凭证删除 |
| EXECUTE | ansible_job | 任务执行 |
| CANCEL | ansible_job | 任务取消 |
| CREATE | playbook | Playbook 创建 |
| EXECUTE | ad_hoc | Ad-hoc 命令执行 |

---

## 六、Celery 任务设计

### 6.1 任务模块结构

```
backend/app/tasks/
├── __init__.py
├── celery_app.py
├── ansible/
│   ├── __init__.py
│   ├── executor.py      # 任务执行器
│   ├── scheduler.py     # 定时调度
│   ├── output.py        # 输出处理
│   └── cleanup.py       # 清理任务
```

### 6.2 核心任务

```python
from celery import shared_task
from celery.result import AsyncResult
import subprocess
import json
import os

@shared_task(bind=True, max_retries=3)
def execute_ansible_job(self, job_id: str):
    """执行 Ansible 任务"""
    from app.crud.ansible import get_job, update_job_status
    from app.services.ansible.executor import AnsibleExecutor
    
    job = get_job(job_id)
    if not job:
        return {"error": "Job not found"}
    
    update_job_status(job_id, "RUNNING")
    
    try:
        executor = AnsibleExecutor(job)
        result = executor.run()
        update_job_status(job_id, "SUCCESS", result)
        return result
    except Exception as e:
        update_job_status(job_id, "FAILED", {"error": str(e)})
        raise self.retry(exc=e, countdown=60)

@shared_task
def schedule_ansible_jobs():
    """定时任务调度器（每分钟执行）"""
    from app.crud.ansible import get_pending_schedules
    
    schedules = get_pending_schedules()
    for schedule in schedules:
        execute_ansible_job.delay(schedule.create_job())

@shared_task
def cleanup_old_job_results():
    """清理 30 天前的任务结果"""
    from app.crud.ansible import delete_old_results
    delete_old_results(days=30)
```

### 6.3 Ansible 执行器

```python
import subprocess
import os
import json
import tempfile
from pathlib import Path

class AnsibleExecutor:
    def __init__(self, job):
        self.job = job
        self.temp_dir = None
        self.output_buffer = []
    
    def run(self) -> dict:
        with tempfile.TemporaryDirectory(prefix='ansible_') as temp_dir:
            self.temp_dir = temp_dir
            
            cmd = self._build_command()
            env = self._build_env()
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=temp_dir,
                text=True
            )
            
            self._stream_output(process)
            
            return self._parse_results()
    
    def _build_command(self) -> list:
        cmd = ['ansible-playbook']
        
        if self.job.playbook:
            if self.job.playbook.source_type == 'FILESYSTEM':
                cmd.append(self.job.playbook.file_path)
            else:
                playbook_path = self._write_playbook()
                cmd.append(playbook_path)
        
        cmd.extend(['-i', self.job.inventory_path])
        
        if self.job.limit_pattern:
            cmd.extend(['--limit', self.job.limit_pattern])
        
        if self.job.tags:
            cmd.extend(['--tags', self.job.tags])
        
        if self.job.skip_tags:
            cmd.extend(['--skip-tags', self.job.skip_tags])
        
        cmd.extend(['--forks', str(self.job.forks)])
        
        if self.job.extra_vars:
            cmd.extend(['--extra-vars', json.dumps(self.job.extra_vars)])
        
        if self.job.credential:
            cmd.extend(self._build_credential_args())
        
        return cmd
    
    def _build_credential_args(self) -> list:
        args = []
        cred = self.job.credential
        
        if cred.cred_type == 'SSH_KEY':
            key_path = self._write_private_key(cred.private_key)
            args.extend(['--private-key', key_path])
            args.extend(['--user', cred.username])
        elif cred.cred_type == 'SSH_PASSWORD':
            args.extend(['--user', cred.username])
            args.append('--ask-pass')
        elif cred.cred_type == 'WINRM':
            args.extend(['--connection', 'winrm'])
            args.extend(['--user', cred.username])
        
        return args
    
    def _stream_output(self, process):
        for line in process.stdout:
            self.output_buffer.append(line)
            self._publish_output(line)
        
        process.wait()
        self.return_code = process.returncode
    
    def _publish_output(self, line: str):
        from app.core.redis import get_redis
        redis = get_redis()
        redis.publish(f'ansible:job:{self.job.id}:output', line)
```

---

## 七、前端设计

### 7.1 页面结构

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

### 7.2 路由配置

```typescript
const ansibleRoutes = [
  {
    path: '/ansible/credentials',
    element: <CredentialList />,
    permission: 'ansible:credential:read',
  },
  {
    path: '/ansible/playbooks',
    element: <PlaybookList />,
    permission: 'ansible:playbook:read',
  },
  {
    path: '/ansible/playbooks/:id/edit',
    element: <PlaybookEditor />,
    permission: 'ansible:playbook:write',
  },
  {
    path: '/ansible/inventories',
    element: <InventoryList />,
    permission: 'ansible:job:read',
  },
  {
    path: '/ansible/jobs',
    element: <JobList />,
    permission: 'ansible:job:read',
  },
  {
    path: '/ansible/jobs/create',
    element: <JobCreate />,
    permission: 'ansible:job:execute',
  },
  {
    path: '/ansible/jobs/:id',
    element: <JobDetail />,
    permission: 'ansible:job:read',
  },
  {
    path: '/ansible/schedules',
    element: <ScheduleList />,
    permission: 'ansible:schedule:read',
  },
  {
    path: '/ansible/ad-hoc',
    element: <AdHocExecute />,
    permission: 'ansible:ad-hoc:execute',
  },
];
```

### 7.3 实时输出组件

```tsx
import { useEffect, useState, useRef } from 'react';

interface JobOutputProps {
  jobId: string;
}

export function JobOutput({ jobId }: JobOutputProps) {
  const [output, setOutput] = useState<string[]>([]);
  const containerRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.host}/api/v1/ansible/jobs/${jobId}/ws`);
    
    ws.onmessage = (event) => {
      setOutput((prev) => [...prev, event.data]);
    };
    
    return () => ws.close();
  }, [jobId]);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [output]);

  return (
    <pre
      ref={containerRef}
      style={{
        backgroundColor: '#1e1e1e',
        color: '#d4d4d4',
        padding: '16px',
        borderRadius: '8px',
        height: '400px',
        overflow: 'auto',
        fontFamily: 'monospace',
        fontSize: '13px',
      }}
    >
      {output.map((line, index) => (
        <div key={index}>{line}</div>
      ))}
    </pre>
  );
}
```

---

## 八、Docker 配置

### 8.1 Dockerfile 更新

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ansible \
    ansible-core \
    sshpass \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/prod.txt .
RUN pip install --no-cache-dir -r prod.txt

COPY . .

RUN mkdir -p /app/ansible && chmod 700 /app/ansible

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.2 docker-compose.yml 更新

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    volumes:
      - ansible_data:/root/.ansible
      - /home/shdy/.ansible/inventory:/app/ansible/inventory:ro
      - /home/shdy/.ansible/playbooks:/app/ansible/playbooks:ro
      - /home/shdy/.ansible/role:/app/ansible/roles:ro
      - /home/shdy/.ansible/collections:/app/ansible/collections:ro
    environment:
      - ANSIBLE_MASTER_KEY=${ANSIBLE_MASTER_KEY}
      - ANSIBLE_HOST_KEY_CHECKING=False
      - ANSIBLE_STDOUT_CALLBACK=ansible.builtin.yaml
    depends_on:
      - postgres
      - redis

  celery-worker:
    build: ./backend
    command: celery -A app.tasks.celery_app worker --loglevel=info
    volumes:
      - ansible_data:/root/.ansible
      - /home/shdy/.ansible/inventory:/app/ansible/inventory:ro
      - /home/shdy/.ansible/playbooks:/app/ansible/playbooks:ro
      - /home/shdy/.ansible/role:/app/ansible/roles:ro
      - /home/shdy/.ansible/collections:/app/ansible/collections:ro
    environment:
      - ANSIBLE_MASTER_KEY=${ANSIBLE_MASTER_KEY}
      - ANSIBLE_HOST_KEY_CHECKING=False
    depends_on:
      - postgres
      - redis

  celery-beat:
    build: ./backend
    command: celery -A app.tasks.celery_app beat --loglevel=info
    volumes:
      - ansible_data:/root/.ansible
    depends_on:
      - postgres
      - redis

volumes:
  ansible_data:
```

---

## 九、现有资源导入

### 9.1 Playbook 导入脚本

```python
# scripts/import_playbooks.py

PLAYBOOK_IMPORTS = [
    {
        'name': 'Debian 系统初始化',
        'file_path': '/app/ansible/playbooks/init_debian.yml',
        'category': 'SYSTEM',
        'description': 'Debian/Ubuntu 系统初始化配置',
        'is_builtin': True,
    },
    {
        'name': 'Docker 安装部署',
        'file_path': '/app/ansible/playbooks/install_docker_init.yml',
        'category': 'DEPLOY',
        'description': '安装 Docker 并初始化配置',
        'is_builtin': True,
    },
    {
        'name': 'Promtail 部署',
        'file_path': '/app/ansible/playbooks/deploy_promtail.yml',
        'category': 'DEPLOY',
        'description': '部署 Promtail 日志收集代理',
        'is_builtin': True,
    },
    {
        'name': '监控组件安装',
        'file_path': '/app/ansible/playbooks/install_monitor.yml',
        'category': 'DEPLOY',
        'description': '安装监控组件',
        'is_builtin': True,
    },
    {
        'name': '监控检查',
        'file_path': '/app/ansible/playbooks/check_monitor.yml',
        'category': 'SYSTEM',
        'description': '检查监控组件状态',
        'is_builtin': True,
    },
    {
        'name': 'SSH 密钥更换',
        'file_path': '/app/ansible/playbooks/change_ssh_key.yml',
        'category': 'SYSTEM',
        'description': '批量更换 SSH 密钥',
        'is_builtin': True,
    },
    {
        'name': 'Windows Exporter 安装',
        'file_path': '/app/ansible/playbooks/windows_exporter_install.yml',
        'category': 'DEPLOY',
        'description': '在 Windows 上安装 Prometheus Exporter',
        'is_builtin': True,
    },
    {
        'name': 'SDC 安装',
        'file_path': '/app/ansible/playbooks/install_sdc.yml',
        'category': 'DEPLOY',
        'description': '安装 SDC 组件',
        'is_builtin': True,
    },
]

INVENTORY_IMPORTS = [
    {
        'name': '开发环境',
        'file_path': '/app/ansible/inventory/dev/hosts',
        'environment': 'dev',
    },
    {
        'name': '测试环境',
        'file_path': '/app/ansible/inventory/qa/hosts',
        'environment': 'qa',
    },
    {
        'name': '生产环境',
        'file_path': '/app/ansible/inventory/ops/hosts',
        'environment': 'ops',
    },
    {
        'name': 'Windows 设备',
        'file_path': '/app/ansible/inventory/windows/host.ini',
        'environment': 'windows',
    },
    {
        'name': '全量资产',
        'file_path': '/app/ansible/inventory/incloud_all/hosts',
        'environment': 'all',
    },
]
```

### 9.2 权限初始化

```python
# scripts/init_ansible_permissions.py

ANSIBLE_PERMISSIONS = [
    {'code': 'ansible:credential:read', 'name': '查看凭证', 'module': 'ansible', 'action': 'read'},
    {'code': 'ansible:credential:write', 'name': '创建/编辑凭证', 'module': 'ansible', 'action': 'write'},
    {'code': 'ansible:credential:delete', 'name': '删除凭证', 'module': 'ansible', 'action': 'delete'},
    {'code': 'ansible:playbook:read', 'name': '查看 Playbook', 'module': 'ansible', 'action': 'read'},
    {'code': 'ansible:playbook:write', 'name': '创建/编辑 Playbook', 'module': 'ansible', 'action': 'write'},
    {'code': 'ansible:playbook:delete', 'name': '删除 Playbook', 'module': 'ansible', 'action': 'delete'},
    {'code': 'ansible:job:execute', 'name': '执行任务', 'module': 'ansible', 'action': 'execute'},
    {'code': 'ansible:job:read', 'name': '查看任务记录', 'module': 'ansible', 'action': 'read'},
    {'code': 'ansible:job:cancel', 'name': '取消任务', 'module': 'ansible', 'action': 'cancel'},
    {'code': 'ansible:schedule:read', 'name': '查看定时任务', 'module': 'ansible', 'action': 'read'},
    {'code': 'ansible:schedule:write', 'name': '创建/编辑定时任务', 'module': 'ansible', 'action': 'write'},
    {'code': 'ansible:schedule:delete', 'name': '删除定时任务', 'module': 'ansible', 'action': 'delete'},
    {'code': 'ansible:ad-hoc:execute', 'name': '执行 Ad-hoc 命令', 'module': 'ansible', 'action': 'execute'},
]
```

---

## 十、实施计划

### 10.1 阶段一：基础框架（1-2 周）

- [ ] 数据库模型和迁移
- [ ] 凭证管理 API
- [ ] Playbook 管理 API
- [ ] Inventory 管理 API
- [ ] 基础权限配置

### 10.2 阶段二：任务执行（2-3 周）

- [ ] Ansible 执行器
- [ ] Celery 任务集成
- [ ] WebSocket 实时输出
- [ ] 任务结果解析和存储
- [ ] 审计日志集成

### 10.3 阶段三：定时调度（1 周）

- [ ] 定时任务管理
- [ ] Celery Beat 集成
- [ ] 调度执行逻辑

### 10.4 阶段四：前端界面（2-3 周）

- [ ] 凭证管理页面
- [ ] Playbook 编辑器
- [ ] 任务执行界面
- [ ] 实时输出展示
- [ ] 定时任务管理

### 10.5 阶段五：测试与优化（1-2 周）

- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能优化
- [ ] 文档完善

---

## 十一、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 凭证泄露 | 高 | AES 加密存储，临时文件自动清理 |
| 任务执行超时 | 中 | 设置超时时间，支持任务取消 |
| 大规模执行性能 | 中 | 限制并发数，任务队列控制 |
| 容器资源不足 | 中 | 监控资源使用，动态扩容 |
| 静态 Inventory 不同步 | 低 | 定期扫描，手动刷新 |

---

## 十二、附录

### 12.1 环境变量

```bash
# .env
ANSIBLE_MASTER_KEY=your-32-byte-master-key-here
ANSIBLE_HOST_KEY_CHECKING=False
ANSIBLE_STDOUT_CALLBACK=ansible.builtin.yaml
ANSIBLE_TIMEOUT=30
```

### 12.2 参考文档

- [Ansible 官方文档](https://docs.ansible.com/)
- [Celery 官方文档](https://docs.celeryq.dev/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [WebSocket RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)
