import json
import logging
from aiokafka import AIOKafkaProducer
from shared.config import settings

logger = logging.getLogger(__name__)

class KafkaProducerManager:
    def __init__(self):
        self.producer: AIOKafkaProducer | None = None

    async def start(self):
        bootstrap_servers = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        try:
            await producer.start()
            self.producer = producer  # Сохраняем ТОЛЬКО если старт прошёл успешно!
            logger.info("✅ Kafka Producer успешно запущен!")
        except Exception as e:
            await producer.stop()  # <--- Закрываем продюсер при ошибке
            self.producer = None
            logger.warning(f"⚠️ Не удалось подключиться к Kafka ({e}). Producer работает в режиме заглушки.")

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka Producer остановлен.")

    async def send_event(self, topic: str, event_data: dict):
        if self.producer:
            await self.producer.send_and_wait(topic, event_data)
            logger.info(f"📨 Событие отправлено в топик '{topic}': {event_data.get('event_id')}")
        else:
            logger.warning(f"[MOCK KAFKA] Событие ДОЛЖНО БЫТЬ отправлено в '{topic}': {event_data}")


kafka_manager = KafkaProducerManager()