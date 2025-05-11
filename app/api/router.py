import os
import datetime
from fastapi import APIRouter, UploadFile, HTTPException, Form
from loguru import logger
from fastapi.responses import HTMLResponse

from app.api.utils import generate_random_string
from app.config import settings, celery_app, redis_client


api_router = APIRouter(
    tags=['API'],
    prefix='/api',
)


@api_router.post("/upload/")
async def upload_file(
    file: UploadFile,
    expiration_minutes: int = Form(...)
):
    try:
        # Прочитать загруженный файл
        file_content = await file.read()

        max_file_size = 5 * 1024 * 1024  # 5 МБ в байтах
        if len(file_content) > max_file_size:
            raise HTTPException(status_code=413, detail="Превышен максимальный размер файла (5 МБ).")

        upload_dir = settings.UPLOAD_DIR
        total_size = sum(os.path.getsize(os.path.join(upload_dir, f)) for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f)))
        max_total_size = 100 * 1024 * 1024  # 100 МБ в байтах
        if total_size + len(file_content) > max_total_size:
            raise HTTPException(status_code=507, detail="Превышен общий лимит размера файлов (100 МБ). Освободите место и повторите попытку.")

        start_file_name = file.filename
        # Сгенерировать уникальное имя файла и ID для удаления
        file_extension = os.path.splitext(file.filename)[1]
        file_id = generate_random_string(12)
        dell_id = generate_random_string(12)

        # Сохранить файл на диск
        file_path = os.path.join(settings.UPLOAD_DIR, file_id + file_extension)
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Рассчитать время истечения в секундах
        expiration_seconds = expiration_minutes * 60
        expiration_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expiration_seconds)

        # Запланировать задачу для удаления файла после истечения времени
        celery_app.send_task('delete_file_scheduled', args=[file_id, dell_id], countdown=expiration_seconds)
        # delete_file_scheduled.apply_async(args=[file_id, dell_id], countdown=expiration_seconds)

        # URL-адреса для метаданных
        download_url = f"{settings.BASE_URL}/files/{file_id + file_extension}"
        view_url = f"{settings.BASE_URL}/view_file/{file_id}"

        # Сохранить метаданные в Redis
        redis_key = f"file:{file_id}"  # Уникальный ключ для файла
        redis_client.hmset(
            redis_key,
            {
                "file_path": file_path,
                "dell_id": dell_id,
                "download_url": download_url,
                "expiration_time": int(expiration_time.timestamp()),
                "start_file_name": start_file_name
            }
        )

        return {
            "message": "Файл успешно загружен",
            "file_id": file_id,
            "dell_id": dell_id,
            "download_url": download_url,
            "view_url": view_url,
            "expiration_time": expiration_time.isoformat(),
            "expiration_seconds": expiration_seconds
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки файла: {str(e)}")


@api_router.delete("/delete/{file_id}/{dell_id}")
async def delete_file(
    file_id: str,
    dell_id: str
):
    redis_key = f"file:{file_id}"
    file_info = redis_client.hgetall(redis_key)

    if not file_info:
        raise HTTPException(status_code=404, detail="Файл не найден")

    dell_id_redis = file_info.get(b"dell_id").decode()
    if dell_id_redis != dell_id:
        raise HTTPException(status_code=403, detail="Не совпадает айди удаления с айди удаления файла")

    file_path = file_info.get(b"file_path").decode()

    # Удаление файла и очистка записи в Redis
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Файл {file_path} успешно удален!")
        else:
            logger.warning(f"Файл {file_path} не найден.")

        redis_client.delete(redis_key)
        return {"message": "Файл успешно удален и запись в Redis очищена!"}

    except OSError as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления файла: {str(e)}")


@api_router.get("/files/", response_class=HTMLResponse)
async def list_files():
    keys = redis_client.keys("file:*")
    files = []

    for key in keys:
        data = redis_client.hgetall(key)
        files.append({
            "file_id": key.decode().split(":")[1],
            "start_file_name": data.get(b"start_file_name", b"").decode(),
            "download_url": data.get(b"download_url", b"").decode(),
            "expiration_time": datetime.datetime.fromtimestamp(
                int(data.get(b"expiration_time", 0))
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "dell_id": data.get(b"dell_id", b"").decode(),
        })

    html = """
    <html>
    <head>
        <title>Загруженные файлы</title>
        <style>
            body {
                font-family: 'Segoe UI', sans-serif;
                background-color: #f9f9f9;
                margin: 0;
                padding: 20px;
                color: #333;
            }

            h1 {
                text-align: center;
                margin-bottom: 30px;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                background-color: white;
                box-shadow: 0 0 10px rgba(0,0,0,0.05);
                border-radius: 8px;
                overflow: hidden;
            }

            th, td {
                padding: 12px 16px;
                border-bottom: 1px solid #eaeaea;
                text-align: left;
            }

            th {
                background-color: #f0f0f0;
                font-weight: 600;
            }

            tr:nth-child(even) {
                background-color: #fafafa;
            }

            tr:hover {
                background-color: #f1f1f1;
            }

            a {
                color: #007bff;
                text-decoration: none;
            }

            a:hover {
                text-decoration: underline;
            }

            button {
                background-color: #dc3545;
                border: none;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                transition: background-color 0.2s ease-in-out;
            }

            button:hover {
                background-color: #c82333;
            }

            .footer {
                text-align: center;
                margin-top: 40px;
                font-size: 16px;
            }

            .footer a {
                font-weight: 500;
                background-color: #007bff;
                color: white;
                padding: 8px 14px;
                border-radius: 6px;
                text-decoration: none;
            }

            .footer a:hover {
                background-color: #0056b3;
            }
        </style>
    </head>
    <body>
        <h1>Список загруженных файлов</h1>
        <table>
            <tr>
                <th>ID</th>
                <th>Оригинальное имя</th>
                <th>Ссылка</th>
                <th>Удалить</th>
                <th>Истекает</th>
            </tr>
    """

    for file in files:
        html += f"""
            <tr>
                <td><a href="/view_file/{file['file_id']}" target="_blank">{file['file_id']}</a></td>
                <td>{file['start_file_name']}</td>
                <td><a href="{file['download_url']}" target="_blank">Скачать</a></td>
                <td><button onclick="deleteFile('{file['file_id']}', '{file['dell_id']}')">Удалить</button></td>
                <td>{file['expiration_time']}</td>
            </tr>
        """

    html += """
        </table>
        <div class="footer">
            <p><a href="/">Загрузить новый файл</a></p>
        </div>
        <script>
            async function deleteFile(fileId, dellId) {
                const response = await fetch(`/api/delete/${fileId}/${dellId}`, {
                    method: 'DELETE'
                });
                if (response.ok) {
                    alert('Файл удалён');
                    window.location.reload();
                } else {
                    alert('Ошибка удаления файла');
                }
            }
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html)
