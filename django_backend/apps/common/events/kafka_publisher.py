import json
import logging
from django.conf import settings
from apps.common.kafka.config import KafkaConnection
from .base import EventPublisher, EventPayload

logger = logging.getLogger(__name__)

class KafkaEventPublisher(EventPublisher):
    """Kafka implementation of EventPublisher"""
    
    def __init__(self):
        self.kafka_connection = KafkaConnection()
        self.producer = self.kafka_connection.get_producer()
    
    def publish(self, topic: str, event: EventPayload, key: str = None) -> bool:
        """
        Publish an event to Kafka topic
        
        Args:
            topic: Kafka topic name
            event: Event payload
            key: Partition key (optional)
            
        Returns:
            bool: True if published successfully
        """
        try:
            message = json.dumps(event.to_dict())
            
            if key:
                key = key.encode('utf-8')
            
            self.producer.send(
                topic=topic,
                value=message.encode('utf-8'),
                key=key
            )
            
            # Flush to ensure message is sent
            self.producer.flush()
            
            logger.info(f"Event published to topic {topic}: {event.event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event to topic {topic}: {str(e)}")
            return False
    
    def close(self):
        """Close Kafka producer connection"""
        try:
            if self.producer:
                self.producer.close()
            if self.kafka_connection:
                self.kafka_connection.close()
        except Exception as e:
            logger.error(f"Error closing Kafka connection: {str(e)}")
