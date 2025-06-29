import os
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- ИЗМЕНЕНИЕ ЗДЕСЬ: Определяем абсолютный путь к .env ---
# Наш рабочий каталог в Docker - /app
# Мы строим путь от текущего файла (settings.py) вверх по иерархии до корня проекта.
# Это самый надежный способ найти .env файл.
# dirname(__file__) -> /app/app/core
# dirname(dirname(__file__)) -> /app/app
# dirname(dirname(dirname(__file__))) -> /app
# os.path.join(...) -> /app/.env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')


class Settings(BaseSettings):
    # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Явно указываем путь к файлу ---
    model_config = SettingsConfigDict(env_file=env_path, env_file_encoding='utf-8')

    BOT_TOKEN: SecretStr
    ADMIN_IDS: list[int]

    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    REDIS_HOST: str
    REDIS_PORT: int

    WEB_APP_BASE_URL: str
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

# Не забудьте удалить этот блок после отладки!
print("="*50)
print(f"DEBUG: Trying to load .env from: {env_path}")
print("DEBUG: Loaded settings object:")
print(settings.model_dump())
print("="*50)