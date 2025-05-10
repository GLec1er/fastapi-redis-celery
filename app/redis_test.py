import redis

from app.config import settings

r = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    password=settings.redis_password,
    ssl=False,
    db=0,
)


try:
    response = r.ping()
    if response:
        print("Подключение к Redis успешно!")
    else:
        print("Не удалось подключиться к Redis.")
except Exception as e:
    print(f"Произошла ошибка: {e}")
