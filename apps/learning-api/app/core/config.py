from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Learning Engine 配置，从环境变量 / .env 读取。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Learning Engine"
    debug: bool = False

    # 数据库连接（postgresql+psycopg://），由环境变量 DATABASE_URL 注入
    database_url: str = "postgresql+psycopg://user:CHANGE_ME@localhost:5432/db"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()