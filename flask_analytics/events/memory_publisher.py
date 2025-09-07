import json
import logging
from collections import defaultdict
from .base import EventPublisher, EventPayload

logger = logging.getLogger(__name__)

class MemoryEventPublisher(EventPublisher):
    """In-memory implementation of EventPublisher (for testing/development)"""
    
    def __init__(self):
        self.events = defaultdict(list)
        logger.info("Memory event publisher initialized")
    
    def publish(self, topic: str, event: EventPayload, key: str = None) -> bool:
        """
        Store an event in memory
        
        Args:
            topic: Topic name
            event: Event payload
            key: Key for the message (optional)
            
        Returns:
            bool: True always (unless error)
        """
        try:
            event_data = event.to_dict()
            if key:
                event_data['key'] = key
                
            self.events[topic].append(event_data)
            
            logger.info(f"Event stored in memory topic {topic}: {event.event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store event in memory topic {topic}: {str(e)}")
            return False
    
    def get_events(self, topic: str = None):
        """Get stored events (for testing)"""
        if topic:
            return self.events.get(topic, [])
        return dict(self.events)
    
    def clear_events(self, topic: str = None):
        """Clear stored events (for testing)"""
        if topic:
            self.events[topic] = []
        else:
            self.events.clear()
    
    def close(self):
        """Clear all events"""
        self.events.clear()
        logger.info("Memory event publisher closed")
