"""
Alert template service.
"""
import re
from datetime import datetime
from textwrap import dedent
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
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
        elapsed = (datetime.utcnow() - cached_time).total_seconds()
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
            self._cache[template_id] = (template, datetime.utcnow())
        return template

    def _escape_go_template(self, text: str) -> str:
        """Escape Go template delimiters in text to prevent interpretation."""
        # Escape {{ to {{"}}"}} but we need a simpler approach
        # Replace {{ with {{"-"}} to prevent interpretation
        text = text.replace("{{", "{{\"-\"")
        text = text.replace("}}", "\"}}")
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
        labels: dict[str, Any],
        annotations: dict[str, Any],
    ) -> dict[str, Any]:
        """Build context dictionary for template rendering.

        All template variables:
        - alertname: Name of the alert
        - status: Alert status (firing, resolved)
        - severity: Alert severity (info, warning, critical)
        - instance: Instance identifier
        - description: Alert description
        - starts_at: Alert start time
        - labels: All labels as dict
        - annotations: All annotations as dict
        """
        return {
            "alertname": alertname,
            "status": status,
            "severity": severity,
            "instance": instance or labels.get("instance", ""),
            "description": description or annotations.get("description", ""),
            "starts_at": starts_at,
            "labels": labels,
            "annotations": annotations,
            # Convenience variables
            "summary": annotations.get("summary", ""),
            "detail": annotations.get("detail", description or ""),
            "generator_url": labels.get("generatorURL", ""),
        }

    def render_template(
        self,
        template_str: str,
        context: dict[str, Any],
    ) -> str:
        """Render a template string with the given context.

        Uses Python's string formatting as a simplified template engine.
        Supports basic Go template syntax.
        """
        template_str = self._prepare_template(template_str)

        local_context = dict(context)

        def process_template(template: str) -> str:
            result = template

            result = re.sub(
                r"\{\{\s*\$(\w+)\s*:=\s*(.+?)\s*\}\}",
                lambda m: _process_assignment(m, local_context),
                result,
            )

            result = re.sub(
                r"\{\{(\s*if\s+.*?\s*)\}\}(.*?)\{\{(\s*end\s*)\}\}",
                lambda m: _process_if(m, local_context),
                result,
                flags=re.DOTALL,
            )

            result = re.sub(
                r"\{\{\s*(\w+)\s+(.*?)\s*\}\}",
                lambda m: _process_function(m, local_context),
                result,
            )

            result = re.sub(
                r"\{\{\s*index\s+(\S+)\s+(\d+)\s*\}\}",
                lambda m: _process_index(m, local_context),
                result,
            )

            result = re.sub(
                r"\{\{\s*\$(\w+)(\.\w+)*\s*\}\}",
                lambda m: _process_variable(m, local_context),
                result,
            )

            result = re.sub(
                r"\{\{\s*\.(\w+)(\.\w+)*\s*\}\}",
                lambda m: _process_dot_variable(m, local_context),
                result,
            )

            return result

        def _process_assignment(match, ctx):
            var_name = match.group(1)
            expr = match.group(2).strip()
            value = _evaluate_expression(expr, ctx)
            ctx[var_name] = value
            return ""

        def _process_if(match, ctx):
            condition = match.group(1).strip()
            content = match.group(2)
            if _evaluate_condition(condition, ctx):
                return content
            return ""

        def _process_function(match, ctx):
            func_name = match.group(1).strip()
            args_str = match.group(2).strip()
            args = [a.strip() for a in args_str.split() if a.strip()]
            return _call_function(func_name, args, ctx)

        def _process_index(match, ctx):
            var_path = match.group(1).strip()
            idx = int(match.group(2))
            value = _resolve_path(var_path, ctx)
            if isinstance(value, list | tuple) and idx < len(value):
                return str(value[idx])
            return ""

        def _process_variable(match, ctx):
            match.group(0)
            var_name = match.group(1)
            rest = match.group(2) or ""
            value = ctx.get(var_name, "")
            if rest:
                parts = [p.lstrip(".") for p in rest.split(".") if p]
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part, "")
                    else:
                        return ""
            return str(value) if value is not None else ""

        def _process_dot_variable(match, ctx):
            path = match.group(1).strip()
            rest = match.group(2) or ""
            value = ctx.get(path, "")
            if rest:
                parts = [p.lstrip(".") for p in rest.split(".") if p]
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part, "")
                    else:
                        return ""
            return str(value) if value is not None else ""

        def _evaluate_expression(expr, ctx):
            expr = expr.strip()
            if expr.startswith("."):
                return _resolve_path(expr.lstrip("."), ctx)
            if expr.startswith('"') and expr.endswith('"'):
                return expr[1:-1]
            if expr.startswith("'") and expr.endswith("'"):
                return expr[1:-1]
            if expr in ctx:
                return ctx[expr]
            return expr

        def _evaluate_condition(condition, ctx):
            condition = condition.strip()
            if condition.startswith("if"):
                condition = condition[2:].strip()
            if condition.startswith("eq"):
                condition = condition[2:].strip()
                parts = condition.split()
                if len(parts) >= 2:
                    left = _resolve_path(parts[0].strip(), ctx)
                    right = _resolve_path(parts[1].strip(), ctx)
                    return str(left) == str(right)
            return False

        def _resolve_path(path, ctx):
            if path.startswith('"') and path.endswith('"'):
                return path[1:-1]
            if path.startswith("'"):
                return path
            if path.startswith("."):
                path = path[1:]
            parts = [p for p in path.split(".") if p]
            value = ctx
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, "")
                elif hasattr(value, part):
                    value = getattr(value, part, "")
                else:
                    return ""
            return value if value is not None else ""

        def _call_function(func_name, args, ctx):
            if func_name == "GetCSTtime":
                if args:
                    time_val = _resolve_path(args[0], ctx)
                    if isinstance(time_val, datetime):
                        return time_val.strftime("%Y-%m-%d %H:%M:%S")
                    return str(time_val)
                return ""
            return "{{" + func_name + " " + " ".join(args) + "}}"

        result = process_template(template_str)
        return result

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
        labels: dict[str, Any],
        annotations: dict[str, Any],
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
            labels: Alert labels
            annotations: Alert annotations

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
            labels=labels,
            annotations=annotations,
        )

        rendered_subject = None
        if template.subject_template:
            rendered_subject = self.render_template(template.subject_template, context)

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
                "starts_at": datetime.utcnow(),
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
