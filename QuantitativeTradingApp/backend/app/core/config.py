"""全局配置（Pydantic Settings，环境变量注入）。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils.dates import SHANGHAI_TZ


class Settings(BaseSettings):
    """应用配置。环境变量见 docs/appendices/deployment/environment.md。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "A股量化选股系统"
    api_prefix: str = "/api"
    debug: bool = False

    # 数据库 / Redis
    database_url: str = (
        "postgresql+psycopg://quant:quant@localhost:5432/quant"
    )
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl: int = 30 * 60  # 30 分钟
    jwt_refresh_ttl: int = 7 * 24 * 3600  # 7 天

    # 时区：所有定时任务、日期存储统一 Asia/Shanghai
    tz: str = "Asia/Shanghai"

    # 调度
    schedule_enabled: bool = True
    schedule_cron_hour: int = 17
    schedule_cron_minute: int = 0
    lock_ttl: int = 7200  # 分布式锁 TTL（秒）

    # 限流（慢速接口）
    rate_limit_enabled: bool = True  # 关闭后 slowapi 直接放行（测试/压测环境用）
    rate_limit_storage: str | None = None  # 默认取 redis_url
    trust_xff: bool = True  # 是否信任 Nginx 透传的 X-Forwarded-For
    cors_origins: str = "*"  # 逗号分隔；开发环境默认全部

    # 可观测性
    log_dir: str = "/var/log/app"
    log_level: str = "INFO"

    @property
    def rate_limit_storage_uri(self) -> str:
        return self.rate_limit_storage or self.redis_url

    @property
    def log_dir_path(self) -> Path:
        return Path(self.log_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
