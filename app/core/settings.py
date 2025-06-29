from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    BOT_TOKEN: SecretStr
    ADMIN_IDS: list[int]

    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    REDIS_HOST: str
    REDIS_PORT: int

    # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Добавляем новую переменную ---
    WEB_APP_BASE_URL: str
class Settings(BaseSettings):
    # ...
    WEB_APP_BASE_URL: str
    # --- НОВАЯ ПЕРЕМЕННАЯ ---
    WEBHOOK_SECRET: SecretStr
    @property
    def DATABASE_URL_asyncpg(self) -> str:
        return (f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}")

    @property
    def DATABASE_URL_psycopg(self) -> str:
        return (f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD.get_secret_value()}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}")

settings = Settings()