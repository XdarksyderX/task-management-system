import logging
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional
from django.conf import settings

from apps.common.events import EventPayload
from apps.common.events.base import EventPublisherFactory
from apps.common.kafka.config import TASK_EVENTS_TOPIC

logger = logging.getLogger(__name__)

class TaskEventType(Enum):
    """Task event types"""
    # Task lifecycle
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_COMPLETED = "task_completed"
    TASK_REOPENED = "task_reopened"
    TASK_ARCHIVED = "task_archived"
    TASK_RESTORED = "task_restored"
    
    # Task status changes
    TASK_STATUS_CHANGED = "task_status_changed"
    TASK_PRIORITY_CHANGED = "task_priority_changed"
    TASK_ASSIGNED = "task_assigned"
    TASK_UNASSIGNED = "task_unassigned"
    TASK_DUE_DATE_CHANGED = "task_due_date_changed"
    TASK_TAGS_UPDATED = "task_tags_updated"
    
    # Task comments
    TASK_COMMENT_ADDED = "task_comment_added"
    TASK_COMMENT_UPDATED = "task_comment_updated"
    TASK_COMMENT_DELETED = "task_comment_deleted"
    
    # Task templates
    TASK_TEMPLATE_CREATED = "task_template_created"
    TASK_TEMPLATE_USED = "task_template_used"

def publish_task_event(
    event_type: TaskEventType,
    user_id: int,
    data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Publish task event using the abstraction layer
    
    Args:
        event_type: Type of task event
        user_id: ID of the user performing the action
        data: Event-specific data (should include task-related info)
        metadata: Additional metadata (optional)
        
    Returns:
        bool: True if event was published successfully
    """
    
    # If we're in testing mode, use memory publisher
    if getattr(settings, 'TESTING', False):
        logger.debug(f"Testing mode. Publishing to memory: {event_type.value}")
        settings.EVENT_PUBLISHER_TYPE = 'memory'
    
    try:
        # Create event payload
        payload = EventPayload(
            event_type=event_type.value,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            data=data,
            metadata=metadata
        )
        
        # Get publisher through factory
        publisher = EventPublisherFactory.get_publisher()
        
        # Create message key (task_id for partitioning if available, otherwise user_id)
        message_key = str(data.get('task_id', user_id))
        
        # Publish event
        success = publisher.publish(
            topic=TASK_EVENTS_TOPIC,
            event=payload,
            key=message_key
        )
        
        if success:
            logger.info(f"Task event published successfully: {event_type.value}")
        else:
            logger.error(f"Failed to publish task event: {event_type.value}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error publishing task event {event_type.value}: {str(e)}")
        return False

# Convenience functions for specific events

def publish_task_created(user_id: int, task_id: int, title: str, description: str = None, 
                        priority: str = None, assigned_to_id: int = None, team_id: int = None):
    """Publishes task creation event"""
    data = {
        'task_id': task_id,
        'title': title,
        'description': description,
        'priority': priority,
        'assigned_to_id': assigned_to_id,
        'team_id': team_id,
        'action': 'create'
    }
    return publish_task_event(TaskEventType.TASK_CREATED, user_id, data)

def publish_task_updated(user_id: int, task_id: int, title: str, changes: Dict[str, Any]):
    """Publishes task update event"""
    data = {
        'task_id': task_id,
        'title': title,
        'changes': changes,
        'action': 'update'
    }
    return publish_task_event(TaskEventType.TASK_UPDATED, user_id, data)

def publish_task_deleted(user_id: int, task_id: int, title: str):
    """Publishes task deletion event"""
    data = {
        'task_id': task_id,
        'title': title,
        'action': 'delete'
    }
    return publish_task_event(TaskEventType.TASK_DELETED, user_id, data)

def publish_task_status_changed(user_id: int, task_id: int, title: str, 
                               old_status: str, new_status: str):
    """Publishes task status change event"""
    data = {
        'task_id': task_id,
        'title': title,
        'old_status': old_status,
        'new_status': new_status,
        'action': 'status_change'
    }
    return publish_task_event(TaskEventType.TASK_STATUS_CHANGED, user_id, data)

def publish_task_completed(user_id: int, task_id: int, title: str):
    """Publishes task completion event"""
    data = {
        'task_id': task_id,
        'title': title,
        'action': 'complete'
    }
    return publish_task_event(TaskEventType.TASK_COMPLETED, user_id, data)

def publish_task_assigned(user_id: int, task_id: int, title: str, 
                         assigned_to_id: int, assigned_to_username: str):
    """Publishes task assignment event"""
    data = {
        'task_id': task_id,
        'title': title,
        'assigned_to_id': assigned_to_id,
        'assigned_to_username': assigned_to_username,
        'action': 'assign'
    }
    return publish_task_event(TaskEventType.TASK_ASSIGNED, user_id, data)

def publish_task_priority_changed(user_id: int, task_id: int, title: str,
                                 old_priority: str, new_priority: str):
    """Publishes task priority change event"""
    data = {
        'task_id': task_id,
        'title': title,
        'old_priority': old_priority,
        'new_priority': new_priority,
        'action': 'priority_change'
    }
    return publish_task_event(TaskEventType.TASK_PRIORITY_CHANGED, user_id, data)

def publish_task_due_date_set(user_id: int, task_id: int, title: str, due_date: str):
    """Publishes task due date set event"""
    data = {
        'task_id': task_id,
        'title': title,
        'due_date': due_date,
        'action': 'set_due_date'
    }
    return publish_task_event(TaskEventType.TASK_DUE_DATE_SET, user_id, data)

def publish_task_archived(user_id: int, task_id: int, title: str):
    """Publishes task archival event"""
    data = {
        'task_id': task_id,
        'title': title,
        'action': 'archive'
    }
    return publish_task_event(TaskEventType.TASK_ARCHIVED, user_id, data)

# Tag events
def publish_tag_created(user_id: int, tag_id: int, tag_name: str, color: str = None):
    """Publishes tag creation event"""
    data = {
        'tag_id': tag_id,
        'tag_name': tag_name,
        'color': color,
        'action': 'create'
    }
    return publish_task_event(TaskEventType.TAG_CREATED, user_id, data)

def publish_tag_updated(user_id: int, tag_id: int, tag_name: str, changes: Dict[str, Any]):
    """Publishes tag update event"""
    data = {
        'tag_id': tag_id,
        'tag_name': tag_name,
        'changes': changes,
        'action': 'update'
    }
    return publish_task_event(TaskEventType.TAG_UPDATED, user_id, data)

def publish_tag_deleted(user_id: int, tag_id: int, tag_name: str):
    """Publishes tag deletion event"""
    data = {
        'tag_id': tag_id,
        'tag_name': tag_name,
        'action': 'delete'
    }
    return publish_task_event(TaskEventType.TAG_DELETED, user_id, data)

def publish_task_tag_added(user_id: int, task_id: int, task_title: str, 
                          tag_id: int, tag_name: str):
    """Publishes task tag addition event"""
    data = {
        'task_id': task_id,
        'task_title': task_title,
        'tag_id': tag_id,
        'tag_name': tag_name,
        'action': 'add_tag'
    }
    return publish_task_event(TaskEventType.TASK_TAG_ADDED, user_id, data)

def publish_task_tag_removed(user_id: int, task_id: int, task_title: str,
                            tag_id: int, tag_name: str):
    """Publishes task tag removal event"""
    data = {
        'task_id': task_id,
        'task_title': task_title,
        'tag_id': tag_id,
        'tag_name': tag_name,
        'action': 'remove_tag'
    }
    return publish_task_event(TaskEventType.TASK_TAG_REMOVED, user_id, data)

# Template events
def publish_template_created(user_id: int, template_id: int, template_title: str,
                           description: str = None, priority: str = None):
    """Publishes template creation event"""
    data = {
        'template_id': template_id,
        'template_title': template_title,
        'description': description,
        'priority': priority,
        'action': 'create'
    }
    return publish_task_event(TaskEventType.TEMPLATE_CREATED, user_id, data)

def publish_template_updated(user_id: int, template_id: int, template_title: str,
                           changes: Dict[str, Any]):
    """Publishes template update event"""
    data = {
        'template_id': template_id,
        'template_title': template_title,
        'changes': changes,
        'action': 'update'
    }
    return publish_task_event(TaskEventType.TEMPLATE_UPDATED, user_id, data)

def publish_template_deleted(user_id: int, template_id: int, template_title: str):
    """Publishes template deletion event"""
    data = {
        'template_id': template_id,
        'template_title': template_title,
        'action': 'delete'
    }
    return publish_task_event(TaskEventType.TEMPLATE_DELETED, user_id, data)

def publish_task_created_from_template(user_id: int, task_id: int, task_title: str,
                                     template_id: int, template_title: str):
    """Publishes task creation from template event"""
    data = {
        'task_id': task_id,
        'task_title': task_title,
        'template_id': template_id,
        'template_title': template_title,
        'action': 'create_from_template'
    }
    return publish_task_event(TaskEventType.TASK_CREATED_FROM_TEMPLATE, user_id, data)
