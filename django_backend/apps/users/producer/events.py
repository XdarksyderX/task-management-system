import logging
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional
from django.conf import settings

from apps.common.events import EventPayload
from apps.common.events.base import EventPublisherFactory
from apps.common.kafka.config import USER_ACTIVITIES_TOPIC

logger = logging.getLogger(__name__)

class UserEventType(Enum):
    """User event types"""
    # Authentication
    USER_REGISTERED = "user_registered"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_LOGIN_FAILED = "user_login_failed"
    
    # Profile
    USER_PROFILE_UPDATED = "user_profile_updated"
    USER_PASSWORD_CHANGED = "user_password_changed"
    USER_EMAIL_CHANGED = "user_email_changed"
    
    # Teams
    TEAM_CREATED = "team_created"
    TEAM_UPDATED = "team_updated"
    TEAM_DELETED = "team_deleted"
    TEAM_MEMBER_ADDED = "team_member_added"
    TEAM_MEMBER_REMOVED = "team_member_removed"
    TEAM_MEMBER_ROLE_CHANGED = "team_member_role_changed"
    TEAM_MEMBER_LEFT = "team_member_left"

def publish_user_event(
    event_type: UserEventType,
    user_id: int,
    data: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Publish user activity event using the abstraction layer
    
    Args:
        event_type: Type of user event
        user_id: ID of the user performing the action
        data: Event-specific data
        metadata: Additional metadata (optional)
        
    Returns:
        bool: True if event was published successfully
    """
    
    # If we're in testing mode, use memory publisher
    if getattr(settings, 'TESTING', False):
        logger.debug(f"Testing mode. Publishing to memory: {event_type.value}")
        # In testing, we might want to use memory publisher
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
        
        # Create message key (user_id for partitioning)
        message_key = str(user_id)
        
        # Publish event
        success = publisher.publish(
            topic=USER_ACTIVITIES_TOPIC,
            event=payload,
            key=message_key
        )
        
        if success:
            logger.info(f"User event published successfully: {event_type.value}")
        else:
            logger.error(f"Failed to publish user event: {event_type.value}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error publishing user event {event_type.value}: {str(e)}")
        return False

# Convenience functions for specific events

def publish_user_registered(user_id: int, username: str, email: str, **extra_data):
    """Publishes user registration event"""
    data = {
        'username': username,
        'email': email,
        **extra_data
    }
    return publish_user_event(UserEventType.USER_REGISTERED, user_id, data)

def publish_user_login(user_id: int, username: str, ip_address: str = None, user_agent: str = None):
    """Publishes user login event"""
    data = {
        'username': username,
        'ip_address': ip_address,
        'user_agent': user_agent
    }
    return publish_user_event(UserEventType.USER_LOGIN, user_id, data)

def publish_user_logout(user_id: int, username: str):
    """Publishes user logout event"""
    data = {
        'username': username
    }
    return publish_user_event(UserEventType.USER_LOGOUT, user_id, data)

def publish_user_login_failed(username: str, ip_address: str = None, reason: str = None):
    """Publishes login failure event"""
    data = {
        'username': username,
        'ip_address': ip_address,
        'reason': reason or 'Invalid credentials'
    }
    # For failed login use user_id = 0 since there's no authenticated user
    return publish_user_event(UserEventType.USER_LOGIN_FAILED, 0, data)

def publish_team_created(user_id: int, team_id: int, team_name: str, team_description: str = None):
    """Publishes team creation event"""
    data = {
        'team_id': team_id,
        'team_name': team_name,
        'team_description': team_description,
        'action': 'create'
    }
    return publish_user_event(UserEventType.TEAM_CREATED, user_id, data)

def publish_team_updated(user_id: int, team_id: int, team_name: str, changes: Dict[str, Any]):
    """Publishes team update event"""
    data = {
        'team_id': team_id,
        'team_name': team_name,
        'changes': changes,
        'action': 'update'
    }
    return publish_user_event(UserEventType.TEAM_UPDATED, user_id, data)

def publish_team_deleted(user_id: int, team_id: int, team_name: str):
    """Publishes team deletion event"""
    data = {
        'team_id': team_id,
        'team_name': team_name,
        'action': 'delete'
    }
    return publish_user_event(UserEventType.TEAM_DELETED, user_id, data)

def publish_team_member_added(admin_user_id: int, team_id: int, team_name: str, new_member_id: int, new_member_username: str):
    """Publishes team member addition event"""
    data = {
        'team_id': team_id,
        'team_name': team_name,
        'new_member_id': new_member_id,
        'new_member_username': new_member_username,
        'action': 'add_member'
    }
    return publish_user_event(UserEventType.TEAM_MEMBER_ADDED, admin_user_id, data)

def publish_team_member_removed(admin_user_id: int, team_id: int, team_name: str, removed_member_id: int, removed_member_username: str):
    """Publishes team member removal event"""
    data = {
        'team_id': team_id,
        'team_name': team_name,
        'removed_member_id': removed_member_id,
        'removed_member_username': removed_member_username,
        'action': 'remove_member'
    }
    return publish_user_event(UserEventType.TEAM_MEMBER_REMOVED, admin_user_id, data)

def publish_team_member_left(user_id: int, team_id: int, team_name: str):
    """Publishes user leaving team event"""
    data = {
        'team_id': team_id,
        'team_name': team_name,
        'action': 'leave_team'
    }
    return publish_user_event(UserEventType.TEAM_MEMBER_LEFT, user_id, data)
