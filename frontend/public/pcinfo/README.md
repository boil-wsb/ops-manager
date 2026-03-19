# PC Info Collector - 终端运维自动化采集工具

[![Version](https://img.shields.io/badge/version-5.0.0-blue.svg)](https://github.com/yourusername/pc-info-collector)
[![Platform](https://img.shields.io/badge/platform-Windows-green.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

PC Info Collector 是一个用于自动化采集 Windows 终端系统信息的工具，支持将数据上报到 Prometheus Pushgateway，便于集中监控和管理。

## 功能特性

- **模块化设计** - 按需启用/禁用采集模块
- **Prometheus 兼容** - 原生支持 Prometheus metrics 格式
- **定时任务** - 支持 Windows 任务计划程序定时执行
- **后台运行** - 静默执行，不影响用户工作
- **UTF-8 编码** - 完美支持中文系统信息
- **灵活配置** - 通过 JSON 配置文件自定义行为

## 采集指标

### 系统信息
- 计算机名称、UUID、序列号
- 操作系统版本、安装日期
- 主板、BIOS 信息

### 硬件信息
- CPU 型号、核心数、使用率
- 内存容量、使用率、内存条数量
- 硬盘容量、使用率、物理磁盘数
- 显卡型号、显存

### 软件信息
- 已安装软件列表
- 系统更新补丁
- 开机启动项

### 网络信息
- 网卡配置、IP 地址、MAC 地址
- 默认网关、DHCP 状态

### 其他信息
- 本地用户账户
- 系统环境变量
- 运行中的进程

## 快速开始

### 1. 配置文件

编辑 `Conf.json` 配置文件：

```json
{
  "CustInfo": {
    "id": "your_customer_id"
  },
  "Modules": {
    "Systeminfo": true,
    "Hardware": true,
    "MEMinfo": true,
    "Diskinfo": true,
    "Softwareinfo": true,
    "Netinfo": true,
    "Hotfixinfo": true,
    "Processinfo": true,
    "Userinfo": true,
    "Environment": true,
    "Startupinfo": true
  },
  "HttpReport": {
    "Enabled": true,
    "Endpoint": "http://192.168.23.31:9091/metrics/job/pcinfo",
    "RetryCount": 3,
    "Timeout": 30000,
    "Format": "prometheus"
  }
}
```

### 2. 手动运行

```cmd
cscript PC_5.0.0_modular.vbs
```

### 3. 定时任务设置

#### 方法1：使用 PowerShell 脚本（推荐）

以管理员身份运行 PowerShell：

```powershell
# 创建系统启动时运行 + 每小时运行的任务
powershell -ExecutionPolicy Bypass -File setup_scheduled_tasks.ps1
```

#### 方法2：手动创建任务

```cmd
# 系统启动时运行
schtasks /create /tn "PC_Info_Collector_Startup" /tr "cscript.exe D:\path\to\PC_5.0.0_modular.vbs //B //Nologo" /sc onstart /ru SYSTEM

# 每小时运行
schtasks /create /tn "PC_Info_Collector_Hourly" /tr "cscript.exe D:\path\to\PC_5.0.0_modular.vbs //B //Nologo" /sc hourly /ru SYSTEM
```

## 项目结构

```
pc_script/
├── PC_5.0.0_modular.vbs      # 主程序
├── Conf.json                  # 配置文件
├── setup_scheduled_tasks.ps1  # 定时任务设置脚本
├── schedule_task.ps1          # 单任务设置脚本
├── check_tasks.bat            # 任务状态检查脚本
├── README.md                  # 本文件
└── PcInfo/                    # 输出目录
    └── 20260311/              # 日期目录
        ├── PcInfo-Systeminfo-xxx.csv
        ├── PcInfo-Hardware-xxx.csv
        ├── PcInfo-MEMinfo-xxx.csv
        └── ...
```

## Prometheus Metrics

采集的指标将以以下格式推送到 Pushgateway：

```prometheus
# HELP pc_info Basic system info
# TYPE pc_info gauge
pc_info{hostname="DESKTOP-XXX",uuid="...",serial="...",customer="boil"} 1

# HELP pc_cpu_usage_percent CPU usage percentage
# TYPE pc_cpu_usage_percent gauge
pc_cpu_usage_percent{hostname="DESKTOP-XXX"} 15.5

# HELP pc_memory_usage_percent Memory usage percentage
# TYPE pc_memory_usage_percent gauge
pc_memory_usage_percent{hostname="DESKTOP-XXX"} 45.2

# HELP pc_disk_usage_percent Disk usage percentage
# TYPE pc_disk_usage_percent gauge
pc_disk_usage_percent{hostname="DESKTOP-XXX",drive="C:"} 65.8
```

## 管理命令

### 查看任务状态

```powershell
# 查看所有 PC_Info 任务
Get-ScheduledTask | Where-Object { $_.TaskName -like 'PC_Info_Collector*' }

# 查看任务详细信息
schtasks /query /tn "PC_Info_Collector_Startup" /fo LIST /v
```

### 启动/停止任务

```powershell
# 立即运行任务
Start-ScheduledTask -TaskName 'PC_Info_Collector_Startup'

# 停止任务
Stop-ScheduledTask -TaskName 'PC_Info_Collector_Hourly'
```

### 删除任务

```powershell
# 删除所有 PC_Info 任务
Get-ScheduledTask | Where-Object { $_.TaskName -like 'PC_Info_Collector*' } | Unregister-ScheduledTask -Confirm:$false
```

## 系统要求

- Windows 7/8/10/11
- Windows Server 2008/2012/2016/2019/2022
- PowerShell 3.0 或更高版本（用于定时任务设置）
- 管理员权限（用于创建定时任务）

## 注意事项

1. **管理员权限** - 创建定时任务需要管理员权限
2. **Pushgateway** - 确保 Pushgateway 服务可访问
3. **防火墙** - 确保防火墙允许访问 Pushgateway 端口（默认 9091）
4. **编码** - 所有 CSV 文件使用 UTF-8 编码，避免中文乱码

## 故障排除

### 任务创建失败

- 确保以管理员身份运行 PowerShell
- 检查执行策略：`Get-ExecutionPolicy`，如需修改：`Set-ExecutionPolicy RemoteSigned`

### Pushgateway 上报失败

- 检查网络连接：`ping 192.168.23.31`
- 检查 Pushgateway 服务状态
- 查看错误日志：检查 `PcInfo/日期/` 目录下的缓存文件

## 更新日志

### v5.0.0 (2026-03-11)

- 重构为模块化架构
- 添加 Prometheus metrics 支持
- 添加 HTTP 上报功能
- 修复 UTF-8 编码问题
- 优化输出目录结构

### v4.3.2 (2021-10-27)

- 基础信息采集功能
- CSV 格式输出

