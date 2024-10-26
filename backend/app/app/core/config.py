import os
from enum import Enum

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class ModeEnum(str, Enum):
    development = "development"
    production = "production"
    testing = "testing"


class Settings(BaseSettings):
    PROJECT_NAME: str = "app"
    BACKEND_CORS_ORIGINS: list[str] | list[AnyHttpUrl] = ["http://51.75.62.15:8083"]
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

    # Email
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_SERVER: str
    MAIL_PORT: int
    MAIL_FROM_NAME: str
    SENDING_NOTIFICATIONS: bool


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
