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

    # Security
    secret_key: str = Field(default="your-secret-key-change-in-production", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=480, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://opsmanager:opsmanager@localhost:5432/opsmanager",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")

    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND"
    )

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
    prometheus_url: str = Field(default="http://192.168.23.31:9090", alias="PROMETHEUS_URL")
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
    minio_endpoint: str = Field(default="192.168.23.36:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    # IT Reporter Configuration
    itreporter_chat_id: str = Field(default="", alias="ITREPORTER_CHAT_ID")
    itreporter_minio_bucket: str = Field(default="reports", alias="ITREPORTER_MINIO_BUCKET")
    itreporter_presigned_url_expires_hours: int = Field(default=2, alias="ITREPORTER_PRESIGNED_URL_EXPIRES_HOURS")
    itreporter_report_path: str = Field(default="devops-scripts/{date}-health-check.html", alias="ITREPORTER_REPORT_PATH")

    # Ansible SSH Configuration
    ansible_ssh_host: str = Field(default="192.168.23.38", alias="ANSIBLE_SSH_HOST")
    ansible_ssh_port: int = Field(default=22, alias="ANSIBLE_SSH_PORT")
    ansible_ssh_username: str = Field(default="root", alias="ANSIBLE_SSH_USERNAME")
    ansible_ssh_password: str = Field(default="P@ssw0rd123", alias="ANSIBLE_SSH_PASSWORD")
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

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from string."""
        if not self.cors_origins_str:
            return ["http://localhost:3000", "http://localhost:5173"]
        return [origin.strip() for origin in self.cors_origins_str.split(",")]

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
