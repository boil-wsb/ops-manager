"""
资产同步服务

Phase 2 实现：
- 从 Prometheus 同步资产数据到数据库
- 支持增量同步和全量同步
- 处理资产变更事件
"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.models.asset import Asset, AssetStatus, AssetType
from app.services.prometheus.client import PrometheusClient

logger = get_logger(__name__)


class AssetSyncService:
    """资产同步服务类"""

    def __init__(self, db: AsyncSession, prometheus_client: PrometheusClient | None = None):
        """
        初始化资产同步服务

        Args:
            db: 数据库会话
            prometheus_client: Prometheus 客户端实例，如果为 None 则创建新实例
        """
        self.db = db
        self.prometheus_client = prometheus_client or PrometheusClient()

    def _extract_ip_from_instance(self, instance: str) -> str:
        """
        从 instance 字符串中提取 IP 地址

        Args:
            instance: instance 字符串 (格式: IP:Port)

        Returns:
            IP 地址
        """
        if not instance:
            return ""
        # 处理 IP:Port 格式
        if ":" in instance:
            return instance.split(":")[0]
        return instance

    def _map_job_to_asset_type(self, job: str) -> AssetType:
        """
        将 Prometheus job 映射为资产类型

        Args:
            job: Prometheus job 名称

        Returns:
            资产类型枚举
        """
        job_mapping = {
            "linux服务器监控": AssetType.SERVER,
            "windows服务器监控": AssetType.SERVER,
            "ops-服务器监控": AssetType.SERVER,
            "ops-monitor": AssetType.SERVER,
            "pd4-monitor": AssetType.SERVER,
            "pd3-monitor": AssetType.SERVER,
            "pd5-monitor": AssetType.SERVER,
            "mysql": AssetType.SERVER,  # 数据库也映射为 SERVER 类型
            "springboot-app": AssetType.VM,
            "域名过期监控": AssetType.NETWORK,
            "pushgateway": AssetType.SERVER,
        }

        # 尝试精确匹配
        if job in job_mapping:
            return job_mapping[job]

        # 尝试前缀匹配
        for key, value in job_mapping.items():
            if job.startswith(key.replace("-monitor", "")):
                return value

        # 根据 job 名称关键字判断
        job_lower = job.lower()
        if "server" in job_lower or "linux" in job_lower or "windows" in job_lower:
            return AssetType.SERVER
        elif "vm" in job_lower or "virtual" in job_lower:
            return AssetType.VM
        elif "network" in job_lower or "switch" in job_lower or "router" in job_lower:
            return AssetType.NETWORK
        elif "storage" in job_lower or "nas" in job_lower or "san" in job_lower:
            return AssetType.STORAGE

        return AssetType.SERVER  # 默认类型

    def _map_status(self, status: str) -> AssetStatus:
        """
        将 Prometheus 状态映射为资产状态

        Args:
            status: Prometheus 状态 (up/down/unknown)

        Returns:
            资产状态枚举
        """
        status_mapping = {
            "up": AssetStatus.ACTIVE,
            "down": AssetStatus.OFFLINE,
            "unknown": AssetStatus.OFFLINE,
        }
        return status_mapping.get(status, AssetStatus.OFFLINE)

    def _normalize_os_type(self, sysname: str) -> str:
        """
        标准化操作系统类型

        Args:
            sysname: 系统名称

        Returns:
            标准化后的 OS 类型 (Linux/Windows/Other)
        """
        if not sysname:
            return "Other"

        sysname_lower = sysname.lower()
        if "linux" in sysname_lower:
            return "Linux"
        elif "windows" in sysname_lower or "win32" in sysname_lower or "win64" in sysname_lower:
            return "Windows"
        elif "darwin" in sysname_lower or "mac" in sysname_lower:
            return "macOS"
        else:
            return "Other"

    def _generate_asset_id(self, nodename: str, ip_address: str) -> str:
        """
        生成资产 ID

        Args:
            nodename: 节点名称
            ip_address: IP 地址

        Returns:
            资产 ID
        """
        if nodename and nodename.strip():
            return nodename.strip()
        return ip_address

    async def _get_asset_by_ip(self, ip_address: str) -> Asset | None:
        """
        根据 IP 地址查找资产

        Args:
            ip_address: IP 地址

        Returns:
            资产对象或 None
        """
        if not ip_address:
            return None

        result = await self.db.execute(select(Asset).where(Asset.ip_address == ip_address))
        return result.scalar_one_or_none()

    def _map_prometheus_node_to_asset_data(self, node: dict[str, Any]) -> dict[str, Any]:
        """
        将 Prometheus 节点数据映射为 Asset 模型字段

        Args:
            node: Prometheus 节点数据

        Returns:
            Asset 模型字段字典
        """
        instance = node.get("instance", "")
        ip_address = self._extract_ip_from_instance(instance)
        nodename = node.get("nodename", "")
        sysname = node.get("sysname", "")
        release = node.get("release", "")
        machine = node.get("machine", "")
        job = node.get("job", "")
        status = node.get("status", "unknown")

        # 生成资产 ID
        asset_id = self._generate_asset_id(nodename, ip_address)

        # 构建 labels_data
        labels_data = {
            "machine": machine,
            "env": node.get("env", ""),
            "source": "prometheus",
            "prometheus_instance": instance,
            "sync_status": "synced",
            "last_sync_time": now_shanghai().isoformat(),
        }

        # 构建资产数据
        asset_data = {
            "asset_id": asset_id,
            "name": nodename if nodename else ip_address,
            "asset_type": self._map_job_to_asset_type(job),
            "status": self._map_status(status),
            "ip_address": ip_address,
            "os_type": self._normalize_os_type(sysname),
            "os_version": release,
            "labels_data": labels_data,
            "description": f"Synced from Prometheus (job: {job})",
        }

        return asset_data

    async def sync_single_asset(self, instance: str) -> dict[str, Any]:
        """
        同步单个节点

        Args:
            instance: 节点实例地址 (IP:Port)

        Returns:
            同步结果字典，包含 success, action, asset, error 等字段
        """
        result = {
            "success": False,
            "action": None,  # "created", "updated", "failed"
            "asset": None,
            "error": None,
        }

        try:
            logger.info(f"开始同步实例: {instance}", extra={"action": "asset.sync", "instance": instance})

            ip_address = self._extract_ip_from_instance(instance)
            logger.info(f"提取IP: {ip_address}", extra={"action": "asset.sync"})

            logger.info("从Prometheus获取节点...", extra={"action": "asset.sync"})
            nodes = await self.prometheus_client.get_all_nodes()
            logger.info(f"从Prometheus获取到 {len(nodes)} 个节点", extra={"action": "asset.sync"})

            node = None
            for n in nodes:
                if n.get("instance") == instance:
                    node = n
                    break

            if not node:
                result["error"] = f"Node not found in Prometheus: {instance}"
                logger.error(result["error"], extra={"action": "asset.sync", "instance": instance})
                return result

            logger.info(f"找到节点: {node}", extra={"action": "asset.sync"})

            logger.info("获取节点状态...", extra={"action": "asset.sync"})
            status = await self.prometheus_client.get_node_status(instance)
            node["status"] = status
            logger.info(f"节点状态: {status}", extra={"action": "asset.sync"})

            logger.info("获取节点指标...", extra={"action": "asset.sync"})
            metrics = await self.prometheus_client.get_node_metrics(instance)
            node.update(metrics)
            logger.info(f"节点指标: {metrics}", extra={"action": "asset.sync"})

            asset_data = self._map_prometheus_node_to_asset_data(node)
            logger.info(f"映射资产数据: {asset_data}", extra={"action": "asset.sync"})

            logger.info(f"检查已有资产 IP: {asset_data['ip_address']}", extra={"action": "asset.sync"})
            existing_asset = await self._get_asset_by_ip(asset_data["ip_address"])
            logger.info(f"已有资产: {existing_asset}", extra={"action": "asset.sync"})

            if existing_asset:
                # 更新现有资产
                from app.models.asset import AssetSource, SyncStatus

                update_data = {
                    "name": asset_data["name"],
                    "status": asset_data["status"],
                    "os_type": asset_data["os_type"],
                    "os_version": asset_data["os_version"],
                    "labels_data": asset_data["labels_data"],
                    "cpu_cores": node.get("cpu_cores"),
                    "memory_gb": node.get("memory_gb"),
                    "disk_gb": node.get("disk_gb"),
                    "source": AssetSource.PROMETHEUS.value,
                    "sync_status": SyncStatus.SYNCED.value,
                    "prometheus_instance": instance,
                    "last_sync_time": now_shanghai(),
                }

                # 更新字段
                for field, value in update_data.items():
                    if value is not None:
                        setattr(existing_asset, field, value)

                await self.db.commit()
                await self.db.refresh(existing_asset)

                result["success"] = True
                result["action"] = "updated"
                result["asset"] = existing_asset
                logger.info(
                    f"更新资产: {existing_asset.asset_id} (IP: {asset_data['ip_address']})",
                    extra={"action": "asset.update", "asset_id": existing_asset.asset_id, "ip_address": asset_data['ip_address']},
                )
            else:
                logger.info("创建新资产...", extra={"action": "asset.create"})
                from app.models.asset import AssetSource, SyncStatus

                new_asset = Asset(
                    asset_id=asset_data["asset_id"],
                    name=asset_data["name"],
                    asset_type=asset_data["asset_type"],
                    status=asset_data["status"],
                    ip_address=asset_data["ip_address"],
                    os_type=asset_data["os_type"],
                    os_version=asset_data["os_version"],
                    labels_data=asset_data["labels_data"],
                    cpu_cores=node.get("cpu_cores"),
                    memory_gb=node.get("memory_gb"),
                    disk_gb=node.get("disk_gb"),
                    description=asset_data["description"],
                    source=AssetSource.PROMETHEUS.value,
                    sync_status=SyncStatus.SYNCED.value,
                    prometheus_instance=instance,
                    last_sync_time=now_shanghai(),
                )

                self.db.add(new_asset)
                logger.info("资产已添加到会话，提交中...", extra={"action": "asset.create"})
                await self.db.commit()
                logger.info("提交成功，刷新中...", extra={"action": "asset.create"})
                await self.db.refresh(new_asset)
                logger.info(f"刷新成功，资产ID: {new_asset.id}", extra={"action": "asset.create"})

                result["success"] = True
                result["action"] = "created"
                result["asset"] = new_asset
                logger.info(
                    f"创建资产: {new_asset.asset_id} (IP: {asset_data['ip_address']})",
                    extra={"action": "asset.create", "asset_id": new_asset.asset_id, "ip_address": asset_data['ip_address']},
                )

        except Exception as e:
            result["error"] = str(e)
            logger.exception(f"同步异常: {e}", extra={"action": "asset.sync", "instance": instance})
            logger.error(f"同步资产失败: {instance}: {e}", extra={"action": "asset.sync", "instance": instance})

        return result

    async def sync_all_assets(self) -> dict[str, Any]:
        """
        从 Prometheus 获取所有节点并同步到数据库

        Returns:
            同步统计信息字典，包含 total, created, updated, failed, errors 等字段
        """
        stats = {
            "total": 0,
            "created": 0,
            "updated": 0,
            "failed": 0,
            "errors": [],
            "start_time": now_shanghai().isoformat(),
            "end_time": None,
        }

        try:
            # 获取所有节点
            nodes = await self.prometheus_client.get_all_nodes()
            stats["total"] = len(nodes)

            logger.info(f"开始同步 {len(nodes)} 个节点", extra={"action": "asset.sync", "total": len(nodes)})

            for node in nodes:
                instance = node.get("instance", "")
                if not instance:
                    stats["failed"] += 1
                    stats["errors"].append("Empty instance in node data")
                    continue

                # 同步单个节点
                result = await self.sync_single_asset(instance)

                if result["success"]:
                    if result["action"] == "created":
                        stats["created"] += 1
                    elif result["action"] == "updated":
                        stats["updated"] += 1
                else:
                    stats["failed"] += 1
                    if result["error"]:
                        stats["errors"].append(f"{instance}: {result['error']}")

            stats["end_time"] = now_shanghai().isoformat()
            logger.info(
                f"同步完成",
                extra={"action": "asset.sync", "total": stats['total'], "created_count": stats['created'], "updated_count": stats['updated'], "failed_count": stats['failed']},
            )

        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(f"Sync error: {str(e)}")
            stats["end_time"] = now_shanghai().isoformat()
            logger.error(f"全量同步失败: {e}", extra={"action": "asset.sync"})

        return stats


async def sync_assets_from_prometheus(
    db: AsyncSession, prometheus_client: PrometheusClient | None = None
) -> dict[str, Any]:
    """
    从 Prometheus 同步资产的便捷函数

    Args:
        db: 数据库会话
        prometheus_client: Prometheus 客户端实例

    Returns:
        同步统计信息
    """
    service = AssetSyncService(db, prometheus_client)
    return await service.sync_all_assets()
