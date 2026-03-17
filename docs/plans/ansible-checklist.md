# Ansible 集成检查清单

## 阶段一：基础框架

### 数据库模型
- [ ] 创建 `backend/app/models/ansible.py` 文件
- [ ] 定义 `Credential` 模型
  - [ ] id: UUID 主键
  - [ ] name: 凭证名称
  - [ ] cred_type: 凭证类型枚举
  - [ ] username: 用户名
  - [ ] password: 加密密码字段
  - [ ] private_key: 加密私钥字段
  - [ ] passphrase: 加密密钥密码字段
  - [ ] winrm_transport: WinRM 传输类型
  - [ ] winrm_port: WinRM 端口
  - [ ] owner_id: 所属用户外键
  - [ ] created_at, updated_at 时间戳
- [ ] 定义 `Playbook` 模型
  - [ ] id: UUID 主键
  - [ ] name: Playbook 名称
  - [ ] description: 描述
  - [ ] category: 分类枚举
  - [ ] source_type: 来源类型枚举
  - [ ] content: YAML 内容
  - [ ] file_path: 文件路径
  - [ ] variables: 默认变量 JSON
  - [ ] is_template: 是否为模板
  - [ ] is_builtin: 是否为内置
  - [ ] created_by: 创建者外键
- [ ] 定义 `InventoryFile` 模型
  - [ ] id: UUID 主键
  - [ ] name: 显示名称
  - [ ] file_path: 文件路径
  - [ ] environment: 环境标识
  - [ ] description: 描述
  - [ ] is_active: 是否激活
- [ ] 定义 `AnsibleJob` 模型
  - [ ] id: UUID 主键
  - [ ] name: 任务名称
  - [ ] job_type: 任务类型枚举
  - [ ] playbook_id: Playbook 外键
  - [ ] ad_hoc_module: Ad-hoc 模块名
  - [ ] ad_hoc_args: Ad-hoc 参数
  - [ ] inventory_file_id: Inventory 外键
  - [ ] credential_id: 凭证外键
  - [ ] extra_vars: 额外变量 JSON
  - [ ] limit_pattern: 限制模式
  - [ ] tags, skip_tags: 标签
  - [ ] forks: 并发数
  - [ ] timeout: 超时时间
  - [ ] status: 状态枚举
  - [ ] started_at, finished_at: 时间戳
  - [ ] duration: 执行时长
  - [ ] trigger_type: 触发类型
  - [ ] triggered_by: 触发者外键
- [ ] 定义 `AnsibleJobResult` 模型
  - [ ] id: UUID 主键
  - [ ] job_id: 任务外键
  - [ ] asset_id: 资产外键
  - [ ] host_name: 主机名
  - [ ] host_ip: 主机 IP
  - [ ] status: 结果状态枚举
  - [ ] changed, failed, unreachable, skipped: 状态标志
  - [ ] stdout, stderr: 输出
  - [ ] rc: 返回码
  - [ ] start_time, end_time, duration: 时间信息
- [ ] 定义 `AnsibleSchedule` 模型
  - [ ] id: UUID 主键
  - [ ] name: 定时任务名称
  - [ ] playbook_id: Playbook 外键
  - [ ] inventory_file_id: Inventory 外键
  - [ ] credential_id: 凭证外键
  - [ ] extra_vars: 额外变量
  - [ ] cron_expression: Cron 表达式
  - [ ] timezone: 时区
  - [ ] is_enabled: 是否启用
  - [ ] last_run_at, next_run_at: 执行时间
  - [ ] last_run_status: 上次执行状态
- [ ] 扩展 `Asset` 模型
  - [ ] credential_id: 关联凭证
  - [ ] ansible_host: Ansible 连接地址
  - [ ] ansible_port: SSH/WinRM 端口
  - [ ] ansible_user: 覆盖用户名
  - [ ] ansible_connection: 连接类型
  - [ ] ansible_become: 是否提权
  - [ ] ansible_become_method: 提权方式
  - [ ] ansible_become_user: 提权用户

### 数据库迁移
- [ ] 创建 Alembic 迁移文件
- [ ] 迁移文件包含所有新表
- [ ] 迁移文件包含 assets 表扩展字段
- [ ] 执行 `alembic upgrade head` 成功
- [ ] 验证数据库表结构正确

### Pydantic Schema
- [ ] 创建 `backend/app/schemas/ansible.py` 文件
- [ ] 定义 `CredentialCreate` Schema
- [ ] 定义 `CredentialUpdate` Schema
- [ ] 定义 `CredentialResponse` Schema（敏感字段脱敏）
- [ ] 定义 `PlaybookCreate` Schema
- [ ] 定义 `PlaybookUpdate` Schema
- [ ] 定义 `PlaybookResponse` Schema
- [ ] 定义 `InventoryFileResponse` Schema
- [ ] 定义 `AnsibleJobCreate` Schema
- [ ] 定义 `AnsibleJobResponse` Schema
- [ ] 定义 `AnsibleJobResultResponse` Schema
- [ ] 定义 `AnsibleScheduleCreate` Schema
- [ ] 定义 `AnsibleScheduleResponse` Schema
- [ ] 定义分页响应 Schema

### CRUD 操作
- [ ] 创建 `backend/app/crud/ansible.py` 文件
- [ ] 实现 `CredentialCRUD` 类
  - [ ] create 方法（加密敏感字段）
  - [ ] get 方法
  - [ ] get_multi 方法（分页）
  - [ ] update 方法
  - [ ] delete 方法
  - [ ] get_by_name 方法
- [ ] 实现 `PlaybookCRUD` 类
  - [ ] create 方法
  - [ ] get 方法
  - [ ] get_multi 方法（支持分类筛选）
  - [ ] update 方法
  - [ ] delete 方法（检查 is_builtin）
  - [ ] get_by_path 方法
- [ ] 实现 `InventoryFileCRUD` 类
  - [ ] create 方法
  - [ ] get 方法
  - [ ] get_multi 方法
  - [ ] get_by_environment 方法
- [ ] 实现 `AnsibleJobCRUD` 类
  - [ ] create 方法
  - [ ] get 方法
  - [ ] get_multi 方法（支持状态筛选）
  - [ ] update_status 方法
  - [ ] get_results 方法
- [ ] 实现 `AnsibleScheduleCRUD` 类
  - [ ] create 方法
  - [ ] get 方法
  - [ ] get_multi 方法
  - [ ] update_next_run 方法
  - [ ] get_pending_schedules 方法

### 权限配置
- [ ] 在 `backend/app/core/permissions.py` 添加 Ansible 权限常量
- [ ] 创建 `backend/scripts/init_ansible_permissions.py` 初始化脚本
- [ ] 执行权限初始化脚本
- [ ] 验证权限已正确添加到数据库
- [ ] 验证权限与角色关联正确

---

## 阶段二：核心服务

### 凭证加密服务
- [ ] 创建 `backend/app/services/ansible/` 目录
- [ ] 创建 `encryption.py` 文件
- [ ] 实现 `CredentialEncryption` 类
  - [ ] 单例模式
  - [ ] 从环境变量获取主密钥
  - [ ] PBKDF2 密钥派生
  - [ ] encrypt 方法
  - [ ] decrypt 方法
  - [ ] 空值处理
- [ ] 添加 `ANSIBLE_MASTER_KEY` 到 `.env.example`
- [ ] 编写加密服务单元测试

### 凭证管理 API
- [ ] 创建 `backend/app/api/v1/ansible.py` 文件
- [ ] 实现 `POST /api/v1/ansible/credentials`
  - [ ] 权限检查
  - [ ] 输入验证
  - [ ] 敏感字段加密
  - [ ] 返回脱敏响应
- [ ] 实现 `GET /api/v1/ansible/credentials`
  - [ ] 权限检查
  - [ ] 分页支持
  - [ ] 类型筛选
  - [ ] 返回脱敏响应
- [ ] 实现 `GET /api/v1/ansible/credentials/{id}`
  - [ ] 权限检查
  - [ ] 存在性检查
  - [ ] 返回脱敏响应
- [ ] 实现 `PUT /api/v1/ansible/credentials/{id}`
  - [ ] 权限检查
  - [ ] 存在性检查
  - [ ] 敏感字段加密
- [ ] 实现 `DELETE /api/v1/ansible/credentials/{id}`
  - [ ] 权限检查
  - [ ] 存在性检查
  - [ ] 检查是否被引用
- [ ] 实现 `POST /api/v1/ansible/credentials/{id}/test`
  - [ ] 权限检查
  - [ ] 解密凭证
  - [ ] 创建临时密钥文件
  - [ ] 执行连接测试
  - [ ] 清理临时文件
  - [ ] 返回测试结果

### Playbook 管理 API
- [ ] 实现 `POST /api/v1/ansible/playbooks`
  - [ ] 权限检查
  - [ ] 输入验证
  - [ ] 语法检查（可选）
- [ ] 实现 `GET /api/v1/ansible/playbooks`
  - [ ] 权限检查
  - [ ] 分页支持
  - [ ] 分类筛选
  - [ ] 来源类型筛选
- [ ] 实现 `GET /api/v1/ansible/playbooks/{id}`
  - [ ] 权限检查
  - [ ] 存在性检查
  - [ ] 文件系统类型读取文件内容
- [ ] 实现 `PUT /api/v1/ansible/playbooks/{id}`
  - [ ] 权限检查
  - [ ] 存在性检查
  - [ ] 内置检查
- [ ] 实现 `DELETE /api/v1/ansible/playbooks/{id}`
  - [ ] 权限检查
  - [ ] 存在性检查
  - [ ] 内置检查
  - [ ] 引用检查
- [ ] 实现 `POST /api/v1/ansible/playbooks/import`
  - [ ] 权限检查
  - [ ] 扫描文件系统目录
  - [ ] 导入到数据库
- [ ] 实现 `POST /api/v1/ansible/playbooks/{id}/validate`
  - [ ] 权限检查
  - [ ] 执行 `ansible-playbook --syntax-check`
  - [ ] 返回验证结果

### Inventory 管理 API
- [ ] 实现 `GET /api/v1/ansible/inventories`
  - [ ] 权限检查
  - [ ] 分页支持
  - [ ] 环境筛选
- [ ] 实现 `GET /api/v1/ansible/inventories/{id}`
  - [ ] 权限检查
  - [ ] 存在性检查
- [ ] 实现 `POST /api/v1/ansible/inventories/scan`
  - [ ] 权限检查
  - [ ] 扫描挂载目录
  - [ ] 识别 Inventory 文件
  - [ ] 自动识别环境
  - [ ] 更新数据库
- [ ] 实现 `GET /api/v1/ansible/inventories/{id}/hosts`
  - [ ] 权限检查
  - [ ] 解析 Inventory 文件
  - [ ] 返回主机列表
- [ ] 实现 `POST /api/v1/ansible/inventories/{id}/test`
  - [ ] 权限检查
  - [ ] 执行 `ansible all -m ping`
  - [ ] 返回测试结果

### Ansible 执行器
- [ ] 创建 `backend/app/services/ansible/executor.py` 文件
- [ ] 实现 `AnsibleExecutor` 类
  - [ ] `__init__` 方法（接收 job 对象）
  - [ ] `_build_command` 方法（构建 ansible-playbook 命令）
  - [ ] `_build_env` 方法（构建环境变量）
  - [ ] `_build_credential_args` 方法（构建凭证参数）
  - [ ] `_write_playbook` 方法（写入临时 playbook 文件）
  - [ ] `_write_private_key` 方法（写入临时密钥文件）
  - [ ] `_stream_output` 方法（流式读取输出）
  - [ ] `_publish_output` 方法（发布到 Redis）
  - [ ] `_parse_results` 方法（解析执行结果）
  - [ ] `run` 方法（主执行方法）
- [ ] 实现 `AdHocExecutor` 类
  - [ ] 类似 Playbook 执行器
  - [ ] 使用 `ansible` 命令而非 `ansible-playbook`

### Celery 任务
- [ ] 创建 `backend/app/tasks/ansible/` 目录
- [ ] 创建 `__init__.py` 文件
- [ ] 创建 `executor.py` 文件
  - [ ] 实现 `execute_ansible_job` 任务
  - [ ] 实现任务重试逻辑
  - [ ] 实现任务超时处理
  - [ ] 实现结果写入
- [ ] 创建 `output.py` 文件
  - [ ] 实现 `OutputPublisher` 类
  - [ ] 实现输出格式化
- [ ] 创建 `cleanup.py` 文件
  - [ ] 实现 `cleanup_old_results` 任务
  - [ ] 实现 `cleanup_temp_files` 任务
- [ ] 更新 `celery_app.py` 配置
  - [ ] 添加 Ansible 任务模块
  - [ ] 配置任务超时
  - [ ] 配置 Beat 调度

### 任务执行 API
- [ ] 实现 `POST /api/v1/ansible/jobs`
  - [ ] 权限检查
  - [ ] 输入验证
  - [ ] 创建任务记录
  - [ ] 发送到 Celery 队列
  - [ ] 返回 Job ID
- [ ] 实现 `GET /api/v1/ansible/jobs`
  - [ ] 权限检查
  - [ ] 分页支持
  - [ ] 状态筛选
  - [ ] 时间范围筛选
- [ ] 实现 `GET /api/v1/ansible/jobs/{id}`
  - [ ] 权限检查
  - [ ] 存在性检查
  - [ ] 返回完整信息
- [ ] 实现 `POST /api/v1/ansible/jobs/{id}/cancel`
  - [ ] 权限检查
  - [ ] 状态检查（仅 RUNNING 可取消）
  - [ ] 终止 Celery 任务
  - [ ] 更新状态
- [ ] 实现 `POST /api/v1/ansible/jobs/{id}/retry`
  - [ ] 权限检查
  - [ ] 状态检查
  - [ ] 创建新任务
- [ ] 实现 `GET /api/v1/ansible/jobs/{id}/results`
  - [ ] 权限检查
  - [ ] 返回所有主机结果
- [ ] 实现 WebSocket 端点 `WS /api/v1/ansible/jobs/{id}/ws`
  - [ ] 连接认证
  - [ ] 订阅 Redis 频道
  - [ ] 推送实时输出
  - [ ] 处理断连

---

## 阶段三：定时调度

### 定时任务服务
- [ ] 创建 `backend/app/tasks/ansible/scheduler.py` 文件
- [ ] 实现 `check_scheduled_jobs` 任务
  - [ ] 查询待执行的定时任务
  - [ ] 创建执行任务
  - [ ] 更新下次执行时间
- [ ] 实现 `calculate_next_run` 函数
  - [ ] 使用 croniter 解析 Cron 表达式
  - [ ] 计算下次执行时间
  - [ ] 处理时区

### 定时任务 API
- [ ] 实现 `POST /api/v1/ansible/schedules`
  - [ ] 权限检查
  - [ ] Cron 表达式验证
  - [ ] 计算下次执行时间
- [ ] 实现 `GET /api/v1/ansible/schedules`
  - [ ] 权限检查
  - [ ] 分页支持
  - [ ] 启用状态筛选
- [ ] 实现 `GET /api/v1/ansible/schedules/{id}`
  - [ ] 权限检查
  - [ ] 存在性检查
- [ ] 实现 `PUT /api/v1/ansible/schedules/{id}`
  - [ ] 权限检查
  - [ ] 存在性检查
  - [ ] 重新计算下次执行时间
- [ ] 实现 `DELETE /api/v1/ansible/schedules/{id}`
  - [ ] 权限检查
  - [ ] 存在性检查
- [ ] 实现 `POST /api/v1/ansible/schedules/{id}/toggle`
  - [ ] 权限检查
  - [ ] 切换启用状态
  - [ ] 更新下次执行时间
- [ ] 实现 `POST /api/v1/ansible/schedules/{id}/run`
  - [ ] 权限检查
  - [ ] 立即创建执行任务

---

## 阶段四：前端界面

### 基础设施
- [ ] 创建 `frontend/src/services/ansible.ts` API 服务文件
- [ ] 添加路由配置到 `routePermissions.ts`
- [ ] 添加导航菜单项
- [ ] 创建 `frontend/src/pages/Ansible/` 目录结构

### 凭证管理页面
- [ ] 创建 `Credentials/CredentialList.tsx`
  - [ ] 表格展示凭证列表
  - [ ] 支持搜索和筛选
  - [ ] 支持新建、编辑、删除
  - [ ] 敏感字段脱敏显示
- [ ] 创建 `Credentials/CredentialForm.tsx`
  - [ ] 表单字段根据类型动态显示
  - [ ] SSH Key 类型显示文本域
  - [ ] WinRM 类型显示传输选项
  - [ ] 表单验证
- [ ] 创建 `Credentials/CredentialTest.tsx`
  - [ ] 测试连接按钮
  - [ ] 显示测试结果

### Playbook 管理页面
- [ ] 创建 `Playbooks/PlaybookList.tsx`
  - [ ] 表格展示 Playbook 列表
  - [ ] 支持分类筛选
  - [ ] 支持来源类型筛选
  - [ ] 支持新建、编辑、删除
  - [ ] 支持导入文件系统 Playbook
- [ ] 创建 `Playbooks/PlaybookEditor.tsx`
  - [ ] 集成 Monaco Editor
  - [ ] YAML 语法高亮
  - [ ] 语法验证按钮
  - [ ] 变量编辑器
- [ ] 创建 `Playbooks/PlaybookImport.tsx`
  - [ ] 显示可导入的 Playbook 列表
  - [ ] 批量导入功能

### Inventory 管理页面
- [ ] 创建 `Inventories/InventoryList.tsx`
  - [ ] 表格展示 Inventory 列表
  - [ ] 支持环境筛选
  - [ ] 扫描按钮
  - [ ] 测试连接按钮
- [ ] 创建 `Inventories/InventoryDetail.tsx`
  - [ ] 显示主机列表
  - [ ] 显示分组信息

### 任务执行页面
- [ ] 创建 `Jobs/JobList.tsx`
  - [ ] 表格展示任务列表
  - [ ] 支持状态筛选
  - [ ] 支持时间范围筛选
  - [ ] 显示执行状态
- [ ] 创建 `Jobs/JobCreate.tsx`
  - [ ] 选择 Playbook
  - [ ] 选择 Inventory
  - [ ] 选择凭证
  - [ ] 配置执行参数
  - [ ] 额外变量编辑
- [ ] 创建 `Jobs/JobDetail.tsx`
  - [ ] 显示任务信息
  - [ ] 显示执行结果汇总
  - [ ] 显示各主机结果
  - [ ] 取消/重试按钮
- [ ] 创建 `Jobs/JobOutput.tsx`
  - [ ] WebSocket 连接
  - [ ] 实时输出显示
  - [ ] 终端风格样式
  - [ ] 自动滚动

### 定时任务页面
- [ ] 创建 `Schedules/ScheduleList.tsx`
  - [ ] 表格展示定时任务列表
  - [ ] 显示下次执行时间
  - [ ] 启用/禁用开关
  - [ ] 手动触发按钮
- [ ] 创建 `Schedules/ScheduleForm.tsx`
  - [ ] Cron 表达式输入
  - [ ] Cron 表达式验证
  - [ ] 下次执行时间预览

### Ad-hoc 命令页面
- [ ] 创建 `AdHoc/AdHocExecute.tsx`
  - [ ] 模块选择下拉框
  - [ ] 参数输入
  - [ ] 目标主机选择
  - [ ] 执行按钮
  - [ ] 结果显示
- [ ] 创建 `AdHoc/ModuleDocs.tsx`
  - [ ] 模块列表
  - [ ] 模块文档查看

---

## 阶段五：测试与优化

### 单元测试
- [ ] 创建 `tests/test_ansible_services.py`
  - [ ] 测试加密服务
  - [ ] 测试解密服务
  - [ ] 测试空值处理
- [ ] 创建 `tests/test_ansible_executor.py`
  - [ ] 测试命令构建
  - [ ] 测试结果解析
  - [ ] Mock subprocess
- [ ] 创建 `tests/test_ansible_crud.py`
  - [ ] 测试 CRUD 操作
  - [ ] 测试分页
  - [ ] 测试筛选

### 集成测试
- [ ] 创建 `tests/test_ansible_api.py`
  - [ ] 测试凭证 API
  - [ ] 测试 Playbook API
  - [ ] 测试 Inventory API
  - [ ] 测试任务 API
  - [ ] 测试定时任务 API
- [ ] 测试权限控制
- [ ] 测试审计日志

### 性能测试
- [ ] API 响应时间测试
- [ ] 并发任务测试
- [ ] WebSocket 连接稳定性测试
- [ ] 数据库查询性能测试

### 文档完善
- [ ] 更新 API 文档
- [ ] 更新部署文档
- [ ] 编写用户手册
- [ ] 编写故障排查指南

---

## 部署检查

### Docker 配置
- [ ] 更新 `backend/Dockerfile`
  - [ ] 安装 ansible 包
  - [ ] 安装 sshpass
  - [ ] 创建 ansible 目录
- [ ] 更新 `docker-compose.yml`
  - [ ] 添加 Ansible 目录挂载
  - [ ] 添加环境变量
  - [ ] 更新 Celery 配置

### 环境变量
- [ ] 生成 `ANSIBLE_MASTER_KEY`
- [ ] 配置 `ANSIBLE_HOST_KEY_CHECKING`
- [ ] 配置 `ANSIBLE_STDOUT_CALLBACK`

### 数据初始化
- [ ] 执行数据库迁移
- [ ] 执行权限初始化
- [ ] 导入现有 Playbook
- [ ] 扫描 Inventory 文件

### 安全检查
- [ ] 验证凭证加密
- [ ] 验证临时文件清理
- [ ] 验证权限控制
- [ ] 验证审计日志

---

## 验收标准

### 功能验收
- [ ] 凭证管理功能完整可用
- [ ] Playbook 管理功能完整可用
- [ ] Inventory 管理功能完整可用
- [ ] 任务执行功能完整可用
- [ ] 实时输出功能正常
- [ ] 定时任务功能完整可用
- [ ] Ad-hoc 命令功能完整可用

### 性能验收
- [ ] API 响应时间 < 500ms (P95)
- [ ] 支持 100 个并发任务
- [ ] WebSocket 连接稳定

### 安全验收
- [ ] 凭证加密存储验证通过
- [ ] 临时文件自动清理验证通过
- [ ] 权限控制验证通过
- [ ] 审计日志记录验证通过

### 文档验收
- [ ] API 文档完整
- [ ] 部署文档完整
- [ ] 用户手册完整
