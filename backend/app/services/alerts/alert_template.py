"""
Alert template service.
"""

import re
from datetime import UTC, datetime, timedelta, timezone
from textwrap import dedent
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.tz import now_shanghai
from app.crud.crud_alert import crud_alert_template
from app.models.alert import AlertTemplate

logger = get_logger(__name__)

# Template cache TTL in seconds
TEMPLATE_CACHE_TTL = 300


class AlertTemplateService:
    """Service for rendering alert notification templates using Go template syntax."""

    def __init__(self):
        """Initialize the template service with cache."""
        self._cache: dict[int, tuple[AlertTemplate, datetime]] = {}
        self._cache_ttl = TEMPLATE_CACHE_TTL

    def _is_cache_valid(self, cached_time: datetime) -> bool:
        """Check if template cache is still valid."""
        elapsed = (now_shanghai() - cached_time).total_seconds()
        return elapsed < self._cache_ttl

    async def get_template_cached(
        self,
        db: AsyncSession,
        template_id: int,
    ) -> AlertTemplate | None:
        """Get template by ID with caching."""
        if template_id in self._cache:
            template, cached_time = self._cache[template_id]
            if self._is_cache_valid(cached_time):
                return template

        template = await crud_alert_template.get(db, id=template_id)
        if template:
            self._cache[template_id] = (template, now_shanghai())
        return template

    def _escape_go_template(self, text: str) -> str:
        """Escape Go template delimiters in text to prevent interpretation."""
        # Escape {{ to {{"}}"}} but we need a simpler approach
        # Replace {{ with {{"-"}} to prevent interpretation
        text = text.replace("{{", '{{"-"')
        text = text.replace("}}", '"}}')
        return text

    def _prepare_template(self, template_str: str) -> str:
        """Prepare template string by cleaning up whitespace."""
        # dedent to remove common leading whitespace
        return dedent(template_str).strip()

    def _build_template_context(
        self,
        alertname: str,
        status: str,
        severity: str,
        instance: str | None,
        description: str | None,
        starts_at: datetime | None,
        ends_at: datetime | None = None,
        labels: dict[str, Any] | None = None,
        annotations: dict[str, Any] | None = None,
        alerts: list[dict[str, Any]] | None = None,
        external_url: str | None = None,
    ) -> dict[str, Any]:
        """Build context dictionary for template rendering.

        All template variables:
        - alertname/Alertname: Name of the alert
        - status/Status: Alert status (firing, resolved)
        - severity/Severity: Alert severity (info, warning, critical)
        - instance/Instance: Instance identifier
        - description/Description: Alert description
        - starts_at/startsAt/StartsAt: Alert start time (datetime object for GetCSTtime)
        - ends_at/endsAt/EndsAt: Alert end time (datetime object for GetCSTtime)
        - labels: All labels as dict
        - annotations: All annotations as dict
        - alerts: List of alert objects (for range iteration)
        - firstAlert: First alert object (for convenience)
        - externalURL/external_url: External URL for links
        - generatorURL/generator_url: Generator URL for links
        - alertId: Alert ID for button callbacks
        - summary: Summary annotation
        - detail: Detail annotation
        """
        labels = labels or {}
        annotations = annotations or {}
        alerts = alerts or []
        first_alert = alerts[0] if alerts else {}
        inst = instance or labels.get("instance", "")
        ext_url = external_url or labels.get("externalURL", annotations.get("externalURL", ""))
        gen_url = labels.get("generatorURL", first_alert.get("generatorURL", ""))
        desc = description or annotations.get("description", "")

        cst = timezone(timedelta(hours=8))
        starts_at_str = ""
        ends_at_str = ""
        if starts_at:
            if starts_at.tzinfo is None:
                starts_at = starts_at.replace(tzinfo=UTC)
            starts_at_str = starts_at.astimezone(cst).strftime("%Y-%m-%d %H:%M:%S")
        if ends_at:
            if ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=UTC)
            ends_at_str = ends_at.astimezone(cst).strftime("%Y-%m-%d %H:%M:%S")

        return {
            "alertname": alertname,
            "Alertname": alertname,
            "alertId": f"{alertname}_{inst}".replace(".", "_").replace(":", "_"),
            "status": status,
            "Status": status,
            "severity": severity,
            "Severity": severity,
            "instance": inst,
            "Instance": inst,
            "description": desc,
            "Description": desc,
            "starts_at": starts_at,
            "startsAt": starts_at_str,
            "StartsAt": starts_at_str,
            "ends_at": ends_at,
            "endsAt": ends_at_str,
            "EndsAt": ends_at_str,
            "labels": labels,
            "annotations": annotations,
            "summary": annotations.get("summary", ""),
            "detail": annotations.get("detail", desc),
            "generator_url": gen_url,
            "generatorURL": gen_url,
            "external_url": ext_url,
            "externalURL": ext_url,
            "alerts": alerts,
            "firstAlert": first_alert,
            "firing_count": sum(1 for a in alerts if a.get("status") == "firing"),
            "resolved_count": sum(1 for a in alerts if a.get("status") == "resolved"),
        }

    def render_template(
        self,
        template_str: str,
        context: dict[str, Any],
    ) -> str:
        """Render a template string with the given context.

        Supports Go template syntax: variables ($var, .field), assignments (:=),
        if/else/end, range/end, index, function calls (GetCSTtime), and HTML comments.
        """
        template_str = self._prepare_template(template_str)

        def _resolve_path(path: str, ctx: dict[str, Any]) -> Any:
            if not path:
                return ""
            path = path.strip()
            if (path.startswith('"') and path.endswith('"')) or (path.startswith("'") and path.endswith("'")):
                return path[1:-1]
            if path.startswith("$"):
                path = path[1:]
            if path == ".":
                return ctx.get("_root", ctx)
            if path.startswith("."):
                path = path[1:]
            if not path:
                return ctx.get("_root", ctx)
            if path in ctx:
                return ctx[path]
            parts = [p for p in path.split(".") if p]
            value: Any = ctx
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, "")
                elif isinstance(value, list | tuple):
                    try:
                        idx = int(part)
                        value = value[idx] if 0 <= idx < len(value) else ""
                    except (ValueError, IndexError):
                        return ""
                elif hasattr(value, part):
                    value = getattr(value, part, "")
                else:
                    return ""
                if value == "":
                    return ""
            return value if value is not None else ""

        def _evaluate_expr(expr: str, ctx: dict[str, Any]) -> Any:
            expr = expr.strip()
            if not expr:
                return ""
            if (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
                return expr[1:-1]
            if expr.startswith("index "):
                rest = expr[6:].strip()
                parts = rest.split()
                if len(parts) >= 2:
                    arr_path = parts[0]
                    try:
                        idx = int(parts[1])
                    except ValueError:
                        return ""
                    arr = _resolve_path(arr_path, ctx)
                    if isinstance(arr, list | tuple) and 0 <= idx < len(arr):
                        return arr[idx]
                return ""
            if expr.startswith(".") or expr.startswith("$"):
                return _resolve_path(expr, ctx)
            if expr in ctx:
                return ctx[expr]
            if expr.lower() == "true":
                return True
            if expr.lower() == "false":
                return False
            return expr

        def _evaluate_condition(condition: str, ctx: dict[str, Any]) -> bool:
            condition = condition.strip()
            if condition.startswith("if"):
                condition = condition[2:].strip()
            if not condition:
                return False
            if condition.startswith("eq "):
                parts = condition[3:].strip().split()
                if len(parts) >= 2:
                    left = _evaluate_expr(parts[0], ctx)
                    right = _evaluate_expr(parts[1], ctx)
                    return str(left) == str(right)
            elif condition.startswith("ne "):
                parts = condition[3:].strip().split()
                if len(parts) >= 2:
                    left = _evaluate_expr(parts[0], ctx)
                    right = _evaluate_expr(parts[1], ctx)
                    return str(left) != str(right)
            else:
                val = _evaluate_expr(condition, ctx)
                return bool(val) and str(val) not in ("", "false", "0", "None")
            return False

        def _call_function(func_name: str, args: list[str], ctx: dict[str, Any]) -> str:
            resolved_args = [_evaluate_expr(a, ctx) for a in args]
            if func_name == "GetCSTtime":
                if resolved_args:
                    time_val = resolved_args[0]
                    cst = timezone(timedelta(hours=8))
                    if isinstance(time_val, datetime):
                        if time_val.tzinfo is None:
                            time_val = time_val.replace(tzinfo=UTC)
                        return time_val.astimezone(cst).strftime("%Y-%m-%d %H:%M:%S")
                    if time_val and isinstance(time_val, str):
                        time_str = time_val.strip()
                        dt = None
                        for fmt in (
                            "%Y-%m-%dT%H:%M:%S.%fZ",
                            "%Y-%m-%dT%H:%M:%SZ",
                            "%Y-%m-%dT%H:%M:%S%z",
                            "%Y-%m-%d %H:%M:%S",
                        ):
                            try:
                                dt = datetime.strptime(time_str, fmt)
                                break
                            except ValueError:
                                continue
                        if dt:
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=UTC)
                            return dt.astimezone(cst).strftime("%Y-%m-%d %H:%M:%S")
                        return time_str
                    return str(time_val) if time_val else ""
                return ""
            return "{{" + func_name + " " + " ".join(args) + "}}"

        def render(template: str, ctx: dict[str, Any]) -> str:
            result = template

            result = re.sub(r"<!--.*?-->", "", result, flags=re.DOTALL)

            for match in list(re.finditer(r"\{\{\s*\$(\w+)\s*:=\s*(.+?)\s*\}\}", result)):
                var_name = match.group(1)
                expr = match.group(2).strip()
                value = _evaluate_expr(expr, ctx)
                ctx[var_name] = value
            result = re.sub(r"\{\{\s*\$(\w+)\s*:=\s*(.+?)\s*\}\}", "", result)

            def process_range(m: re.Match) -> str:
                expr_str = m.group(1).strip()
                body = m.group(2)
                items = _evaluate_expr(expr_str, ctx)
                if not isinstance(items, list | tuple):
                    return ""
                parts = []
                for item in items:
                    item_ctx = dict(ctx)
                    item_ctx["_root"] = item
                    if isinstance(item, dict):
                        item_ctx.update(item)
                    parts.append(render(body, item_ctx))
                return "".join(parts)

            result = re.sub(
                r"\{\{\s*range\s+(.+?)\s*\}\}(.*?)\{\{\s*end\s*\}\}",
                process_range,
                result,
                flags=re.DOTALL,
            )

            def process_if(m: re.Match) -> str:
                condition = m.group(1).strip()
                full_content = m.group(2)
                if "{{else}}" in full_content:
                    true_content, false_content = full_content.split("{{else}}", 1)
                else:
                    true_content, false_content = full_content, ""
                if _evaluate_condition(condition, ctx):
                    return render(true_content, ctx)
                else:
                    return render(false_content, ctx)

            result = re.sub(
                r"\{\{(\s*if\s+.*?\s*)\}\}(.*?)\{\{\s*end\s*\}\}",
                process_if,
                result,
                flags=re.DOTALL,
            )

            def process_func(m: re.Match) -> str:
                func_name = m.group(1).strip()
                args_str = m.group(2).strip()
                args = [a.strip() for a in args_str.split() if a.strip()]
                return _call_function(func_name, args, ctx)

            result = re.sub(
                r"\{\{\s*(\w+)\s+((?:(?!\{\{).)*?)\s*\}\}",
                process_func,
                result,
            )

            def process_index(m: re.Match) -> str:
                var_path = m.group(1).strip()
                idx = int(m.group(2))
                value = _resolve_path(var_path, ctx)
                if isinstance(value, list | tuple) and 0 <= idx < len(value):
                    item = value[idx]
                    return str(item) if not isinstance(item, dict | list) else ""
                return ""

            result = re.sub(
                r"\{\{\s*index\s+(\S+)\s+(\d+)\s*\}\}",
                process_index,
                result,
            )

            def process_dollar_var(m: re.Match) -> str:
                var_name = m.group(1)
                rest = m.group(2) or ""
                value: Any = ctx.get(var_name, "")
                if rest and isinstance(value, dict):
                    parts = [p for p in rest.split(".") if p]
                    for part in parts:
                        if isinstance(value, dict):
                            value = value.get(part, "")
                        else:
                            return ""
                if isinstance(value, dict | list):
                    return ""
                return str(value) if value is not None else ""

            result = re.sub(
                r"\{\{\s*\$(\w+)((?:\.\w+)*)\s*\}\}",
                process_dollar_var,
                result,
            )

            def process_dot_var(m: re.Match) -> str:
                path = m.group(1)
                rest = m.group(2) or ""
                full_path = path + rest
                value = _resolve_path("." + full_path, ctx)
                if isinstance(value, dict | list):
                    return ""
                return str(value) if value is not None else ""

            result = re.sub(
                r"\{\{\s*\.(\w+)((?:\.\w+)*)\s*\}\}",
                process_dot_var,
                result,
            )

            return result

        return render(template_str, dict(context))

    async def render_alert_template(
        self,
        db: AsyncSession,
        template: AlertTemplate,
        alertname: str,
        status: str,
        severity: str,
        instance: str | None,
        description: str | None,
        starts_at: datetime | None,
        ends_at: datetime | None = None,
        labels: dict[str, Any] | None = None,
        annotations: dict[str, Any] | None = None,
        alerts: list[dict[str, Any]] | None = None,
        external_url: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Render an alert template with alert data.

        Args:
            db: Database session
            template: AlertTemplate model
            alertname: Alert name
            status: Alert status
            severity: Alert severity
            instance: Instance identifier
            description: Alert description
            starts_at: Alert start time
            ends_at: Alert end time (for resolved alerts)
            labels: Alert labels
            annotations: Alert annotations
            alerts: List of raw alert objects from Alertmanager
            external_url: External URL for links

        Returns:
            Tuple of (rendered_subject, rendered_body)
        """
        context = self._build_template_context(
            alertname=alertname,
            status=status,
            severity=severity,
            instance=instance,
            description=description,
            starts_at=starts_at,
            ends_at=ends_at,
            labels=labels,
            annotations=annotations,
            alerts=alerts,
            external_url=external_url,
        )

        rendered_subject = None
        if template.subject_template:
            rendered_subject = self.render_template(template.subject_template, context)

        rendered_body = None
        if template.body_template:
            rendered_body = self.render_template(template.body_template, context)

        return rendered_subject, rendered_body

    def render_preview(
        self,
        template_str: str,
        preview_data: dict[str, Any] | None = None,
    ) -> str:
        """Render a template for preview purposes.

        Args:
            template_str: Template string to render
            preview_data: Optional preview data, uses defaults if not provided

        Returns:
            Rendered template string
        """
        if preview_data is None:
            preview_data = {
                "alertname": "HighMemoryUsage",
                "status": "firing",
                "severity": "critical",
                "instance": "server-01",
                "description": "Memory usage is above 90%",
                "starts_at": now_shanghai(),
                "labels": {
                    "alertname": "HighMemoryUsage",
                    "severity": "critical",
                    "instance": "server-01",
                    "job": "node_exporter",
                },
                "annotations": {
                    "summary": "High memory usage detected on server-01",
                    "detail": "Memory usage has been above 90% for the last 5 minutes",
                },
            }

        return self.render_template(template_str, preview_data)

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()


# Global service instance
alert_template_service = AlertTemplateService()
