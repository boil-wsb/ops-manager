"""
优化的资产同步服务

优化点：
1. 缓存 Prometheus 节点列表，避免重复查询
2. 并行获取节点指标
3. 批量导入支持
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.models.asset import Asset, AssetSource, AssetStatus, AssetType, SyncStatus
from app.services.prometheus.client import PrometheusClient

logger = get_logger(__name__)


@dataclass
class NodeCache:
    """节点缓存"""

    nodes: list[dict[str, Any]]
    timestamp: datetime
    ttl: timedelta = timedelta(minutes=5)  # 缓存5分钟

    def is_valid(self) -> bool:
        return now_shanghai() - self.timestamp < self.ttl


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
            logger.debug(
                f"使用缓存节点 ({len(self._node_cache.nodes)} 个)", extra={"action": "asset.sync"}
            )
            return self._node_cache.nodes

        logger.debug("从Prometheus获取节点...", extra={"action": "asset.sync"})
        # 合并 Linux（node_exporter）与 Windows（windows_exporter）节点
        linux_nodes = await self.prometheus_client.get_all_nodes()
        windows_nodes = await self.prometheus_client.get_all_windows_nodes()
        nodes = linux_nodes + windows_nodes
        self._node_cache = NodeCache(nodes=nodes, timestamp=now_shanghai())
        logger.info(
            "节点列表获取完成",
            extra={
                "action": "asset.sync",
                "linux_count": len(linux_nodes),
                "windows_count": len(windows_nodes),
                "total": len(nodes),
            },
        )
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
        # Windows 节点使用 windows_* 系列指标，Linux 节点使用 node_* 系列指标
        if node.get("is_windows"):
            metrics_task = self.prometheus_client.get_windows_node_metrics(instance)
        else:
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
            logger.debug(
                f"开始优化同步实例: {instance}",
                extra={"action": "asset.sync", "instance": instance},
            )

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
                logger.error(result["error"], extra={"action": "asset.sync", "instance": instance})
                return result

            # 获取节点详细信息
            node = await self._get_node_details(instance, node)

            # 映射数据
            asset_data = self._map_prometheus_node_to_asset_data(node)
            logger.debug(f"映射资产数据: {asset_data}", extra={"action": "asset.sync"})

            # 检查是否已存在
            existing_asset = await self._get_asset_by_ip(asset_data["ip_address"])
            if not existing_asset and asset_data.get("asset_id"):
                existing_asset = await self._get_asset_by_asset_id(asset_data["asset_id"])

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
            if self.db:
                await self.db.rollback()
            result["error"] = str(e)
            logger.exception(f"同步异常: {e}", extra={"action": "asset.sync", "instance": instance})

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

        logger.debug(
            f"开始批量同步 {len(instances)} 个实例",
            extra={"action": "asset.sync", "total": len(instances)},
        )

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

        logger.debug(f"批量同步完成: {results}", extra={"action": "asset.sync"})
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
            "retired": 0,
            "errors": [],
            "start_time": now_shanghai().isoformat(),
            "end_time": None,
        }

        try:
            nodes = await self._get_cached_nodes(force_refresh=True)
            stats["total"] = len(nodes)

            logger.debug(
                f"开始同步 {len(nodes)} 个节点", extra={"action": "asset.sync", "total": len(nodes)}
            )

            # 收集 Prometheus 中所有 instance 的 IP 集合，用于反向比对
            # Windows 节点 instance 为中文主机名，需优先使用真实 IP
            prometheus_ips = set()
            for node in nodes:
                instance = node.get("instance", "")
                if instance:
                    ip = node.get("ip_address") or self._extract_ip_from_instance(instance)
                    prometheus_ips.add(ip)

            for node in nodes:
                instance = node.get("instance", "")
                if not instance:
                    stats["failed"] += 1
                    stats["errors"].append("Empty instance in node data")
                    continue

                # 同步单个节点，捕获异常以避免污染整个事务
                try:
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
                except Exception as e:
                    # 单个节点同步异常时 rollback 恢复事务状态，继续处理其他节点
                    await self.db.rollback()
                    stats["failed"] += 1
                    stats["errors"].append(f"{instance}: {str(e)}")
                    logger.error(
                        f"同步单节点异常: {instance}: {e}",
                        extra={"action": "asset.sync", "instance": instance},
                    )

            # 反向比对：将 Prometheus 中已不存在的资产标记为 RETIRED
            # 放在独立 try 块中，不受上面单节点同步错误影响
            try:
                retired_result = await self._retire_stale_prometheus_assets(prometheus_ips)
                stats["retired"] = retired_result
            except Exception as e:
                logger.error(
                    f"标记失活资产异常: {e}",
                    extra={"action": "asset.retire"},
                )
                stats["errors"].append(f"Retire error: {str(e)}")

            stats["end_time"] = now_shanghai().isoformat()
            logger.info(
                "同步完成",
                extra={
                    "action": "asset.sync",
                    "total": stats["total"],
                    "created_count": stats["created"],
                    "updated_count": stats["updated"],
                    "failed_count": stats["failed"],
                    "retired_count": stats["retired"],
                },
            )

        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(f"Sync error: {str(e)}")
            stats["end_time"] = now_shanghai().isoformat()
            logger.error(f"全量同步失败: {e}", extra={"action": "asset.sync"})

        return stats

    async def _retire_stale_prometheus_assets(self, prometheus_ips: set[str]) -> int:
        """
        将 Prometheus 中已不存在的资产标记为 RETIRED

        查询数据库中所有 source=PROMETHEUS 的资产，如果其 IP 不在
        当前 Prometheus 节点列表中，则将状态标记为 RETIRED，
        sync_status 标记为 ERROR。

        Args:
            prometheus_ips: Prometheus 当前所有节点的 IP 集合

        Returns:
            标记为 RETIRED 的资产数量
        """
        result = await self.db.execute(
            select(Asset).where(
                Asset.source == AssetSource.PROMETHEUS,
                Asset.status != AssetStatus.RETIRED,
                Asset.asset_type != AssetType.TERMINAL,
            )
        )
        prometheus_assets = result.scalars().all()

        retired_count = 0
        for asset in prometheus_assets:
            try:
                if asset.ip_address not in prometheus_ips:
                    asset.status = AssetStatus.RETIRED
                    asset.sync_status = SyncStatus.ERROR
                    asset.last_sync_time = now_shanghai()
                    retired_count += 1
                    logger.info(
                        f"资产已从 Prometheus 消失，标记为 RETIRED: {asset.ip_address}",
                        extra={
                            "action": "asset.retire",
                            "ip_address": asset.ip_address,
                            "asset_id": asset.asset_id,
                        },
                    )
            except Exception as e:
                logger.error(
                    f"标记退役资产异常: {asset.ip_address}: {e}",
                    extra={
                        "action": "asset.retire",
                        "ip_address": asset.ip_address,
                    },
                )
                continue

        if retired_count > 0:
            try:
                await self.db.commit()
            except Exception as e:
                await self.db.rollback()
                logger.error(f"提交退役资产事务异常: {e}", extra={"action": "asset.retire"})
                raise

        return retired_count

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
        # Windows 节点 instance 为中文主机名，优先使用预解析的真实 IP
        ip_address = node.get("ip_address") or self._extract_ip_from_instance(instance)
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
            "last_sync_time": now_shanghai().isoformat(),
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

        result = await self.db.execute(select(Asset).where(Asset.ip_address == ip_address))
        return result.scalar_one_or_none()

    async def _get_asset_by_asset_id(self, asset_id: str) -> Asset | None:
        """根据 asset_id 查找资产"""
        if not asset_id:
            return None

        result = await self.db.execute(select(Asset).where(Asset.asset_id == asset_id))
        return result.scalar_one_or_none()

    async def _update_asset(
        self, existing_asset: Asset, asset_data: dict[str, Any], node: dict[str, Any], instance: str
    ) -> None:
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
            "last_sync_time": now_shanghai(),
        }

        for field, value in update_data.items():
            if value is not None:
                setattr(existing_asset, field, value)

        await self.db.commit()
        await self.db.refresh(existing_asset)
        logger.debug(
            f"更新资产: {existing_asset.asset_id}",
            extra={"action": "asset.update", "asset_id": existing_asset.asset_id},
        )

    async def _create_asset(
        self, asset_data: dict[str, Any], node: dict[str, Any], instance: str
    ) -> Asset:
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
            last_sync_time=now_shanghai(),
        )

        self.db.add(new_asset)
        await self.db.commit()
        await self.db.refresh(new_asset)
        logger.debug(
            f"创建资产: {new_asset.asset_id}",
            extra={"action": "asset.create", "asset_id": new_asset.asset_id},
        )
        return new_asset
