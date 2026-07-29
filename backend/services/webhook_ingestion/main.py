from contextlib import asynccontextmanager
from fastapi import FastAPI
from .router import router
from .kafka import kafka_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте приложения запускаем Kafka Producer
    await kafka_manager.start()
    yield
    # При остановке — мягко закрываем соединение
    await kafka_manager.stop()


app = FastAPI(
    title="Webhook Ingestion Service",
    description="Прием вебхуков от GitHub/GitLab и валидация HMAC",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health_check():
    return {"service": "webhook_ingestion", "status": "ok"}