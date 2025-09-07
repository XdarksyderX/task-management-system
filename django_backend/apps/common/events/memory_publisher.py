import logging 
from typing import Dict ,List 
from .base import EventPublisher ,EventPayload 

logger =logging .getLogger (__name__ )

class MemoryEventPublisher (EventPublisher ):
    """In-memory implementation of EventPublisher for testing"""

    def __init__ (self ):
        self .events :Dict [str ,List [Dict ]]={}

    def publish (self ,topic :str ,event :EventPayload ,key :str =None )->bool :
        """
        Store event in memory
        
        Args:
            topic: Topic name
            event: Event payload
            key: Key (stored in metadata)
            
        Returns:
            bool: Always True
        """
        try :
            if topic not in self .events :
                self .events [topic ]=[]

            event_data =event .to_dict ()
            if key :
                event_data ['key']=key 

            self .events [topic ].append (event_data )

            logger .info (f"Event stored in memory for topic {topic }: {event .event_type }")
            return True 

        except Exception as e :
            logger .error (f"Failed to store event in memory for topic {topic }: {str (e )}")
            return False 

    def get_events (self ,topic :str )->List [Dict ]:
        """Get all events for a topic (testing utility)"""
        return self .events .get (topic ,[])

    def clear_events (self ,topic :str =None ):
        """Clear events for a topic or all topics (testing utility)"""
        if topic :
            self .events .pop (topic ,None )
        else :
            self .events .clear ()

    def close (self ):
        """No connection to close for memory publisher"""
        pass 
