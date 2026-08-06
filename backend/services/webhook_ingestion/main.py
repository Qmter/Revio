from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .router import router, api_router  # <--- Добавили api_router
from .kafka import kafka_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await kafka_manager.start()
    yield
    await kafka_manager.stop()


app = FastAPI(
    title="AI Code Review API & Webhook Service",
    version="1.0.0",
    lifespan=lifespan,
)

# Разрешаем запросы с React (Vite)
# Разрешаем запросы с React (Vite / Nginx)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:80",
        "http://localhost:5173" # На случай запуска фронта без докера
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(api_router)  # <--- Подключили эндпоинты для фронтенда!


@app.get("/health")
async def health_check():
    return {"service": "api_gateway", "status": "ok"}