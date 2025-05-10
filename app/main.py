import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import settings
from app.pages.router import pages_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все источники
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы
    allow_headers=["*"],  # Разрешаем все заголовки
)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app.mount("/files", StaticFiles(directory=settings.UPLOAD_DIR), name="files")
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

app.include_router(api_router)
app.include_router(pages_router)


@app.get("/", response_class=HTMLResponse, tags=['SPA'])
def spa():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🐍 FastAPI + Celery + Redis</title>
        <style>
            body {
                font-family: 'Comic Sans MS', cursive, sans-serif;
                background-color: #fdf6e3;
                text-align: center;
                margin-top: 10%;
            }
            h1 {
                color: #2aa198;
                font-size: 48px;
            }
            p {
                color: #657b83;
                font-size: 20px;
            }
        </style>
    </head>
    <body>
        <h1>🚀 Ура! Сервер работает! 🎉</h1>
        <p>Добро пожаловать в FastAPI + Redis + Celery мир!</p>
        <p>Зайди на <a href="/docs">/docs</a>, чтобы увидеть магию Swagger ✨</p>
    </body>
    </html>
    """
