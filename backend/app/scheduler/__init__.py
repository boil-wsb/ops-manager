import asyncio
import importlib
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.core.logging import get_logger
from app.db.session import get_session_maker

logger = get_logger(__name__)

scheduler: AsyncIOScheduler | None = None

BUILTIN_TASKS = [
    {
        "task_id": "check-all-monitors",
        "name": "监控检查",
        "task_function": "app.tasks.monitor_tasks.check_all_monitors",
        "trigger_type": "interval",
        "trigger_config": {"seconds": 60},
        "category": "monitor",
        "description": "检查所有启用的监控项状态",
    },
    {
        "task_id": "cleanup-audit-logs-db",
        "name": "审计日志数据库清理",
        "task_function": "app.tasks.audit_log_cleanup.cleanup_audit_logs_db",
        "trigger_type": "cron",
        "trigger_config": {"hour": 3, "minute": 0},
        "category": "cleanup",
        "description": "清理过期的审计日志数据库记录",
    },
    {
        "task_id": "cleanup-audit-logs-file",
        "name": "审计日志文件清理",
        "task_function": "app.tasks.audit_log_cleanup.cleanup_audit_logs_file",
        "trigger_type": "cron",
        "trigger_config": {"hour": 3, "minute": 30},
        "category": "cleanup",
        "description": "清理过期的审计日志文件",
    },
    {
        "task_id": "sync-feishu-users",
        "name": "飞书用户同步",
        "task_function": "app.tasks.feishu_sync_tasks.sync_feishu_users_task",
        "trigger_type": "cron",
        "trigger_config": {"hour": 2, "minute": 0},
        "category": "sync",
        "description": "从飞书同步用户数据到本地数据库",
    },
    {
        "task_id": "sync-assets-from-prometheus",
        "name": "Prometheus 资产同步",
        "task_function": "app.tasks.asset_sync_tasks.sync_assets_from_prometheus_task",
        "trigger_type": "interval",
        "trigger_config": {"minutes": settings.prometheus_sync_interval},
        "category": "sync",
        "description": "从 Prometheus 自动同步资产数据",
    },
    {
        "task_id": "sync-certificates-from-prometheus",
        "name": "Prometheus 证书同步",
        "task_function": "app.tasks.certificate_sync_tasks.sync_certificates_from_prometheus_task",
        "trigger_type": "cron",
        "trigger_config": {"hour": 3, "minute": 0},
        "category": "sync",
        "description": "从 Prometheus 同步 SSL 证书数据",
    },
    {
        "task_id": "sync-terminal-metrics",
        "name": "终端指标同步",
        "task_function": "app.tasks.sync_terminal_metrics.sync_terminal_metrics_task",
        "trigger_type": "interval",
        "trigger_config": {"minutes": 5},
        "category": "sync",
        "description": "从 Prometheus 同步终端指标数据",
    },
    {
        "task_id": "execute-ansible-playbook",
        "name": "Ansible Playbook 执行",
        "task_function": "app.tasks.ansible_tasks.execute_ansible_command",
        "trigger_type": "cron",
        "trigger_config": {
            "hour": settings.ansible_schedule_hour,
            "minute": settings.ansible_schedule_minute,
        },
        "category": "ops",
        "description": "通过 SSH 执行 Ansible Playbook",
    },
    {
        "task_id": "process-it-report",
        "name": "IT巡检报告处理",
        "task_function": "app.tasks.it_reporter_tasks.process_it_report_task",
        "trigger_type": "cron",
        "trigger_config": {"hour": 9, "minute": 0},
        "category": "ops",
        "description": "处理IT系统健康巡检报告并发送飞书通知",
    },
]


def get_scheduler() -> AsyncIOScheduler:
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    return scheduler


async def register_builtin_tasks():
    from app.crud.crud_scheduled_task import crud_scheduled_task
    from app.crud.crud_system_config import crud_system_config

    session_maker = get_session_maker()
    async with session_maker() as db:
        for task_def in BUILTIN_TASKS:
            try:
                await crud_scheduled_task.upsert_by_task_id(
                    db,
                    task_id=task_def["task_id"],
                    name=task_def["name"],
                    task_function=task_def["task_function"],
                    trigger_type=task_def["trigger_type"],
                    trigger_config=task_def["trigger_config"],
                    category=task_def["category"],
                    description=task_def.get("description"),
                )
                await crud_system_config.upsert_by_key(
                    db,
                    key=f"scheduler.task_mapping.{task_def['task_id']}",
                    value=task_def["task_function"],
                    group="scheduler",
                    description=f"定时任务「{task_def['name']}」对应的代码函数路径",
                )
            except Exception as e:
                logger.error(f"Failed to register builtin task {task_def['task_id']}: {e}")

        await _init_default_configs(db)


async def _init_default_configs(db):
    from app.crud.crud_system_config import crud_system_config

    default_configs = [
        {
            "key": "itreporter.chat_id",
            "value": settings.itreporter_chat_id,
            "group": "itreporter",
            "description": "IT巡检报告飞书通知群聊 ID",
        },
        {
            "key": "itreporter.minio_bucket",
            "value": settings.itreporter_minio_bucket,
            "group": "itreporter",
            "description": "IT巡检报告默认 MinIO 存储桶",
        },
        {
            "key": "itreporter.presigned_url_expires_hours",
            "value": str(settings.itreporter_presigned_url_expires_hours),
            "group": "itreporter",
            "description": "预签名 URL 有效期（小时）",
        },
        {
            "key": "itreporter.report_path",
            "value": settings.itreporter_report_path,
            "group": "itreporter",
            "description": "IT巡检报告在 MinIO 中的默认路径",
        },
    ]
    for config in default_configs:
        try:
            existing = await crud_system_config.get_by_key(db, config["key"])
            if existing:
                if not existing.value and config.get("value"):
                    existing.value = config["value"]
                    await db.commit()
                continue
            await crud_system_config.upsert_by_key(db, **config)
        except Exception as e:
            logger.error(f"Failed to init default config {config['key']}: {e}")


async def load_tasks_from_db():
    from app.crud.crud_scheduled_task import crud_scheduled_task

    sched = get_scheduler()
    session_maker = get_session_maker()
    async with session_maker() as db:
        tasks, _ = await crud_scheduled_task.get_multi(db, limit=1000, is_enabled=True)
        for task in tasks:
            try:
                trigger = _build_trigger(task.trigger_type, task.trigger_config)
                if trigger is None:
                    logger.error(f"Failed to build trigger for task {task.task_id}")
                    continue
                sched.add_job(
                    _execute_task_wrapper,
                    trigger=trigger,
                    id=task.task_id,
                    name=task.name,
                    args=[task.task_id],
                    replace_existing=True,
                )
                logger.info(f"Loaded scheduled task: {task.task_id} ({task.trigger_type})")
            except Exception as e:
                logger.error(f"Failed to load task {task.task_id}: {e}")


def _build_trigger(trigger_type: str, trigger_config: dict):
    try:
        if trigger_type == "cron":
            return CronTrigger(timezone="Asia/Shanghai", **trigger_config)
        elif trigger_type == "interval":
            return IntervalTrigger(timezone="Asia/Shanghai", **trigger_config)
        else:
            logger.error(f"Unknown trigger type: {trigger_type}")
            return None
    except Exception as e:
        logger.error(f"Failed to build trigger ({trigger_type}, {trigger_config}): {e}")
        return None


async def _execute_task_wrapper(task_id: str):
    from app.crud.crud_scheduled_task import crud_scheduled_task

    session_maker = get_session_maker()

    task_function_path = None
    async with session_maker() as db:
        task = await crud_scheduled_task.get_by_task_id(db, task_id)
        if not task:
            logger.debug(f"Task {task_id} not found in database")
            return
        task_function_path = task.task_function

    started_at = datetime.now(ZoneInfo("Asia/Shanghai"))
    error_message = None
    result_summary = None
    status = "success"
    duration = 0.0
    start_time = time.time()

    try:
        module_path, func_name = task_function_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)

        start_time = time.time()

        if asyncio.iscoroutinefunction(func):
            result = await func()
        else:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, func)

        duration = time.time() - start_time

        if isinstance(result, dict):
            if result.get("result_summary"):
                result_summary = result["result_summary"]
            elif result.get("presigned_url"):
                result_summary = f"status={result.get('status', 'success')}, presigned_url={result['presigned_url']}"
            else:
                result_summary = str(result.get("status", ""))
            if result.get("error"):
                error_message = str(result["error"])
                status = "failed"
        elif isinstance(result, tuple) and len(result) == 2:
            success, message = result
            if not success:
                status = "failed"
                error_message = str(message)
            result_summary = str(message) if message else None
        elif isinstance(result, str):
            result_summary = result

        if status == "success":
            logger.debug(f"Task {task_id} completed in {duration:.2f}s")
        else:
            logger.debug(f"Task {task_id} failed: {error_message}")

    except Exception as e:
        duration = time.time() - start_time
        status = "failed"
        error_message = str(e)
        logger.debug(f"Task {task_id} execution error: {e}")

    finished_at = datetime.now(ZoneInfo("Asia/Shanghai"))

    try:
        async with session_maker() as db:
            await crud_scheduled_task.create_execution_log(
                db,
                task_id=task_id,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
                duration=duration,
                error_message=error_message,
                result_summary=result_summary,
                trigger_type="scheduled",
            )
            await crud_scheduled_task.update_run_status(
                db,
                task_id=task_id,
                status=status,
                duration=duration,
                result_summary=result_summary,
                error_message=error_message,
            )
    except Exception as e:
        logger.debug(f"Failed to update task status for {task_id}: {e}")


def update_scheduler_job(task_id: str):
    from app.crud.crud_scheduled_task import crud_scheduled_task

    sched = get_scheduler()

    async def _update():
        session_maker = get_session_maker()
        async with session_maker() as db:
            task = await crud_scheduled_task.get_by_task_id(db, task_id)
            if not task:
                return

            if not task.is_enabled:
                remove_scheduler_job(task_id)
                return

            trigger = _build_trigger(task.trigger_type, task.trigger_config)
            if trigger is None:
                return

            sched.add_job(
                _execute_task_wrapper,
                trigger=trigger,
                id=task.task_id,
                name=task.name,
                args=[task.task_id],
                replace_existing=True,
            )

            try:
                job = sched.get_job(task_id)
                if job:
                    task.next_run_time = job.next_run_time
                    db.add(task)
                    await db.commit()
            except Exception:
                pass

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_update())
        else:
            loop.run_until_complete(_update())
    except RuntimeError:
        asyncio.run(_update())


def remove_scheduler_job(task_id: str):
    sched = get_scheduler()
    try:
        sched.remove_job(task_id)
        logger.info(f"Removed scheduler job: {task_id}")
    except Exception:
        pass


def add_scheduler_job(task_id: str):
    update_scheduler_job(task_id)


async def run_task_manually(task_id: str, triggered_by: str | None = None):
    from app.crud.crud_scheduled_task import crud_scheduled_task

    session_maker = get_session_maker()

    task_function_path = None
    async with session_maker() as db:
        task = await crud_scheduled_task.get_by_task_id(db, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        task_function_path = task.task_function

    started_at = datetime.now(ZoneInfo("Asia/Shanghai"))
    error_message = None
    result_summary = None
    status = "success"
    duration = 0.0

    try:
        module_path, func_name = task_function_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)

        start_time = time.time()

        if asyncio.iscoroutinefunction(func):
            result = await func()
        else:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, func)

        duration = time.time() - start_time

        if isinstance(result, dict):
            if result.get("result_summary"):
                result_summary = result["result_summary"]
            elif result.get("presigned_url"):
                result_summary = f"status={result.get('status', 'success')}, presigned_url={result['presigned_url']}"
            else:
                result_summary = str(result.get("status", ""))
            if result.get("error"):
                error_message = str(result["error"])
                status = "failed"
        elif isinstance(result, tuple) and len(result) == 2:
            success, message = result
            if not success:
                status = "failed"
                error_message = str(message)
            result_summary = str(message) if message else None
        elif isinstance(result, str):
            result_summary = result

    except Exception as e:
        duration = time.time() - start_time
        status = "failed"
        error_message = str(e)

    finished_at = datetime.now(ZoneInfo("Asia/Shanghai"))

    async with session_maker() as db:
        await crud_scheduled_task.create_execution_log(
            db,
            task_id=task_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration=duration,
            error_message=error_message,
            result_summary=result_summary,
            trigger_type="manual",
            triggered_by=triggered_by,
        )
        await crud_scheduled_task.update_run_status(
            db,
            task_id=task_id,
            status=status,
            duration=duration,
            result_summary=result_summary,
            error_message=error_message,
        )

    return {
        "status": status,
        "duration": duration,
        "errorMessage": error_message,
        "resultSummary": result_summary,
    }


def start_scheduler():
    sched = get_scheduler()

    async def _init():
        await register_builtin_tasks()
        await load_tasks_from_db()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_init())
        else:
            loop.run_until_complete(_init())
    except RuntimeError:
        asyncio.run(_init())

    sched.start()
    logger.info("APScheduler started")


def stop_scheduler():
    global scheduler
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("APScheduler stopped")
