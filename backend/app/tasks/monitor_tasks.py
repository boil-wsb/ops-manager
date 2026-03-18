"""
Monitor check tasks.
"""
import asyncio
import subprocess
import socket
import time
from datetime import datetime
from typing import Optional

import httpx
from celery import shared_task

from app.config import settings
from app.core.logging import get_logger
from app.tasks.utils import get_celery_async_session

logger = get_logger(__name__)


async def check_ping(target: str, timeout: int = 10) -> tuple[bool, Optional[str], Optional[int]]:
    """Check if target responds to ping.
    
    Returns: (success, message, response_time_ms)
    """
    try:
        start_time = time.time()
        
        count_flag = "-n" if subprocess.sys.platform == "win32" else "-c"
        result = subprocess.run(
            ["ping", count_flag, "1", "-W", str(timeout), target],
            capture_output=True,
            text=True,
            timeout=timeout + 2
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if result.returncode == 0:
            return True, "Ping successful", elapsed_ms
        else:
            return False, "Ping failed", None
            
    except subprocess.TimeoutExpired:
        return False, "Ping timeout", None
    except Exception as e:
        return False, f"Ping error: {str(e)}", None


async def check_http(
    target: str,
    method: str = "GET",
    headers: Optional[dict] = None,
    body: Optional[str] = None,
    expected_status: Optional[int] = None,
    expected_content: Optional[str] = None,
    timeout: int = 10
) -> tuple[bool, Optional[str], Optional[int]]:
    """Check HTTP endpoint.
    
    Returns: (success, message, response_time_ms)
    """
    try:
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            method = method.upper()
            
            if method == "GET":
                response = await client.get(target, headers=headers)
            elif method == "POST":
                response = await client.post(target, headers=headers, content=body)
            elif method == "PUT":
                response = await client.put(target, headers=headers, content=body)
            elif method == "DELETE":
                response = await client.delete(target, headers=headers)
            else:
                response = await client.request(method, target, headers=headers, content=body)
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            if expected_status and response.status_code != expected_status:
                return (
                    False,
                    f"Unexpected status code: {response.status_code} (expected {expected_status})",
                    elapsed_ms
                )
            
            if expected_content and expected_content not in response.text:
                return False, f"Expected content not found in response", elapsed_ms
            
            return True, f"HTTP {response.status_code}", elapsed_ms
            
    except httpx.TimeoutException:
        return False, "HTTP request timeout", None
    except httpx.ConnectError:
        return False, "Connection error", None
    except Exception as e:
        return False, f"HTTP error: {str(e)}", None


async def check_tcp(target: str, port: int, timeout: int = 10) -> tuple[bool, Optional[str], Optional[int]]:
    """Check TCP port.
    
    Returns: (success, message, response_time_ms)
    """
    try:
        start_time = time.time()
        
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(target, port),
            timeout=timeout
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        writer.close()
        await writer.wait_closed()
        
        return True, f"TCP port {port} open", elapsed_ms
        
    except asyncio.TimeoutError:
        return False, f"TCP connection timeout to port {port}", None
    except ConnectionRefusedError:
        return False, f"TCP connection refused on port {port}", None
    except Exception as e:
        return False, f"TCP error: {str(e)}", None


async def check_udp(target: str, port: int, timeout: int = 10) -> tuple[bool, Optional[str], Optional[int]]:
    """Check UDP port.
    
    Returns: (success, message, response_time_ms)
    """
    try:
        start_time = time.time()
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        sock.sendto(b"", (target, port))
        
        try:
            sock.recvfrom(1024)
        except socket.timeout:
            pass
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        sock.close()
        
        return True, f"UDP port {port} reachable", elapsed_ms
        
    except Exception as e:
        return False, f"UDP error: {str(e)}", None


async def perform_check(monitor) -> tuple[bool, Optional[str], Optional[int]]:
    """Perform a single monitor check."""
    monitor_type = monitor.monitor_type.value
    target = monitor.target
    timeout = monitor.timeout_seconds
    
    if monitor_type == "ping":
        return await check_ping(target, timeout)
    
    elif monitor_type == "http":
        return await check_http(
            target,
            method=monitor.http_method or "GET",
            headers=monitor.http_headers,
            body=monitor.http_body,
            expected_status=monitor.expected_status_code,
            expected_content=monitor.expected_response_content,
            timeout=timeout
        )
    
    elif monitor_type == "tcp":
        try:
            host, port = target.rsplit(":", 1)
            port = int(port)
            return await check_tcp(host, port, timeout)
        except ValueError:
            return False, "Invalid TCP target format (expected host:port)", None
    
    elif monitor_type == "udp":
        try:
            host, port = target.rsplit(":", 1)
            port = int(port)
            return await check_udp(host, port, timeout)
        except ValueError:
            return False, "Invalid UDP target format (expected host:port)", None
    
    else:
        return False, f"Unknown monitor type: {monitor_type}", None


@shared_task(bind=True, max_retries=3)
def check_monitor(self, monitor_id: int):
    """Check a single monitor."""
    from sqlalchemy import select
    from app.models.monitor import Monitor, Alert, MonitorStatus, AlertSeverity
    
    async def _check():
        SessionLocal = get_celery_async_session()
        
        async with SessionLocal() as db:
            result = await db.execute(
                select(Monitor).where(Monitor.id == monitor_id)
            )
            monitor = result.scalar_one_or_none()
            
            if not monitor or not monitor.is_enabled:
                return
            
            success, message, duration_ms = await perform_check(monitor)
            
            monitor.last_check_at = datetime.utcnow()
            monitor.last_check_result = message
            monitor.last_check_duration_ms = duration_ms
            
            old_status = monitor.current_status
            new_status = MonitorStatus.UP if success else MonitorStatus.DOWN
            monitor.current_status = new_status
            
            await db.commit()
            
            if old_status != MonitorStatus.DOWN and new_status == MonitorStatus.DOWN:
                alert = Alert(
                    monitor_id=monitor.id,
                    severity=AlertSeverity.WARNING,
                    status="firing",
                    title=f"Monitor {monitor.name} is DOWN",
                    message=message,
                    metric_name="response_time",
                    metric_value=duration_ms,
                    started_at=datetime.utcnow()
                )
                db.add(alert)
                await db.commit()
            
            if old_status == MonitorStatus.DOWN and new_status == MonitorStatus.UP:
                result = await db.execute(
                    select(Alert).where(
                        Alert.monitor_id == monitor.id,
                        Alert.status == "firing"
                    )
                )
                alert = result.scalar_one_or_none()
                if alert:
                    alert.status = "resolved"
                    alert.resolved_at = datetime.utcnow()
                    await db.commit()
            
            logger.info(
                f"Monitor check completed: id={monitor_id}, name={monitor.name}, success={success}, duration={duration_ms}ms"
            )
    
    try:
        asyncio.run(_check())
    except Exception as exc:
        logger.error(f"Monitor check failed: id={monitor_id}, error={str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task
def check_all_monitors():
    """Check all enabled monitors."""
    from sqlalchemy import select
    from app.models.monitor import Monitor
    
    async def _check_all():
        SessionLocal = get_celery_async_session()
        
        async with SessionLocal() as db:
            result = await db.execute(
                select(Monitor).where(Monitor.is_enabled == True)
            )
            monitors = result.scalars().all()
            
            logger.info(f"Checking {len(monitors)} monitors")
            
            for monitor in monitors:
                check_monitor.delay(monitor.id)
    
    asyncio.run(_check_all())
