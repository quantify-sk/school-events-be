import os
from enum import Enum

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class ModeEnum(str, Enum):
    development = "development"
    production = "production"
    testing = "testing"


class Settings(BaseSettings):
    PROJECT_NAME: str = "app"
    BACKEND_CORS_ORIGINS: list[str] | list[AnyHttpUrl]
    MODE: ModeEnum = ModeEnum.development
    API_VERSION: str = "v1"
    API_V1_STR: str = f"/api/{API_VERSION}"

    # Postgres
    DATABASE_LOCAL_URI: str
    DATABASE_URI: str
    DATABASE_HOST: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    DATABASE_NAME: str
    DATABASE_PORT: int

    # 5 minutes
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # 30 min
    REFRESH_TOKEN_EXPIRE_MINUTES: int

    # Change on production !!! openssl rand -hex 64
    SECRET_KEY: str
    ALGORITHM: str

    # API login and password
    API_LOGIN: str
    API_PASSWORD: str

    class Config:
        case_sensitive = True
        env_file = os.path.expanduser("~/.env")


settings = Settings()
