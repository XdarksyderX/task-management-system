import os
from kafka import KafkaProducer
import json
import logging

logger = logging.getLogger(__name__)


KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(",")


USER_ACTIVITIES_TOPIC = "user-activities"
TASK_EVENTS_TOPIC = "task-events"
SYSTEM_NOTIFICATIONS_TOPIC = "system-notifications"
ANALYTICS_EVENTS_TOPIC = "analytics-events"


class KafkaConnection:
    _producer = None

    @classmethod
    def get_producer(cls):
        if cls._producer is None:
            try:
                cls._producer = KafkaProducer(
                    bootstrap_servers=KAFKA_SERVERS,
                    value_serializer=lambda x: json.dumps(x).encode("utf-8"),
                    key_serializer=lambda x: x.encode("utf-8") if x else None,
                    retries=3,
                    retry_backoff_ms=300,
                    request_timeout_ms=30000,
                    acks="all",
                )
                logger.info("Kafka producer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {e }")
                cls._producer = None
        return cls._producer

    @classmethod
    def close_producer(cls):
        if cls._producer:
            cls._producer.close()
            cls._producer = None
