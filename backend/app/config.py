"""
Application configuration using Pydantic Settings.
"""

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = Field(default="OpsManager V2", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    timezone: str = Field(default="Asia/Shanghai", alias="APP_TIMEZONE")

    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=480, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")

    # Database
    db_user: str = Field(default="opsmanager", alias="DB_USER")
    db_password: str = Field(default="opsmanager", alias="DB_PASSWORD")
    db_name: str = Field(default="opsmanager", alias="DB_NAME")
    database_url: str = Field(
        default="postgresql+asyncpg://opsmanager:opsmanager@localhost:5432/opsmanager",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")

    # CORS - Use string type and parse manually
    cors_origins_str: str = Field(
        default="http://localhost:3000,http://localhost:5173", alias="CORS_ORIGINS"
    )

    # Email (optional)
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str | None = Field(default=None, alias="SMTP_USER")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_tls: bool = Field(default=True, alias="SMTP_TLS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")  # json or console

    # Logging File Configuration
    log_file_enabled: bool = Field(default=True, alias="LOG_FILE_ENABLED")
    log_file_dir: str = Field(default="logs", alias="LOG_FILE_DIR")
    log_file_retention_days: int = Field(default=30, alias="LOG_FILE_RETENTION_DAYS")

    # Audit Log Configuration
    audit_log_enabled: bool = Field(default=True, alias="AUDIT_LOG_ENABLED")
    audit_log_db_retention_days: int = Field(default=90, alias="AUDIT_LOG_DB_RETENTION_DAYS")
    audit_log_file_retention_days: int = Field(default=365, alias="AUDIT_LOG_FILE_RETENTION_DAYS")
    audit_log_file_path: str = Field(default="logs/audit.log", alias="AUDIT_LOG_FILE_PATH")
    audit_log_async: bool = Field(default=True, alias="AUDIT_LOG_ASYNC")
    audit_log_max_file_size: str = Field(default="100MB", alias="AUDIT_LOG_MAX_FILE_SIZE")
    audit_log_backup_count: int = Field(default=10, alias="AUDIT_LOG_BACKUP_COUNT")

    # Prometheus Configuration
    prometheus_url: str = Field(default="http://localhost:9090", alias="PROMETHEUS_URL")
    prometheus_sync_interval: int = Field(default=30, alias="PROMETHEUS_SYNC_INTERVAL")  # minutes
    prometheus_timeout: int = Field(default=10, alias="PROMETHEUS_TIMEOUT")  # seconds
    prometheus_retry_count: int = Field(default=3, alias="PROMETHEUS_RETRY_COUNT")

    # Rate Limiting
    disable_rate_limit: bool = Field(default=False, alias="DISABLE_RATE_LIMIT")

    # Feishu (Lark) Configuration
    feishu_app_id: str | None = Field(default=None, alias="FEISHU_APP_ID")
    feishu_app_secret: str | None = Field(default=None, alias="FEISHU_APP_SECRET")
    feishu_enable: bool = Field(default=False, alias="FEISHU_ENABLE")

    # MinIO Configuration
    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="", alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    # IT Reporter Configuration
    itreporter_chat_id: str = Field(default="", alias="ITREPORTER_CHAT_ID")
    itreporter_minio_bucket: str = Field(default="devops-scripts", alias="ITREPORTER_MINIO_BUCKET")
    itreporter_presigned_url_expires_hours: int = Field(
        default=2, alias="ITREPORTER_PRESIGNED_URL_EXPIRES_HOURS"
    )
    itreporter_report_path: str = Field(
        default="IT-days-reporter/health_check_detailed_report_{date_compact}",
        alias="ITREPORTER_REPORT_PATH",
    )
    itreporter_download_base_url: str = Field(
        default="http://localhost:8080", alias="ITREPORTER_DOWNLOAD_BASE_URL"
    )

    # Ansible SSH Configuration
    ansible_ssh_host: str = Field(default="localhost", alias="ANSIBLE_SSH_HOST")
    ansible_ssh_port: int = Field(default=22, alias="ANSIBLE_SSH_PORT")
    ansible_ssh_username: str = Field(default="", alias="ANSIBLE_SSH_USERNAME")
    ansible_ssh_password: str = Field(default="", alias="ANSIBLE_SSH_PASSWORD")
    ansible_ssh_key_path: str | None = Field(default=None, alias="ANSIBLE_SSH_KEY_PATH")
    ansible_command: str = Field(
        default="cd /home/shdy/.ansible && ansible-playbook -i inventory/incloud_all/hosts playbooks/site.yml -l all",
        alias="ANSIBLE_COMMAND",
    )
    ansible_script: str | None = Field(
        default=None,
        alias="ANSIBLE_SCRIPT",
        description="Shell script content to execute on remote server. If set, this takes precedence over ansible_command.",
    )
    ansible_local_script_path: str | None = Field(
        default=None,
        alias="ANSIBLE_LOCAL_SCRIPT_PATH",
        description="Local script file path to read and execute on remote server. Takes precedence over ansible_script and ansible_command.",
    )
    ansible_schedule_hour: int = Field(default=12, alias="ANSIBLE_SCHEDULE_HOUR")
    ansible_schedule_minute: int = Field(default=0, alias="ANSIBLE_SCHEDULE_MINUTE")

    # Auth Whitelist Configuration
    auth_excluded_paths: str = Field(default="", alias="AUTH_EXCLUDED_PATHS")
    auth_trusted_networks: str = Field(default="", alias="AUTH_TRUSTED_NETWORKS")

    # Alert Aggregation Configuration
    alert_aggregation_window_seconds: int = Field(
        default=300, alias="ALERT_AGGREGATION_WINDOW_SECONDS"
    )

    # CRM Sync Configuration
    crm_sync_url: str = Field(default="http://192.168.23.36:9091", alias="CRM_SYNC_URL")
    crm_sync_timeout: int = Field(default=30, alias="CRM_SYNC_TIMEOUT")

    # Default Admin Configuration
    default_admin_username: str = Field(default="admin", alias="DEFAULT_ADMIN_USERNAME")
    default_admin_password: str = Field(default="admin123", alias="DEFAULT_ADMIN_PASSWORD")

    # Feishu Sync Default Password
    feishu_sync_default_password: str = Field(
        default="mh123456", alias="FEISHU_SYNC_DEFAULT_PASSWORD"
    )

    # IT Feedback Local IP Mapping
    local_ip_mapping_str: str = Field(default="", alias="LOCAL_IP_MAPPING")

    # Git Repository Management Configuration
    git_repo_url: str = Field(
        default="http://192.168.23.19/devops/infrastructure/prometheus.git",
        alias="GIT_REPO_URL",
    )
    git_private_token: str = Field(default="", alias="GIT_PRIVATE_TOKEN")
    git_repo_base_dir: str = Field(default="/app/git-repos", alias="GIT_REPO_LOCAL_DIR")
    git_repo_sparse_paths: str = Field(default="conf/prometheus", alias="GIT_REPO_SPARSE_PATHS")
    git_command_timeout: int = Field(default=60, alias="GIT_COMMAND_TIMEOUT")
    git_commit_user_name: str = Field(default="ops-manager", alias="GIT_COMMIT_USER_NAME")
    git_commit_user_email: str = Field(
        default="ops-manager@ops-manager.local", alias="GIT_COMMIT_USER_EMAIL"
    )

    def _parse_list(self, raw: str) -> list[str]:
        """Parse comma/space separated string into a non-empty list."""
        return [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]

    @property
    def git_repo_sparse_path_list(self) -> list[str]:
        return self._parse_list(self.git_repo_sparse_paths)

    @property
    def git_repo_base_dir_abs(self) -> str:
        """将 git 仓库本地目录解析为稳定绝对路径。

        GIT_REPO_LOCAL_DIR 允许配置相对值（如 'git-repos'），生产/容器内为绝对路径
        （'/app/git-repos'）。相对值会锚定到后端工程根（config.py 的上上级目录），
        避免随进程 CWD 变化导致目录嵌套错位（如 git-repos/git-repos/prometheus）。"""
        base = self.git_repo_base_dir
        p = Path(base)
        if p.is_absolute():
            return str(p)
        return str(Path(__file__).resolve().parent.parent / p)

    # PC Client Info Configuration
    pcinfo_pushgateway_url: str = Field(
        default="http://localhost:9091/metrics/job/pcinfo", alias="PCINFO_PUSHGATEWAY_URL"
    )
    pcinfo_update_server_host: str = Field(default="localhost", alias="PCINFO_UPDATE_SERVER_HOST")
    pcinfo_update_server_port: int = Field(default=8080, alias="PCINFO_UPDATE_SERVER_PORT")

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from string."""
        if not self.cors_origins_str:
            return ["http://localhost:3000", "http://localhost:5173"]
        return [origin.strip() for origin in self.cors_origins_str.split(",")]

    @property
    def local_ip_mapping(self) -> dict[str, str]:
        """Parse local IP mapping from string."""
        if not self.local_ip_mapping_str:
            return {}
        mapping = {}
        for pair in self.local_ip_mapping_str.split(","):
            pair = pair.strip()
            if ":" in pair:
                key, value = pair.split(":", 1)
                mapping[key.strip()] = value.strip()
        return mapping

    @property
    def async_database_url(self) -> str:
        """Get async database URL."""
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Validate security settings in production environment."""
        if not self.debug:
            if self.secret_key == "your-secret-key-change-in-production":
                raise ValueError(
                    "SECRET_KEY must be set in production environment. "
                    "Please set a secure random string via SECRET_KEY environment variable."
                )
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters long for security.")
        return self


# Global settings instance
settings = Settings()
