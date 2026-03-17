"""
资产同步服务

Phase 2 实现：
- 从 Prometheus 同步资产数据到数据库
- 支持增量同步和全量同步
- 处理资产变更事件
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.prometheus.client import PrometheusClient, get_prometheus_client
from app.models.asset import Asset, AssetStatus, AssetType
from app.crud.crud_asset import crud_asset

logger = logging.getLogger(__name__)


class AssetSyncService:
    """资产同步服务类"""

    def __init__(self, db: AsyncSession, prometheus_client: Optional[PrometheusClient] = None):
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

    async def _get_asset_by_ip(self, ip_address: str) -> Optional[Asset]:
        """
        根据 IP 地址查找资产

        Args:
            ip_address: IP 地址

        Returns:
            资产对象或 None
        """
        if not ip_address:
            return None

        result = await self.db.execute(
            select(Asset).where(Asset.ip_address == ip_address)
        )
        return result.scalar_one_or_none()

    def _map_prometheus_node_to_asset_data(self, node: Dict[str, Any]) -> Dict[str, Any]:
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
            "last_sync_time": datetime.utcnow().isoformat(),
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

    async def sync_single_asset(self, instance: str) -> Dict[str, Any]:
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
            logger.info(f"Starting sync for instance: {instance}")

            # 获取节点信息
            ip_address = self._extract_ip_from_instance(instance)
            logger.info(f"Extracted IP: {ip_address}")

            # 从 Prometheus 获取节点详细信息
            logger.info("Fetching nodes from Prometheus...")
            nodes = await self.prometheus_client.get_all_nodes()
            logger.info(f"Found {len(nodes)} nodes from Prometheus")

            node = None
            for n in nodes:
                if n.get("instance") == instance:
                    node = n
                    break

            if not node:
                result["error"] = f"Node not found in Prometheus: {instance}"
                logger.error(result["error"])
                return result

            logger.info(f"Found node: {node}")

            # 获取节点状态
            logger.info("Fetching node status...")
            status = await self.prometheus_client.get_node_status(instance)
            node["status"] = status
            logger.info(f"Node status: {status}")

            # 获取节点指标
            logger.info("Fetching node metrics...")
            metrics = await self.prometheus_client.get_node_metrics(instance)
            node.update(metrics)
            logger.info(f"Node metrics: {metrics}")

            # 映射数据
            asset_data = self._map_prometheus_node_to_asset_data(node)
            logger.info(f"Mapped asset data: {asset_data}")

            # 检查是否已存在（通过 IP 地址）
            logger.info(f"Checking for existing asset with IP: {asset_data['ip_address']}")
            existing_asset = await self._get_asset_by_ip(asset_data["ip_address"])
            logger.info(f"Existing asset: {existing_asset}")

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
                    "last_sync_time": datetime.utcnow(),
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
                logger.info(f"Updated asset: {existing_asset.asset_id} (IP: {asset_data['ip_address']})")
            else:
                # 创建新资产
                logger.info("Creating new asset...")
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
                    last_sync_time=datetime.utcnow(),
                )

                self.db.add(new_asset)
                logger.info("Asset added to session, committing...")
                await self.db.commit()
                logger.info("Commit successful, refreshing...")
                await self.db.refresh(new_asset)
                logger.info(f"Refresh successful, asset ID: {new_asset.id}")

                result["success"] = True
                result["action"] = "created"
                result["asset"] = new_asset
                logger.info(f"Created asset: {new_asset.asset_id} (IP: {asset_data['ip_address']})")

        except Exception as e:
            result["error"] = str(e)
            logger.exception(f"Exception in sync_single_asset: {e}")
            logger.error(f"Failed to sync asset {instance}: {e}")

        return result

    async def sync_all_assets(self) -> Dict[str, Any]:
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
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
        }

        try:
            # 获取所有节点
            nodes = await self.prometheus_client.get_all_nodes()
            stats["total"] = len(nodes)

            logger.info(f"Starting sync for {len(nodes)} nodes from Prometheus")

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

            stats["end_time"] = datetime.utcnow().isoformat()
            logger.info(
                f"Sync completed. Total: {stats['total']}, "
                f"Created: {stats['created']}, Updated: {stats['updated']}, "
                f"Failed: {stats['failed']}"
            )

        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(f"Sync error: {str(e)}")
            stats["end_time"] = datetime.utcnow().isoformat()
            logger.error(f"Failed to sync all assets: {e}")

        return stats


async def sync_assets_from_prometheus(
    db: AsyncSession,
    prometheus_client: Optional[PrometheusClient] = None
) -> Dict[str, Any]:
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
