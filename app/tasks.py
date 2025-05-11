import requests

from app.config import celery_app, settings


@celery_app.task(
    name='delete_file_scheduled',
    bind=True,
    max_retries=3,
    default_retry_delay=5
)
def delete_file_scheduled(self, file_id, dell_id):
    """Задача для отложенного удаления файла"""
    try:
        response = requests.delete(f"{settings.BASE_URL}/api/delete/{file_id}/{dell_id}")
        response.raise_for_status()
        return response.status_code
    except requests.RequestException as exc:
        self.retry(exc=exc)
    except Exception as e:
        return None
