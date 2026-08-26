"""
Prometheus HTTP API 客户端实现
"""

import asyncio
import contextlib
from datetime import datetime
from typing import Any

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.core.tz import from_timestamp, now_shanghai

logger = get_logger(__name__)


class PrometheusClient:
    """Prometheus HTTP API 客户端"""

    def __init__(self, base_url: str = None, timeout: int = None):
        self.base_url = base_url or settings.prometheus_url
        self.timeout = timeout or settings.prometheus_timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()

    async def query(self, query: str) -> dict[str, Any]:
        """
        执行 Prometheus 查询

        Args:
            query: PromQL 查询语句

        Returns:
            查询结果字典
        """
        url = f"{self.base_url}/api/v1/query"
        params = {"query": query}

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                logger.error(f"查询失败: {data.get('error')}", extra={"action": "prometheus.query"})
                return {"status": "error", "error": data.get("error")}

            return data
        except httpx.TimeoutException:
            logger.error(f"查询超时: {query}", extra={"action": "prometheus.query", "query": query})
            return {"status": "error", "error": "timeout"}
        except Exception as e:
            logger.error(f"查询异常: {e}", extra={"action": "prometheus.query"})
            return {"status": "error", "error": str(e)}

    async def query_range(
        self, query: str, start: datetime, end: datetime, step: str = "1m"
    ) -> dict[str, Any]:
        """
        执行 Prometheus 范围查询

        Args:
            query: PromQL 查询语句
            start: 开始时间
            end: 结束时间
            step: 步长

        Returns:
            查询结果字典
        """
        url = f"{self.base_url}/api/v1/query_range"
        params = {"query": query, "start": start.timestamp(), "end": end.timestamp(), "step": step}

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                logger.error(
                    f"范围查询失败: {data.get('error')}", extra={"action": "prometheus.query"}
                )
                return {"status": "error", "error": data.get("error")}

            return data
        except Exception as e:
            logger.error(f"范围查询异常: {e}", extra={"action": "prometheus.query"})
            return {"status": "error", "error": str(e)}

    async def get_all_nodes(self) -> list[dict[str, Any]]:
        """
        获取 Prometheus 中所有监控的节点

        Returns:
            节点列表，每个节点包含 instance, nodename, job, env 等信息
        """
        # 使用 node_uname_info 获取所有节点信息
        data = await self.query("node_uname_info")

        if data.get("status") != "success":
            return []

        nodes = []
        for result in data.get("data", {}).get("result", []):
            metric = result.get("metric", {})
            nodes.append(
                {
                    "instance": metric.get("instance", ""),
                    "nodename": metric.get("nodename", ""),
                    "sysname": metric.get("sysname", ""),
                    "release": metric.get("release", ""),
                    "machine": metric.get("machine", ""),
                    "job": metric.get("job", ""),
                    "env": metric.get("env", ""),
                }
            )

        return nodes

    async def get_targets(self) -> list[dict[str, Any]]:
        """
        获取 Prometheus active targets

        Windows 节点的 instance 标签多为中文主机名（非 IP），
        通过 discoveredLabels.__address__ 解析真实抓取地址。

        Returns:
            target 列表，包含 instance/job/address/health

        Raises:
            httpx.HTTPError: 网络/超时错误时抛出，由调用方决定降级策略
                （I-17 修复：原先 catch+return [] 静默吞异常，导致调用方
                 误以为"无 targets"而非"查询失败"，Windows 节点 IP 解析
                 静默失败。现改为抛出，调用方按需 try/except 降级。）
        """
        url = f"{self.base_url}/api/v1/targets"
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "success":
            logger.error("targets 查询失败", extra={"action": "prometheus.targets"})
            return []
        targets = []
        for t in data.get("data", {}).get("activeTargets", []):
            labels = t.get("labels", {})
            discovered = t.get("discoveredLabels", {}) or {}
            address = discovered.get("__address__", "") or t.get("scrapeUrl", "")
            targets.append(
                {
                    "instance": labels.get("instance", ""),
                    "job": labels.get("job", ""),
                    "address": address,
                    "health": t.get("health", "unknown"),
                }
            )
        return targets

    async def get_all_windows_nodes(self) -> list[dict[str, Any]]:
        """
        获取 Windows 服务器节点（基于 windows_exporter）

        Windows 服务器使用 windows_exporter，指标前缀为 windows_*，
        不在 node_uname_info 中，需单独采集。
        instance 标签多为中文主机名，真实 IP 通过 /api/v1/targets 解析。

        Returns:
            节点列表，字段与 get_all_nodes() 兼容，额外含 ip_address、is_windows
        """
        data = await self.query("windows_exporter_build_info")
        if data.get("status") != "success":
            return []

        # 构建 instance -> 真实 IP 映射
        # I-17 修复：get_targets 现在抛出异常而非静默返回 []，
        # 调用方按需降级：targets 查询失败时记 WARNING 并继续
        # （Windows 节点 IP 字段为空，不影响节点发现本身）
        addr_map: dict[str, str] = {}
        try:
            targets = await self.get_targets()
            for t in targets:
                job = t.get("job", "")
                if "windows" not in job.lower():
                    continue
                address = t.get("address", "")
                ip = self._extract_ip(address)
                if ip and t.get("instance"):
                    addr_map[t["instance"]] = ip
        except Exception as e:
            logger.warning(
                f"get_targets 失败，Windows 节点 IP 解析降级为空: {e}",
                extra={"action": "prometheus.windows_nodes", "error": str(e)},
            )

        nodes = []
        for result in data.get("data", {}).get("result", []):
            metric = result.get("metric", {})
            instance = metric.get("instance", "")
            ip = addr_map.get(instance, "")
            nodes.append(
                {
                    "instance": instance,  # Prometheus 标签（中文主机名），用于查询指标
                    "ip_address": ip,  # 真实 IP，用于入库
                    "nodename": instance,
                    "sysname": "Windows",
                    "release": metric.get("version", ""),
                    "machine": metric.get("goarch", ""),
                    "job": metric.get("job", ""),
                    "env": metric.get("env", ""),
                    "is_windows": True,
                }
            )

        logger.info(
            "Windows 节点发现完成",
            extra={"action": "prometheus.windows_nodes", "count": len(nodes)},
        )
        return nodes

    @staticmethod
    def _extract_ip(address: str) -> str:
        """从 address 字符串中提取 IP（支持 IP:port / http://IP:port/path 格式）

        I-18 修复：原先直接字符串拆分，不校验 IP 格式，主机名/异常输入
        会被当作 IP 返回（如 "localhost" / "windows-host-01"），污染
        addr_map 和资产 ip_address 字段。现使用 ipaddress.ip_address()
        严格校验，非法返回 "" 并记 WARNING。
        """
        if not address:
            return ""
        import ipaddress

        cleaned = address.replace("http://", "").replace("https://", "")
        cleaned = cleaned.split("/")[0]
        if ":" in cleaned:
            cleaned = cleaned.split(":")[0]
        # 校验是否为合法 IPv4/IPv6 地址
        try:
            ipaddress.ip_address(cleaned)
            return cleaned
        except ValueError:
            logger.warning(
                f"_extract_ip: 非法 IP 格式，已丢弃: address={address}, extracted={cleaned}",
                extra={"action": "prometheus.extract_ip", "address": address, "extracted": cleaned},
            )
            return ""

    async def get_windows_node_metrics(self, instance: str) -> dict[str, Any]:
        """
        获取 Windows 节点指标（基于 windows_exporter）

        Args:
            instance: Prometheus instance 标签（中文主机名）

        Returns:
            指标字典，包含 cpu_cores、memory_gb、disk_gb、
            memory_usage_percent、disk_usage_percent
        """
        metrics: dict[str, Any] = {}

        queries = {
            "cpu_cores": f'windows_cs_logical_processors{{instance="{instance}"}}',
            "memory_gb": f'windows_cs_physical_memory_bytes{{instance="{instance}"}} / 1024 / 1024 / 1024',
            "disk_gb": f'sum(windows_logical_disk_size_bytes{{instance="{instance}"}}) / 1024 / 1024 / 1024',
            "memory_usage_percent": (
                f'100 * (1 - (windows_os_physical_memory_free_bytes{{instance="{instance}"}} '
                f'/ windows_cs_physical_memory_bytes{{instance="{instance}"}}))'
            ),
            "disk_usage_percent": (
                f'100 * (1 - (sum(windows_logical_disk_free_bytes{{instance="{instance}"}}) '
                f'/ sum(windows_logical_disk_size_bytes{{instance="{instance}"}})))'
            ),
        }

        results = await asyncio.gather(
            *[self.query(q) for q in queries.values()], return_exceptions=True
        )

        for (key, _), data in zip(queries.items(), results, strict=True):
            if isinstance(data, Exception):
                logger.error(
                    f"Windows 指标查询失败: {instance} {key}: {data}",
                    extra={"action": "prometheus.query", "instance": instance},
                )
                continue
            if data.get("status") == "success":
                result_list = data.get("data", {}).get("result", [])
                if result_list:
                    value = result_list[0].get("value", [])
                    if len(value) >= 2:
                        try:
                            raw = float(value[1])
                            metrics[key] = int(raw) if key == "cpu_cores" else round(raw, 2)
                        except (ValueError, TypeError):
                            continue

        return metrics

    async def get_all_windows_nodes_health_check(self) -> list[dict[str, Any]]:
        """
        批量获取所有 Windows 服务器节点的健康检查数据

        基于 windows_exporter 指标，与 get_all_nodes_health_check() 输出结构对齐。
        Windows 无 load 概念，load1/5/15 置 None；
        CPU 使用率通过 windows_cpu_time_total{mode="idle"} 计算。

        Returns:
            节点健康检查列表（字段与 Linux 版兼容，额外含 is_windows 标识）
        """
        queries = {
            "build_info": "windows_exporter_build_info",
            "up": 'up{job=~".*windows.*|.*Windows.*"}',
            "cpu_usage": '100 - (avg by (instance) (irate(windows_cpu_time_total{mode="idle"}[5m])) * 100)',
            "memory_usage": "100 * (1 - (windows_os_physical_memory_free_bytes / windows_cs_physical_memory_bytes))",
            "memory_total": "windows_cs_physical_memory_bytes / 1024 / 1024",
            "disk_usage": "100 * (1 - (sum by (instance) (windows_logical_disk_free_bytes) / sum by (instance) (windows_logical_disk_size_bytes)))",
            "disk_total": "sum by (instance) (windows_logical_disk_size_bytes) / 1024 / 1024 / 1024",
            "cpu_cores": "windows_cs_logical_processors",
        }

        results = await asyncio.gather(
            *[self.query(q) for q in queries.values()], return_exceptions=True
        )

        query_results: dict[str, list[dict[str, Any]]] = {}
        for key, data in zip(queries.keys(), results, strict=True):
            if isinstance(data, Exception):
                logger.error(
                    f"Windows 批量查询失败: {key}: {data}",
                    extra={"action": "prometheus.query"},
                )
                query_results[key] = []
                continue
            if data.get("status") == "success":
                query_results[key] = data.get("data", {}).get("result", [])
            else:
                query_results[key] = []

        # 构建 instance -> 真实 IP 映射（Windows 节点 instance 多为中文主机名）
        # I-17 修复：get_targets 现在抛出异常而非静默返回 []，
        # 调用方按需降级：targets 查询失败时记 WARNING 并继续
        addr_map: dict[str, str] = {}
        try:
            targets = await self.get_targets()
            for t in targets:
                job = t.get("job", "")
                if "windows" not in job.lower():
                    continue
                address = t.get("address", "")
                ip = self._extract_ip(address)
                if ip and t.get("instance"):
                    addr_map[t["instance"]] = ip
        except Exception as e:
            logger.warning(
                f"get_targets 失败，Windows 健康检查 IP 解析降级为空: {e}",
                extra={"action": "prometheus.windows_health_check", "error": str(e)},
            )

        nodes_by_instance: dict[str, dict[str, Any]] = {}
        for result in query_results.get("build_info", []):
            metric = result.get("metric", {})
            inst = metric.get("instance", "")
            if not inst:
                continue
            # 用真实 IP 作为 instance 展示，便于前端识别
            display_instance = addr_map.get(inst, inst)
            nodes_by_instance[inst] = {
                "instance": display_instance,
                "nodename": inst,
                "sysname": "Windows",
                "release": metric.get("version", ""),
                "machine": metric.get("goarch", ""),
                "job": metric.get("job", ""),
                "env": metric.get("env", ""),
                "is_windows": True,
            }

        def build_value_map(results_list: list[dict[str, Any]]) -> dict[str, float]:
            value_map: dict[str, float] = {}
            for r in results_list:
                metric = r.get("metric", {})
                inst = metric.get("instance", "")
                value = r.get("value", [])
                if inst and len(value) >= 2:
                    with contextlib.suppress(ValueError, TypeError):
                        value_map[inst] = float(value[1])
            return value_map

        up_map: dict[str, bool] = {}
        for r in query_results.get("up", []):
            metric = r.get("metric", {})
            inst = metric.get("instance", "")
            value = r.get("value", [])
            if inst and len(value) >= 2:
                up_map[inst] = value[1] == "1"

        cpu_usage_map = build_value_map(query_results.get("cpu_usage", []))
        memory_usage_map = build_value_map(query_results.get("memory_usage", []))
        memory_total_map = build_value_map(query_results.get("memory_total", []))
        disk_usage_map = build_value_map(query_results.get("disk_usage", []))
        disk_total_map = build_value_map(query_results.get("disk_total", []))
        cpu_cores_map = build_value_map(query_results.get("cpu_cores", []))

        health_check_list: list[dict[str, Any]] = []
        for inst, node in nodes_by_instance.items():
            node["is_online"] = up_map.get(inst, False)
            node["cpu_usage_percent"] = round(cpu_usage_map.get(inst, 0.0), 2)
            node["cpu_cores"] = int(cpu_cores_map.get(inst, 0))
            node["load1"] = None
            node["load5"] = None
            node["load15"] = None
            node["memory_usage_percent"] = round(memory_usage_map.get(inst, 0.0), 2)
            node["memory_total_mb"] = round(memory_total_map.get(inst, 0.0), 2)
            node["disk_usage_percent"] = round(disk_usage_map.get(inst, 0.0), 2)
            node["disk_total_gb"] = round(disk_total_map.get(inst, 0.0), 2)
            health_check_list.append(node)

        logger.info(
            "Windows 健康检查数据采集完成",
            extra={"action": "prometheus.windows_health_check", "count": len(health_check_list)},
        )
        return health_check_list

    async def get_node_status(self, instance: str) -> str:
        """
        获取节点在线状态

        Args:
            instance: 节点实例地址 (IP 或主机名)

        Returns:
            "up" 或 "down"
        """
        # 使用 up 指标查询节点状态
        query = f'up{{instance=~".*{instance}.*"}}'
        data = await self.query(query)

        if data.get("status") != "success":
            return "unknown"

        results = data.get("data", {}).get("result", [])
        if not results:
            return "unknown"

        # 获取最新的值
        value = results[0].get("value", [])
        if len(value) >= 2:
            return "up" if value[1] == "1" else "down"

        return "unknown"

    async def get_node_metrics(self, instance: str) -> dict[str, Any]:
        """
        获取节点的实时指标

        Args:
            instance: 节点实例地址

        Returns:
            指标字典，包含 CPU、内存、磁盘、网络等
        """
        metrics = {}

        # CPU 使用率
        cpu_query = f'100 - (avg by (instance) (irate(node_cpu_seconds_total{{mode="idle",instance=~".*{instance}.*"}}[5m])) * 100)'
        cpu_data = await self.query(cpu_query)
        if cpu_data.get("status") == "success" and cpu_data.get("data", {}).get("result"):
            value = cpu_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["cpu_usage_percent"] = round(float(value[1]), 2)

        # 内存使用率
        mem_query = f'100 * (1 - (node_memory_MemAvailable_bytes{{instance=~".*{instance}.*"}} / node_memory_MemTotal_bytes{{instance=~".*{instance}.*"}}))'
        mem_data = await self.query(mem_query)
        if mem_data.get("status") == "success" and mem_data.get("data", {}).get("result"):
            value = mem_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["memory_usage_percent"] = round(float(value[1]), 2)

        # 磁盘使用率
        disk_query = f'100 * (1 - (node_filesystem_avail_bytes{{instance=~".*{instance}.*",mountpoint="/"}} / node_filesystem_size_bytes{{instance=~".*{instance}.*",mountpoint="/"}}))'
        disk_data = await self.query(disk_query)
        if disk_data.get("status") == "success" and disk_data.get("data", {}).get("result"):
            value = disk_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["disk_usage_percent"] = round(float(value[1]), 2)

        # 网络流量
        net_recv_query = (
            f'node_network_receive_bytes_total{{instance=~".*{instance}.*",device="eth0"}}'
        )
        net_recv_data = await self.query(net_recv_query)
        if net_recv_data.get("status") == "success" and net_recv_data.get("data", {}).get("result"):
            value = net_recv_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["network_receive_bytes"] = int(float(value[1]))

        net_transmit_query = (
            f'node_network_transmit_bytes_total{{instance=~".*{instance}.*",device="eth0"}}'
        )
        net_transmit_data = await self.query(net_transmit_query)
        if net_transmit_data.get("status") == "success" and net_transmit_data.get("data", {}).get(
            "result"
        ):
            value = net_transmit_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["network_transmit_bytes"] = int(float(value[1]))

        # 运行时间
        uptime_query = f'node_time_seconds{{instance=~".*{instance}.*"}} - node_boot_time_seconds{{instance=~".*{instance}.*"}}'
        uptime_data = await self.query(uptime_query)
        if uptime_data.get("status") == "success" and uptime_data.get("data", {}).get("result"):
            value = uptime_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["uptime_seconds"] = int(float(value[1]))

        # CPU 核心数
        cpu_cores_query = (
            f'count(node_cpu_seconds_total{{mode="system",instance=~".*{instance}.*"}})'
        )
        cpu_cores_data = await self.query(cpu_cores_query)
        if cpu_cores_data.get("status") == "success" and cpu_cores_data.get("data", {}).get(
            "result"
        ):
            value = cpu_cores_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["cpu_cores"] = int(float(value[1]))

        # 内存总量
        mem_total_query = (
            f'node_memory_MemTotal_bytes{{instance=~".*{instance}.*"}} / 1024 / 1024 / 1024'
        )
        mem_total_data = await self.query(mem_total_query)
        if mem_total_data.get("status") == "success" and mem_total_data.get("data", {}).get(
            "result"
        ):
            value = mem_total_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["memory_gb"] = round(float(value[1]), 2)

        # 磁盘总量
        disk_total_query = f'node_filesystem_size_bytes{{instance=~".*{instance}.*",mountpoint="/"}} / 1024 / 1024 / 1024'
        disk_total_data = await self.query(disk_total_query)
        if disk_total_data.get("status") == "success" and disk_total_data.get("data", {}).get(
            "result"
        ):
            value = disk_total_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["disk_gb"] = round(float(value[1]), 2)

        return metrics

    async def get_node_load(self, instance: str) -> dict[str, Any]:
        """
        获取节点的负载信息

        Args:
            instance: 节点实例地址

        Returns:
            负载字典，包含 load1, load5, load15
        """
        result = {}

        queries = {
            "load1": f'node_load1{{instance=~".*{instance}.*"}}',
            "load5": f'node_load5{{instance=~".*{instance}.*"}}',
            "load15": f'node_load15{{instance=~".*{instance}.*"}}',
        }

        results = await asyncio.gather(
            *[self.query(q) for q in queries.values()], return_exceptions=True
        )

        for (key, _), data in zip(queries.items(), results, strict=True):
            if isinstance(data, Exception):
                logger.error(
                    f"负载查询失败: {instance} {key}: {data}",
                    extra={"action": "prometheus.query", "instance": instance},
                )
                continue
            if data.get("status") == "success":
                result_list = data.get("data", {}).get("result", [])
                if result_list:
                    value = result_list[0].get("value", [])
                    if len(value) >= 2:
                        result[key] = round(float(value[1]), 2)

        return result

    async def get_all_nodes_with_metrics(self) -> list[dict[str, Any]]:
        """
        获取所有节点及其指标

        Returns:
            包含完整信息的节点列表
        """
        nodes = await self.get_all_nodes()

        # 并发获取每个节点的状态和指标
        tasks = []
        for node in nodes:
            task = self._enrich_node_data(node)
            tasks.append(task)

        enriched_nodes = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤掉异常结果
        return [node for node in enriched_nodes if isinstance(node, dict)]

    async def get_all_nodes_health_check(self) -> list[dict[str, Any]]:
        """
        批量获取所有服务器节点的健康检查数据

        Returns:
            节点健康检查列表
        """
        queries = {
            "uname": "node_uname_info",
            "up": "up",
            "load1": "node_load1",
            "load5": "node_load5",
            "load15": "node_load15",
            "cpu_usage": '100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            "memory_usage": "100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))",
            "memory_total": "node_memory_MemTotal_bytes / 1024 / 1024",
            "disk_usage": '100 * (1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}))',
            "disk_total": 'node_filesystem_size_bytes{mountpoint="/"} / 1024 / 1024 / 1024',
            "cpu_cores": 'count(node_cpu_seconds_total{mode="system"}) by (instance)',
        }

        results = await asyncio.gather(
            *[self.query(q) for q in queries.values()], return_exceptions=True
        )

        query_results: dict[str, list[dict[str, Any]]] = {}
        for key, data in zip(queries.keys(), results, strict=True):
            if isinstance(data, Exception):
                logger.error(f"批量查询失败: {key}: {data}", extra={"action": "prometheus.query"})
                query_results[key] = []
                continue
            if data.get("status") == "success":
                query_results[key] = data.get("data", {}).get("result", [])
            else:
                query_results[key] = []

        nodes_by_instance: dict[str, dict[str, Any]] = {}
        for result in query_results.get("uname", []):
            metric = result.get("metric", {})
            inst = metric.get("instance", "")
            job = metric.get("job", "")
            asset_type = self.map_job_to_asset_type(job)
            if asset_type != "server":
                continue
            nodes_by_instance[inst] = {
                "instance": inst,
                "nodename": metric.get("nodename", ""),
                "sysname": metric.get("sysname", ""),
                "release": metric.get("release", ""),
                "machine": metric.get("machine", ""),
                "job": job,
                "env": metric.get("env", ""),
            }

        def build_value_map(results_list: list[dict[str, Any]]) -> dict[str, float]:
            value_map: dict[str, float] = {}
            for r in results_list:
                metric = r.get("metric", {})
                inst = metric.get("instance", "")
                value = r.get("value", [])
                if inst and len(value) >= 2:
                    with contextlib.suppress(ValueError, TypeError):
                        value_map[inst] = float(value[1])
            return value_map

        up_map: dict[str, bool] = {}
        for r in query_results.get("up", []):
            metric = r.get("metric", {})
            inst = metric.get("instance", "")
            value = r.get("value", [])
            if inst and len(value) >= 2:
                up_map[inst] = value[1] == "1"

        load1_map = build_value_map(query_results.get("load1", []))
        load5_map = build_value_map(query_results.get("load5", []))
        load15_map = build_value_map(query_results.get("load15", []))
        cpu_usage_map = build_value_map(query_results.get("cpu_usage", []))
        memory_usage_map = build_value_map(query_results.get("memory_usage", []))
        memory_total_map = build_value_map(query_results.get("memory_total", []))
        disk_usage_map = build_value_map(query_results.get("disk_usage", []))
        disk_total_map = build_value_map(query_results.get("disk_total", []))
        cpu_cores_map = build_value_map(query_results.get("cpu_cores", []))

        health_check_list: list[dict[str, Any]] = []
        for inst, node in nodes_by_instance.items():
            node["is_online"] = up_map.get(inst, False)
            node["cpu_usage_percent"] = round(cpu_usage_map.get(inst, 0.0), 2)
            node["cpu_cores"] = int(cpu_cores_map.get(inst, 0))
            node["load1"] = round(load1_map.get(inst, 0.0), 2)
            node["load5"] = round(load5_map.get(inst, 0.0), 2)
            node["load15"] = round(load15_map.get(inst, 0.0), 2)
            node["memory_usage_percent"] = round(memory_usage_map.get(inst, 0.0), 2)
            node["memory_total_mb"] = round(memory_total_map.get(inst, 0.0), 2)
            node["disk_usage_percent"] = round(disk_usage_map.get(inst, 0.0), 2)
            node["disk_total_gb"] = round(disk_total_map.get(inst, 0.0), 2)
            health_check_list.append(node)

        return health_check_list

    async def _enrich_node_data(self, node: dict[str, Any]) -> dict[str, Any]:
        """
        丰富节点数据，添加状态和指标

        Args:
            node: 基础节点信息

        Returns:
            完整的节点数据
        """
        instance = node.get("instance", "")
        try:
            # 获取状态
            status = await self.get_node_status(instance)
            node["status"] = status

            # 获取指标
            metrics = await self.get_node_metrics(instance)
            node.update(metrics)

            return node
        except Exception as e:
            logger.error(
                f"节点数据丰富失败: {instance}: {e}",
                extra={"action": "prometheus.query", "instance": instance},
            )
            node["status"] = "unknown"
            return node

    async def get_ssl_certificates(self) -> list[dict[str, Any]]:
        """
        获取所有 SSL 证书信息

        Returns:
            证书列表，包含域名、过期时间等信息
        """
        certificates = []

        # 查询 SSL 证书过期时间
        query = "probe_ssl_earliest_cert_expiry"
        data = await self.query(query)

        if data.get("status") != "success":
            logger.warning("SSL证书查询失败", extra={"action": "prometheus.query"})
            return certificates

        for result in data.get("data", {}).get("result", []):
            metric = result.get("metric", {})
            value = result.get("value", [])

            if len(value) >= 2:
                expiry_timestamp = float(value[1])
                expiry_date = from_timestamp(expiry_timestamp)
                now = now_shanghai()
                days_until_expiry = (expiry_date - now).days

                certificates.append(
                    {
                        "domain": metric.get("instance", "")
                        .replace("https://", "")
                        .replace("http://", "")
                        .split("/")[0],
                        "target": metric.get("instance", ""),
                        "job": metric.get("job", ""),
                        "expiry_date": expiry_date.isoformat(),
                        "days_until_expiry": days_until_expiry,
                        "status": self._get_cert_status(days_until_expiry),
                    }
                )

        return certificates

    def _get_cert_status(self, days_until_expiry: int) -> str:
        """根据剩余天数判断证书状态"""
        if days_until_expiry < 0:
            return "expired"
        elif days_until_expiry < 7:
            return "critical"
        elif days_until_expiry < 30:
            return "expiring"
        else:
            return "active"

    async def get_certificate_details(self, target: str) -> dict[str, Any]:
        """
        获取单个证书的详细信息

        Args:
            target: 目标 URL

        Returns:
            证书详细信息
        """
        # 查询证书过期时间
        query = f'probe_ssl_earliest_cert_expiry{{instance="{target}"}}'
        data = await self.query(query)

        if data.get("status") != "success":
            return {}

        results = data.get("data", {}).get("result", [])
        if not results:
            return {}

        result = results[0]
        metric = result.get("metric", {})
        value = result.get("value", [])

        if len(value) < 2:
            return {}

        expiry_timestamp = float(value[1])
        expiry_date = from_timestamp(expiry_timestamp)
        now = now_shanghai()
        days_until_expiry = (expiry_date - now).days

        return {
            "domain": metric.get("instance", "")
            .replace("https://", "")
            .replace("http://", "")
            .split("/")[0],
            "target": metric.get("instance", ""),
            "job": metric.get("job", ""),
            "expiry_date": expiry_date.isoformat(),
            "days_until_expiry": days_until_expiry,
            "status": self._get_cert_status(days_until_expiry),
        }

    def map_job_to_asset_type(self, job: str) -> str:
        """
        将 Prometheus job 映射为资产类型

        Args:
            job: Prometheus job 名称

        Returns:
            资产类型
        """
        job_mapping = {
            "linux服务器监控": "server",
            "windows服务器监控": "server",
            "ops-服务器监控": "server",
            "ops-monitor": "server",
            "pd4-monitor": "server",
            "pd3-monitor": "server",
            "pd5-monitor": "server",
            "mysql": "database",
            "springboot-app": "application",
            "域名过期监控": "domain",
            "pushgateway": "middleware",
            "pcinfo": "terminal",
        }

        if job in job_mapping:
            return job_mapping[job]

        for key, value in job_mapping.items():
            if job.startswith(key.replace("-monitor", "")):
                return value

        return "server"

    async def get_pc_info_terminals(self) -> list[dict[str, Any]]:
        """
        获取 pc_info 指标中的终端信息，提取所有标签

        Returns:
            终端列表，包含所有 pc_info 标签
        """
        terminals = []

        pc_info_query = "pc_info"
        data = await self.query(pc_info_query)

        if data.get("status") != "success":
            logger.warning("终端指标查询失败", extra={"action": "prometheus.query"})
            return terminals

        results = data.get("data", {}).get("result", [])

        for result in results:
            metric = result.get("metric", {})
            value = result.get("value", [])

            if len(value) >= 2 and value[1] == "1":
                terminal = {
                    "hostname": metric.get("hostname", ""),
                    "serial_number": metric.get("serial", ""),
                    "uuid": metric.get("uuid", ""),
                    "customer": metric.get("customer", ""),
                    "instance": metric.get("instance", ""),
                    "ip_address": metric.get("ipAddress", ""),
                    "job": metric.get("job", ""),
                    "os_caption": metric.get("osCaption", ""),
                    "os_version": metric.get("osVersion", ""),
                    "pc_info_labels": dict(metric),
                }
                terminals.append(terminal)

        return terminals

    async def get_terminal_metrics(self, hostname: str) -> dict[str, Any]:
        """
        获取终端的详细指标

        Args:
            hostname: 主机名

        Returns:
            终端指标字典
        """
        metrics = {}

        queries = {
            "disk_total": f'pc_disk_total_bytes{{hostname="{hostname}"}}',
            "disk_usage": f'pc_disk_usage_percent{{hostname="{hostname}"}}',
            "memory_total": f'pc_memory_total_bytes{{hostname="{hostname}"}}',
            "memory_usage": f'pc_memory_usage_percent{{hostname="{hostname}"}}',
            "cpu_usage": f'pc_cpu_usage_percent{{hostname="{hostname}"}}',
        }

        results = await asyncio.gather(
            *[self.query(q) for q in queries.values()], return_exceptions=True
        )

        for (key, _), data in zip(queries.items(), results, strict=True):
            if isinstance(data, Exception):
                logger.error(
                    f"终端指标查询失败: {hostname} {key}: {data}",
                    extra={"action": "prometheus.query", "hostname": hostname},
                )
                continue
            if data.get("status") == "success":
                result_list = data.get("data", {}).get("result", [])
                if result_list:
                    if key in ("disk_total", "memory_total"):
                        total = sum(
                            float(r.get("value", [0, 0])[1])
                            for r in result_list
                            if r.get("value") and len(r["value"]) >= 2
                        )
                        metrics[key] = total
                    else:
                        value = result_list[0].get("value", [])
                        if len(value) >= 2:
                            try:
                                metrics[key] = float(value[1])
                            except (ValueError, TypeError):
                                metrics[key] = value[1]

        return metrics

    async def get_all_terminals_with_metrics(self) -> list[dict[str, Any]]:
        """
        获取所有终端及其指标

        使用 asyncio.Semaphore 限制并发数，避免大量并发请求
        导致事件循环或网络资源压力过大。

        Returns:
            包含完整信息的终端列表
        """
        import asyncio

        terminals = await self.get_pc_info_terminals()

        # 限制并发数，避免同时发起过多 HTTP 请求
        semaphore = asyncio.Semaphore(10)

        async def _enrich_terminal(terminal: dict) -> dict:
            async with semaphore:
                hostname = terminal.get("hostname", "")
                if hostname:
                    try:
                        metrics = await self.get_terminal_metrics(hostname)
                        terminal.update(metrics)
                    except Exception as e:
                        logger.error(
                            f"终端指标获取失败: {hostname}: {e}",
                            extra={"action": "prometheus.query", "hostname": hostname},
                        )
                return terminal

        enriched_terminals = await asyncio.gather(*[_enrich_terminal(t) for t in terminals])

        return list(enriched_terminals)


prometheus_client: PrometheusClient | None = None


def get_prometheus_client() -> PrometheusClient:
    """
    获取 Prometheus 客户端实例

    Returns:
        PrometheusClient 实例
    """
    global prometheus_client
    if prometheus_client is None:
        prometheus_client = PrometheusClient()
    return prometheus_client
