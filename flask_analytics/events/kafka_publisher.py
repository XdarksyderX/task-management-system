import json
import logging
import os
from .base import EventPublisher, EventPayload

logger = logging.getLogger(__name__)

class KafkaEventPublisher(EventPublisher):
    """Kafka implementation of EventPublisher"""
    
    def __init__(self):
        self.producer = None
        self._initialize_kafka()
    
    def _initialize_kafka(self):
        """Initialize Kafka producer"""
        try:
            from kafka import KafkaProducer
            
            # Use same configuration pattern as Django backend
            bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092').split(',')
            
            kafka_config = {
                'bootstrap_servers': bootstrap_servers,
                'value_serializer': lambda x: json.dumps(x).encode('utf-8'),  # Same as Django
                'key_serializer': lambda x: x.encode('utf-8') if x else None,
                'retries': 3,
                'retry_backoff_ms': 300,  # Same as Django
                'request_timeout_ms': 30000,
                'acks': 'all'  # Ensures message is written to all replicas
            }
            
            self.producer = KafkaProducer(**kafka_config)
            logger.info("Kafka producer initialized successfully")
            
        except ImportError:
            logger.error("kafka-python not installed. Install with: pip install kafka-python")
            self.producer = None
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {str(e)}")
            self.producer = None
            # Don't raise here - let publish method handle gracefully
            # This allows the application to continue running even if Kafka is down
    
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
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return False
            
        try:
            # Convert event to dict (same as Django implementation)
            event_data = event.to_dict()
            
            # Send message (serializers will handle encoding)
            self.producer.send(
                topic=topic,
                value=event_data,  # value_serializer will handle JSON conversion + encoding
                key=key  # key_serializer will handle encoding
            )
            
            # Flush to ensure message is sent (same as Django)
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
                logger.info("Kafka producer closed")
        except Exception as e:
            logger.error(f"Error closing Kafka connection: {str(e)}")
