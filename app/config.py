import os
import ssl
import redis

from celery import Celery
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import Field


class Settings(BaseSettings):
    debug: bool = Field(
        default=False,
        description="Run in debug mode",
    )
    redis_port: int = Field(
        default=6379,
        description='Redis port',
    )
    redis_password: str | None = Field(
        default=None,
        description='Redis password',
    )
    redis_host: str = Field(
        default='localhost',
        description='Redis host',
    )

    BASE_URL: str = Field(
        default='http://localhost:8000',
        description='Base URL',
    )
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    UPLOAD_DIR: str = os.path.join(BASE_DIR, 'app/uploads')
    STATIC_DIR: str = os.path.join(BASE_DIR, 'app/static')

    model_config = SettingsConfigDict(env_file=f"{BASE_DIR}/.env")

    @property
    def get_redis_url(self) -> str:
        host = 'localhost' if self.debug else self.redis_host
        if self.redis_password:
            return f"redis://:{self.redis_password}@{host}:{self.redis_port}/0"
        return f"redis://{host}:{self.redis_port}/0"


settings = Settings()


celery_app = Celery(
    "celery_worker",
    broker=settings.get_redis_url,
    backend=settings.get_redis_url
)
celery_app.autodiscover_tasks(['app.tasks'])


ssl_options = {
    "ssl_cert_reqs": ssl.CERT_NONE,
}

celery_app.conf.update(
    # broker_use_ssl=ssl_options, # only rediss
    # redis_backend_use_ssl=ssl_options, # only rediss
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    enable_utc=True,
    timezone='Europe/Moscow',  # Устанавливаем московское время
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    password=settings.redis_password,
    ssl=False,
    db=0,
)
