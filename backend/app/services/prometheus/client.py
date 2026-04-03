"""
Prometheus HTTP API 客户端实现
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


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
                logger.error(f"Prometheus query failed: {data.get('error')}")
                return {"status": "error", "error": data.get("error")}

            return data
        except httpx.TimeoutException:
            logger.error(f"Prometheus query timeout: {query}")
            return {"status": "error", "error": "timeout"}
        except Exception as e:
            logger.error(f"Prometheus query error: {e}")
            return {"status": "error", "error": str(e)}

    async def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str = "1m"
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
        params = {
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "success":
                logger.error(f"Prometheus range query failed: {data.get('error')}")
                return {"status": "error", "error": data.get("error")}

            return data
        except Exception as e:
            logger.error(f"Prometheus range query error: {e}")
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
            nodes.append({
                "instance": metric.get("instance", ""),
                "nodename": metric.get("nodename", ""),
                "sysname": metric.get("sysname", ""),
                "release": metric.get("release", ""),
                "machine": metric.get("machine", ""),
                "job": metric.get("job", ""),
                "env": metric.get("env", ""),
            })

        return nodes

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
        disk_query = f'100 * (1 - (node_filesystem_avail_bytes{{instance=~".*{instance}.*",mount="/"}} / node_filesystem_size_bytes{{instance=~".*{instance}.*",mount="/"}}))'
        disk_data = await self.query(disk_query)
        if disk_data.get("status") == "success" and disk_data.get("data", {}).get("result"):
            value = disk_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["disk_usage_percent"] = round(float(value[1]), 2)

        # 网络流量
        net_recv_query = f'node_network_receive_bytes_total{{instance=~".*{instance}.*",device="eth0"}}'
        net_recv_data = await self.query(net_recv_query)
        if net_recv_data.get("status") == "success" and net_recv_data.get("data", {}).get("result"):
            value = net_recv_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["network_receive_bytes"] = int(float(value[1]))

        net_transmit_query = f'node_network_transmit_bytes_total{{instance=~".*{instance}.*",device="eth0"}}'
        net_transmit_data = await self.query(net_transmit_query)
        if net_transmit_data.get("status") == "success" and net_transmit_data.get("data", {}).get("result"):
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
        cpu_cores_query = f'count(node_cpu_seconds_total{{mode="system",instance=~".*{instance}.*"}})'
        cpu_cores_data = await self.query(cpu_cores_query)
        if cpu_cores_data.get("status") == "success" and cpu_cores_data.get("data", {}).get("result"):
            value = cpu_cores_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["cpu_cores"] = int(float(value[1]))

        # 内存总量
        mem_total_query = f'node_memory_MemTotal_bytes{{instance=~".*{instance}.*"}} / 1024 / 1024 / 1024'
        mem_total_data = await self.query(mem_total_query)
        if mem_total_data.get("status") == "success" and mem_total_data.get("data", {}).get("result"):
            value = mem_total_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["memory_gb"] = round(float(value[1]), 2)

        # 磁盘总量
        disk_total_query = f'node_filesystem_size_bytes{{instance=~".*{instance}.*",mount="/"}} / 1024 / 1024 / 1024'
        disk_total_data = await self.query(disk_total_query)
        if disk_total_data.get("status") == "success" and disk_total_data.get("data", {}).get("result"):
            value = disk_total_data["data"]["result"][0].get("value", [])
            if len(value) >= 2:
                metrics["disk_gb"] = round(float(value[1]), 2)

        return metrics

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
            logger.error(f"Failed to enrich node data for {instance}: {e}")
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
        query = 'probe_ssl_earliest_cert_expiry'
        data = await self.query(query)

        if data.get("status") != "success":
            logger.warning("Failed to query SSL certificate expiry")
            return certificates

        for result in data.get("data", {}).get("result", []):
            metric = result.get("metric", {})
            value = result.get("value", [])

            if len(value) >= 2:
                expiry_timestamp = float(value[1])
                expiry_date = datetime.fromtimestamp(expiry_timestamp)
                now = datetime.now()
                days_until_expiry = (expiry_date - now).days

                certificates.append({
                    "domain": metric.get("instance", "").replace("https://", "").replace("http://", "").split("/")[0],
                    "target": metric.get("instance", ""),
                    "job": metric.get("job", ""),
                    "expiry_date": expiry_date.isoformat(),
                    "days_until_expiry": days_until_expiry,
                    "status": self._get_cert_status(days_until_expiry),
                })

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
        expiry_date = datetime.fromtimestamp(expiry_timestamp)
        now = datetime.now()
        days_until_expiry = (expiry_date - now).days

        return {
            "domain": metric.get("instance", "").replace("https://", "").replace("http://", "").split("/")[0],
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

        pc_info_query = 'pc_info'
        data = await self.query(pc_info_query)

        if data.get("status") != "success":
            logger.warning("Failed to query pc_info metrics")
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
                    "job": metric.get("job", ""),
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

        results = await asyncio.gather(*[self.query(q) for q in queries.values()], return_exceptions=True)

        for (key, _), data in zip(queries.items(), results, strict=True):
            if isinstance(data, Exception):
                logger.error(f"Failed to query {key} for {hostname}: {data}")
                continue
            if data.get("status") == "success":
                result_list = data.get("data", {}).get("result", [])
                if result_list:
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

        Returns:
            包含完整信息的终端列表
        """
        terminals = await self.get_pc_info_terminals()

        enriched_terminals = []
        for terminal in terminals:
            hostname = terminal.get("hostname", "")
            if hostname:
                try:
                    metrics = await self.get_terminal_metrics(hostname)
                    terminal.update(metrics)
                except Exception as e:
                    logger.error(f"Failed to get metrics for terminal {hostname}: {e}")
            enriched_terminals.append(terminal)

        return enriched_terminals


# 全局客户端实例
prometheus_client = PrometheusClient()


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


prometheus_client: "PrometheusClient | None" = None
