"""
优化的资产同步服务

优化点：
1. 缓存 Prometheus 节点列表，避免重复查询
2. 并行获取节点指标
3. 批量导入支持
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetSource, AssetStatus, AssetType, SyncStatus
from app.services.prometheus.client import PrometheusClient

logger = logging.getLogger(__name__)


@dataclass
class NodeCache:
    """节点缓存"""
    nodes: list[dict[str, Any]]
    timestamp: datetime
    ttl: timedelta = timedelta(minutes=5)  # 缓存5分钟

    def is_valid(self) -> bool:
        return datetime.utcnow() - self.timestamp < self.ttl


class OptimizedAssetSyncService:
    """优化的资产同步服务类"""

    # 类级别的缓存
    _node_cache: NodeCache | None = None

    def __init__(self, db: AsyncSession, prometheus_client: PrometheusClient | None = None):
        self.db = db
        self.prometheus_client = prometheus_client or PrometheusClient()

    async def _get_cached_nodes(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """
        获取缓存的节点列表

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            节点列表
        """
        if not force_refresh and self._node_cache and self._node_cache.is_valid():
            logger.info(f"Using cached nodes ({len(self._node_cache.nodes)} nodes)")
            return self._node_cache.nodes

        logger.info("Fetching nodes from Prometheus...")
        nodes = await self.prometheus_client.get_all_nodes()
        self._node_cache = NodeCache(nodes=nodes, timestamp=datetime.utcnow())
        logger.info(f"Cached {len(nodes)} nodes from Prometheus")
        return nodes

    async def _get_node_details(self, instance: str, node: dict[str, Any]) -> dict[str, Any]:
        """
        获取节点详细信息（并行查询）

        Args:
            instance: 节点实例地址
            node: 节点基本信息

        Returns:
            包含详细信息的节点数据
        """
        # 并行获取状态和指标
        status_task = self.prometheus_client.get_node_status(instance)
        metrics_task = self.prometheus_client.get_node_metrics(instance)

        status, metrics = await asyncio.gather(status_task, metrics_task)

        node["status"] = status
        node.update(metrics)
        return node

    async def sync_single_asset(self, instance: str, force_refresh: bool = False) -> dict[str, Any]:
        """
        同步单个节点（优化版）

        Args:
            instance: 节点实例地址 (IP:Port)
            force_refresh: 是否强制刷新节点缓存

        Returns:
            同步结果字典
        """
        result = {
            "success": False,
            "action": None,
            "asset": None,
            "error": None,
        }

        try:
            logger.info(f"Starting optimized sync for instance: {instance}")

            # 从缓存获取节点列表
            nodes = await self._get_cached_nodes(force_refresh=force_refresh)

            # 查找目标节点
            node = None
            for n in nodes:
                if n.get("instance") == instance:
                    node = n
                    break

            if not node:
                result["error"] = f"Node not found in Prometheus: {instance}"
                logger.error(result["error"])
                return result

            # 获取节点详细信息
            node = await self._get_node_details(instance, node)

            # 映射数据
            asset_data = self._map_prometheus_node_to_asset_data(node)
            logger.info(f"Mapped asset data: {asset_data}")

            # 检查是否已存在
            existing_asset = await self._get_asset_by_ip(asset_data["ip_address"])

            if existing_asset:
                # 更新现有资产
                await self._update_asset(existing_asset, asset_data, node, instance)
                result["success"] = True
                result["action"] = "updated"
                result["asset"] = existing_asset
            else:
                # 创建新资产
                new_asset = await self._create_asset(asset_data, node, instance)
                result["success"] = True
                result["action"] = "created"
                result["asset"] = new_asset

        except Exception as e:
            result["error"] = str(e)
            logger.exception(f"Exception in sync_single_asset: {e}")

        return result

    async def batch_sync_assets(self, instances: list[str]) -> dict[str, Any]:
        """
        批量同步多个节点

        Args:
            instances: 节点实例地址列表

        Returns:
            批量同步结果
        """
        results = {
            "total": len(instances),
            "success": 0,
            "failed": 0,
            "created": 0,
            "updated": 0,
            "errors": [],
        }

        logger.info(f"Starting batch sync for {len(instances)} instances")

        # 先刷新缓存，确保数据最新
        await self._get_cached_nodes(force_refresh=True)

        # 串行处理（避免数据库冲突）
        for instance in instances:
            try:
                result = await self.sync_single_asset(instance, force_refresh=False)
                if result["success"]:
                    results["success"] += 1
                    if result["action"] == "created":
                        results["created"] += 1
                    elif result["action"] == "updated":
                        results["updated"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{instance}: {result.get('error')}")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{instance}: {str(e)}")

        logger.info(f"Batch sync completed: {results}")
        return results

    async def sync_all_assets(self) -> dict[str, Any]:
        """
        从 Prometheus 获取所有节点并同步到数据库

        Returns:
            同步统计信息字典
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
            nodes = await self._get_cached_nodes(force_refresh=True)
            stats["total"] = len(nodes)

            logger.info(f"Starting sync for {len(nodes)} nodes from Prometheus")

            for node in nodes:
                instance = node.get("instance", "")
                if not instance:
                    stats["failed"] += 1
                    stats["errors"].append("Empty instance in node data")
                    continue

                result = await self.sync_single_asset(instance, force_refresh=False)

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

    def _extract_ip_from_instance(self, instance: str) -> str:
        """从 instance 字符串中提取 IP 地址"""
        if not instance:
            return ""
        if ":" in instance:
            return instance.split(":")[0]
        return instance

    def _map_job_to_asset_type(self, job: str) -> AssetType:
        """将 Prometheus job 映射为资产类型"""
        job_mapping = {
            "linux服务器监控": AssetType.SERVER,
            "windows服务器监控": AssetType.SERVER,
            "ops-服务器监控": AssetType.SERVER,
            "ops-monitor": AssetType.SERVER,
            "pd4-monitor": AssetType.SERVER,
            "pd3-monitor": AssetType.SERVER,
            "pd5-monitor": AssetType.SERVER,
            "mysql": AssetType.SERVER,
            "springboot-app": AssetType.VM,
            "域名过期监控": AssetType.NETWORK,
            "pushgateway": AssetType.SERVER,
        }

        if job in job_mapping:
            return job_mapping[job]

        for key, value in job_mapping.items():
            if job.startswith(key.replace("-monitor", "")):
                return value

        job_lower = job.lower()
        if "server" in job_lower or "linux" in job_lower or "windows" in job_lower:
            return AssetType.SERVER
        elif "vm" in job_lower or "virtual" in job_lower:
            return AssetType.VM
        elif "network" in job_lower or "switch" in job_lower or "router" in job_lower:
            return AssetType.NETWORK
        elif "storage" in job_lower or "nas" in job_lower or "san" in job_lower:
            return AssetType.STORAGE

        return AssetType.SERVER

    def _map_status(self, status: str) -> AssetStatus:
        """将 Prometheus 状态映射为资产状态"""
        status_mapping = {
            "up": AssetStatus.ACTIVE,
            "down": AssetStatus.OFFLINE,
            "unknown": AssetStatus.OFFLINE,
        }
        return status_mapping.get(status, AssetStatus.OFFLINE)

    def _normalize_os_type(self, sysname: str) -> str:
        """标准化操作系统类型"""
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
        """生成资产 ID"""
        if nodename and nodename.strip():
            return nodename.strip()
        return ip_address

    def _map_prometheus_node_to_asset_data(self, node: dict[str, Any]) -> dict[str, Any]:
        """将 Prometheus 节点数据映射为 Asset 模型字段"""
        instance = node.get("instance", "")
        ip_address = self._extract_ip_from_instance(instance)
        nodename = node.get("nodename", "")
        sysname = node.get("sysname", "")
        release = node.get("release", "")
        machine = node.get("machine", "")
        job = node.get("job", "")
        status = node.get("status", "unknown")

        asset_id = self._generate_asset_id(nodename, ip_address)

        labels_data = {
            "machine": machine,
            "env": node.get("env", ""),
            "source": "prometheus",
            "prometheus_instance": instance,
            "sync_status": "synced",
            "last_sync_time": datetime.utcnow().isoformat(),
        }

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

    async def _get_asset_by_ip(self, ip_address: str) -> Asset | None:
        """根据 IP 地址查找资产"""
        if not ip_address:
            return None

        result = await self.db.execute(
            select(Asset).where(Asset.ip_address == ip_address)
        )
        return result.scalar_one_or_none()

    async def _update_asset(self, existing_asset: Asset, asset_data: dict[str, Any],
                           node: dict[str, Any], instance: str) -> None:
        """更新现有资产"""
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

        for field, value in update_data.items():
            if value is not None:
                setattr(existing_asset, field, value)

        await self.db.commit()
        await self.db.refresh(existing_asset)
        logger.info(f"Updated asset: {existing_asset.asset_id}")

    async def _create_asset(self, asset_data: dict[str, Any],
                           node: dict[str, Any], instance: str) -> Asset:
        """创建新资产"""
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
        await self.db.commit()
        await self.db.refresh(new_asset)
        logger.info(f"Created asset: {new_asset.asset_id}")
        return new_asset
