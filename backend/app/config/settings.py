"""运行配置：所有值都可用同名环境变量覆盖。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # --- PostgreSQL ---
    DB_NAME: str = "rfmseg_db"
    DB_USER: str = "rfmseg_user"
    DB_PASSWORD: str = "rfmseg_pwd"
    DB_HOST: str = "db"
    DB_PORT: int = 5432

    # --- auth ---
    JWT_SECRET: str = "rfmseg_dev_jwt_secret_change_me_1109"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 8

    # --- infra ---
    REDIS_URL: str = "redis://redis:6379/0"
    ARTIFACT_DIR: str = "/data/artifacts"

    # --- 运行配额 / 限流 ---
    RUN_DAILY_QUOTA: int = 20
    RATE_WINDOW_SECONDS: int = 60
    RATE_WINDOW_MAX: int = 60

    # --- demo seed ---
    SEED_DEMO: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
