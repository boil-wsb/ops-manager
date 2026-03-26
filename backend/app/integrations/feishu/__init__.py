def get_feishu_service() -> "FeishuService":  # noqa: F821
    """Get or create Feishu service singleton (lazy import)."""
    from app.integrations.feishu.service import FeishuService, feishu_service
    return feishu_service if feishu_service else FeishuService()


def get_sync_users():
    """Lazy import sync_users function."""
    from app.integrations.feishu.sync_service import sync_users
    return sync_users


def get_fetch_all_users():
    """Lazy import fetch_all_users function."""
    from app.integrations.feishu.sync_service import fetch_all_users
    return fetch_all_users


__all__ = ["get_feishu_service", "get_sync_users", "get_fetch_all_users"]
