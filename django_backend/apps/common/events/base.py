from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class EventPayload:
    """Base class for event payloads"""
    
    def __init__(self, event_type: str, user_id: int, timestamp: datetime = None, 
                 data: Dict[str, Any] = None, metadata: Dict[str, Any] = None):
        self.event_type = event_type
        self.user_id = user_id
        self.timestamp = timestamp or datetime.utcnow()
        self.data = data or {}
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'metadata': self.metadata
        }

class EventPublisher(ABC):
    """Abstract base class for event publishers"""
    
    @abstractmethod
    def publish(self, topic: str, event: EventPayload, key: str = None) -> bool:
        """
        Publish an event to the specified topic
        
        Args:
            topic: Topic/queue name
            event: Event payload
            key: Partition key (optional)
            
        Returns:
            bool: True if published successfully
        """
        pass
    
    @abstractmethod
    def close(self):
        """Close publisher connection"""
        pass

class EventPublisherFactory:
    """Factory for creating event publishers"""
    
    _publisher = None
    
    @classmethod
    def get_publisher(cls) -> EventPublisher:
        """Get the configured event publisher"""
        if cls._publisher is None:
            from django.conf import settings
            
            publisher_type = getattr(settings, 'EVENT_PUBLISHER_TYPE', 'kafka')
            
            if publisher_type == 'kafka':
                from .kafka_publisher import KafkaEventPublisher
                cls._publisher = KafkaEventPublisher()
            elif publisher_type == 'rabbitmq':
                from .rabbitmq_publisher import RabbitMQEventPublisher
                cls._publisher = RabbitMQEventPublisher()
            elif publisher_type == 'redis':
                from .redis_publisher import RedisEventPublisher
                cls._publisher = RedisEventPublisher()
            elif publisher_type == 'memory':
                from .memory_publisher import MemoryEventPublisher
                cls._publisher = MemoryEventPublisher()
            else:
                raise ValueError(f"Unknown event publisher type: {publisher_type}")
        
        return cls._publisher
    
    @classmethod
    def reset_publisher(cls):
        """Reset publisher (useful for testing)"""
        if cls._publisher:
            cls._publisher.close()
            cls._publisher = None
