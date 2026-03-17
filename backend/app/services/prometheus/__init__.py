"""
Prometheus 服务模块

用于与 Prometheus HTTP API 交互，获取资产数据
"""

from .client import PrometheusClient

__all__ = ["PrometheusClient"]
