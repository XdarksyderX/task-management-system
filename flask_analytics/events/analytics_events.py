import logging
from datetime import datetime
from typing import Dict, Any, Optional
from .base import EventPayload, EventPublisherFactory

logger = logging.getLogger(__name__)


class AnalyticsEventService:
    """Service for publishing analytics events"""

    TOPIC = "analytics-events"

    def __init__(self):
        self.publisher = EventPublisherFactory.get_publisher()

    def publish_dashboard_viewed(
        self, user_id: int, metadata: Dict[str, Any] = None
    ) -> bool:
        """Publish dashboard viewed event"""
        event = EventPayload(
            event_type="dashboard_viewed", user_id=user_id, metadata=metadata or {}
        )
        return self._publish_event(event, key=f"user_{user_id }")

    def publish_report_generated(
        self,
        user_id: int,
        report_type: str,
        job_id: str,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Publish report generation event"""
        event = EventPayload(
            event_type="report_generated",
            user_id=user_id,
            data={"report_type": report_type, "job_id": job_id},
            metadata=metadata or {},
        )
        return self._publish_event(event, key=f"user_{user_id }")

    def publish_report_downloaded(
        self, user_id: int, report_id: str, metadata: Dict[str, Any] = None
    ) -> bool:
        """Publish report download event"""
        event = EventPayload(
            event_type="report_downloaded",
            user_id=user_id,
            data={"report_id": report_id},
            metadata=metadata or {},
        )
        return self._publish_event(event, key=f"user_{user_id }")

    def publish_analytics_query(
        self,
        user_id: int,
        endpoint: str,
        query_type: str,
        execution_time_ms: float,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Publish analytics query event"""
        event = EventPayload(
            event_type="analytics_query",
            user_id=user_id,
            data={
                "endpoint": endpoint,
                "query_type": query_type,
                "execution_time_ms": execution_time_ms,
            },
            metadata=metadata or {},
        )
        return self._publish_event(event, key=f"user_{user_id }")

    def publish_user_stats_accessed(
        self,
        requesting_user_id: int,
        target_user_id: int,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Publish user stats access event"""
        event = EventPayload(
            event_type="user_stats_accessed",
            user_id=requesting_user_id,
            data={"target_user_id": target_user_id},
            metadata=metadata or {},
        )
        return self._publish_event(event, key=f"user_{requesting_user_id }")

    def publish_team_performance_accessed(
        self, user_id: int, team_id: int, metadata: Dict[str, Any] = None
    ) -> bool:
        """Publish team performance access event"""
        event = EventPayload(
            event_type="team_performance_accessed",
            user_id=user_id,
            data={"team_id": team_id},
            metadata=metadata or {},
        )
        return self._publish_event(event, key=f"user_{user_id }")

    def publish_task_distribution_viewed(
        self, user_id: int, metadata: Dict[str, Any] = None
    ) -> bool:
        """Publish task distribution viewed event"""
        event = EventPayload(
            event_type="task_distribution_viewed",
            user_id=user_id,
            metadata=metadata or {},
        )
        return self._publish_event(event, key=f"user_{user_id }")

    def publish_error_occurred(
        self,
        user_id: int = None,
        error_type: str = None,
        endpoint: str = None,
        error_message: str = None,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Publish error event"""
        event = EventPayload(
            event_type="error_occurred",
            user_id=user_id,
            data={
                "error_type": error_type,
                "endpoint": endpoint,
                "error_message": error_message,
            },
            metadata=metadata or {},
        )
        key = f"user_{user_id }" if user_id else "system"
        return self._publish_event(event, key=key)

    def _publish_event(self, event: EventPayload, key: str = None) -> bool:
        """Internal method to publish events"""
        try:
            success = self.publisher.publish(self.TOPIC, event, key)
            if success:
                logger.info(
                    f"Published event: {event .event_type } for user: {event .user_id }"
                )
            else:
                logger.warning(
                    f"Failed to publish event: {event .event_type } for user: {event .user_id }"
                )
            return success
        except Exception as e:
            logger.error(f"Error publishing event {event .event_type }: {str (e )}")
            return False

    def close(self):
        """Close the event publisher"""
        try:
            self.publisher.close()
        except Exception as e:
            logger.error(f"Error closing event publisher: {str (e )}")


analytics_events = AnalyticsEventService()
