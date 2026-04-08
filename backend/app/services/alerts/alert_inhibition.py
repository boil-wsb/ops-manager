"""
Alert inhibition service.
"""
import re
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.crud.crud_alert import crud_alert_silence
from app.models.alert import AlertSilence

logger = get_logger(__name__)

# Cache TTL in seconds
CACHE_TTL = 60


class AlertInhibitionService:
    """Service for checking alert inhibition/silencing rules."""

    def __init__(self):
        """Initialize the service with a cache."""
        self._cache: dict[str, tuple[list[AlertSilence], datetime]] = {}
        self._cache_ttl = CACHE_TTL

    def _get_cache_key(self, labels: dict[str, Any]) -> str:
        """Generate cache key from labels."""
        sorted_labels = sorted(labels.items())
        return str(sorted_labels)

    def _is_cache_valid(self, cached_time: datetime) -> bool:
        """Check if cache is still valid."""
        elapsed = (datetime.utcnow() - cached_time).total_seconds()
        return elapsed < self._cache_ttl

    async def get_active_silences_cached(
        self,
        db: AsyncSession,
    ) -> list[AlertSilence]:
        """Get active silences with caching."""
        cache_key = "__all_active_silences__"
        now = datetime.utcnow()

        if cache_key in self._cache:
            silences, cached_time = self._cache[cache_key]
            if self._is_cache_valid(cached_time):
                return silences

        silences = await crud_alert_silence.get_active_silences(db, current_time=now)
        self._cache[cache_key] = (silences, now)
        return silences

    def _match_exact_labels(
        self,
        alert_labels: dict[str, Any],
        silence_labels: dict[str, Any],
    ) -> bool:
        """Match alerts against silence rules using exact label matching.

        All silence match_labels must be present in alert_labels with exact values.
        """
        return all(alert_labels.get(key) == value for key, value in silence_labels.items())

    def _match_regex_pattern(
        self,
        alert_labels: dict[str, Any],
        pattern: str,
    ) -> bool:
        """Match alerts against silence rules using regex pattern.

        The pattern should match against the label string representation.
        """
        try:
            regex = re.compile(pattern)
            # Create a string representation of labels for matching
            labels_str = str(sorted(alert_labels.items()))
            return regex.search(labels_str) is not None
        except re.error:
            logger.warning(f"Invalid regex pattern: {pattern}")
            return False

    def is_alert_suppressed(
        self,
        alert_labels: dict[str, Any],
        silences: list[AlertSilence],
    ) -> tuple[bool, AlertSilence | None]:
        """Check if an alert should be suppressed by any silence rule.

        Args:
            alert_labels: Labels from the alert
            silences: List of active silence rules

        Returns:
            Tuple of (is_suppressed, matched_silence)
        """
        for silence in silences:
            if silence.match_labels and self._match_exact_labels(alert_labels, silence.match_labels):
                logger.info(f"Alert matched silence rule: {silence.name}")
                return True, silence

            if silence.match_pattern and self._match_regex_pattern(alert_labels, silence.match_pattern):
                logger.info(f"Alert matched silence regex pattern: {silence.name}")
                return True, silence

        return False, None

    async def check_alert_inhibition(
        self,
        db: AsyncSession,
        alert_labels: dict[str, Any],
    ) -> tuple[bool, int | None]:
        """Check if an alert should be inhibited/silenced.

        Args:
            db: Database session
            alert_labels: Labels from the Alertmanager alert

        Returns:
            Tuple of (is_suppressed, silence_id)
        """
        silences = await self.get_active_silences_cached(db)
        is_suppressed, matched_silence = self.is_alert_suppressed(alert_labels, silences)

        if is_suppressed and matched_silence:
            return True, matched_silence.id
        return False, None

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()


# Global service instance
alert_inhibition_service = AlertInhibitionService()
