"""
WebSocket consumers for real-time task management functionality.

This module provides WebSocket consumers for:
- Task comments in real-time
- Task room for collaborative editing
- User notifications
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from ..models import Task, Comment

User = get_user_model()


class TaskCommentsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time task comments.
    
    Manages real-time communication for task-specific comment rooms.
    Users can join a task's comment room and receive instant updates
    when new comments are added.
    """
    
    async def connect(self):
        """Accept WebSocket connection and join task comment room."""
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.room_group_name = f'task_comments_{self.task_id}'
        
        # Check if user has permission to view this task
        if await self.has_task_permission():
            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            
            # Send initial comments
            await self.send_initial_comments()
        else:
            await self.close(code=4003)  # Forbidden
    
    async def disconnect(self, close_code):
        """Leave task comment room."""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            if message_type == 'comment.fetch':
                await self.send_initial_comments()
            elif message_type == 'comment.add':
                await self.handle_add_comment(text_data_json)
            elif message_type == 'comment.edit':
                await self.handle_edit_comment(text_data_json)
            elif message_type == 'comment.delete':
                await self.handle_delete_comment(text_data_json)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'comment.error',
                'message': 'Invalid JSON format'
            }))
    
    async def handle_add_comment(self, data):
        """Handle adding a new comment."""
        print("[DEBUG] handle_add_comment called with data:", data)
        content = data.get('content', '').strip()
        print("[DEBUG] Extracted content:", content)
        if not content:
            print("[DEBUG] Comment content is empty, sending error to client.")
            await self.send(text_data=json.dumps({
                'type': 'comment.error',
                'message': 'Comment content cannot be empty'
            }))
            return
        
        # Create comment in database
        comment = await self.create_comment(content)
        print("[DEBUG] Created comment:", comment)
        if comment:
            # Broadcast to room group
            serialized_comment = await self.serialize_comment(comment)
            print("[DEBUG] Broadcasting new comment to group:", self.room_group_name)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'comment_added',
                    'comment': serialized_comment
                }
            )
        else:
            print("[DEBUG] Failed to create comment.")
    
    async def handle_edit_comment(self, data):
        """Handle editing an existing comment."""
        comment_id = data.get('comment_id')
        content = data.get('content', '').strip()
        
        if not content:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Comment content cannot be empty'
            }))
            return
        
        comment = await self.update_comment(comment_id, content)
        if comment:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'comment_edited',
                    'comment': await self.serialize_comment(comment)
                }
            )
    
    async def handle_delete_comment(self, data):
        """Handle deleting a comment."""
        comment_id = data.get('comment_id')
        
        if await self.delete_comment(comment_id):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'comment_deleted',
                    'comment_id': comment_id
                }
            )
    
    # WebSocket event handlers
    async def comment_added(self, event):
        """Send comment added event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'comment.added',
            'comment': event['comment']
        }))
    
    async def comment_edited(self, event):
        """Send comment edited event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'comment.edited',
            'comment': event['comment']
        }))
    
    async def comment_deleted(self, event):
        """Send comment deleted event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'comment.deleted',
            'comment_id': event['comment_id']
        }))
    
    # Database operations
    @database_sync_to_async
    def has_task_permission(self):
        """Check if user has permission to view this task."""
        try:
            user = self.scope["user"]
            if not user.is_authenticated:
                return False
            
            task = Task.objects.get(id=self.task_id)
            # User can view if they're assigned, creator, or staff
            return (
                task.assigned_to.filter(id=user.id).exists() or
                task.created_by == user or
                user.is_staff
            )
        except ObjectDoesNotExist:
            return False
    
    @database_sync_to_async
    def create_comment(self, content):
        """Create a new comment in the database."""
        try:
            user = self.scope["user"]
            task = Task.objects.get(id=self.task_id)
            
            comment = Comment.objects.create(
                task=task,
                author=user,
                body=content
            )
            return comment
        except Exception as e:
            print("[ERROR] Exception in create_comment:", e)
            return None
    
    @database_sync_to_async
    def update_comment(self, comment_id, content):
        """Update an existing comment."""
        try:
            user = self.scope["user"]
            comment = Comment.objects.get(
                id=comment_id,
                task_id=self.task_id,
                author=user  # Only author can edit
            )
            comment.body = content
            comment.save()
            return comment
        except Exception:
            return None
    
    @database_sync_to_async
    def delete_comment(self, comment_id):
        """Delete a comment."""
        try:
            user = self.scope["user"]
            comment = Comment.objects.get(
                id=comment_id,
                task_id=self.task_id
            )
            # Only author or task creator can delete
            if comment.author == user or comment.task.created_by == user:
                comment.delete()
                return True
            return False
        except Exception:
            return False
    
    @database_sync_to_async
    def get_task_comments(self):
        """Get all comments for the task."""
        try:
            comments = Comment.objects.filter(
                task_id=self.task_id
            ).select_related('author').order_by('created_at')
            return list(comments)
        except Exception:
            return []
    
    @database_sync_to_async
    def serialize_comment(self, comment):
        """Serialize comment for JSON response."""
        return {
            'id': comment.id,
            'content': comment.body,
            'author_name': comment.author.get_full_name() or comment.author.username,
            'author': {
                'id': comment.author.id,
                'username': comment.author.username,
                'first_name': comment.author.first_name,
                'last_name': comment.author.last_name,
            },
            'created_at': comment.created_at.isoformat(),
            'updated_at': comment.updated_at.isoformat(),
        }
    
    async def send_initial_comments(self):
        """Send existing comments when user joins."""
        comments = await self.get_task_comments()
        serialized_comments = []
        
        for comment in comments:
            serialized_comments.append(await self.serialize_comment(comment))
        
        await self.send(text_data=json.dumps({
            'type': 'comment.history',
            'comments': serialized_comments
        }))


class TaskRoomConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for general task room functionality.
    
    Manages real-time updates for task changes, status updates,
    and user presence in task rooms.
    """
    
    async def connect(self):
        """Accept WebSocket connection and join task room."""
        self.task_id = self.scope['url_route']['kwargs']['task_id']
        self.room_group_name = f'task_room_{self.task_id}'
        
        if await self.has_task_permission():
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            
            # Notify others that user joined
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_joined',
                    'user': await self.get_user_info()
                }
            )
        else:
            await self.close(code=4003)
    
    async def disconnect(self, close_code):
        """Leave task room."""
        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user': await self.get_user_info()
            }
        )
        
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'task.update':
                await self.handle_task_update(text_data_json)
            elif message_type == 'user.typing':
                await self.handle_user_typing(text_data_json)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
    
    async def handle_task_update(self, data):
        """Handle task updates."""
        # Broadcast task update to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'task_updated',
                'update_data': data.get('data', {}),
                'user': await self.get_user_info()
            }
        )
    
    async def handle_user_typing(self, data):
        """Handle user typing indicators."""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_typing',
                'user': await self.get_user_info(),
                'is_typing': data.get('is_typing', False)
            }
        )
    
    # WebSocket event handlers
    async def user_joined(self, event):
        """Send user joined event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'user.joined',
            'user': event['user']
        }))
    
    async def user_left(self, event):
        """Send user left event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'user.left',
            'user': event['user']
        }))
    
    async def task_updated(self, event):
        """Send task updated event to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'task.updated',
            'data': event['update_data'],
            'user': event['user']
        }))
    
    async def user_typing(self, event):
        """Send user typing event to WebSocket."""
        # Don't send typing indicator back to the typer
        user = await self.get_user_info()
        if user['id'] != event['user']['id']:
            await self.send(text_data=json.dumps({
                'type': 'user.typing',
                'user': event['user'],
                'is_typing': event['is_typing']
            }))
    
    @database_sync_to_async
    def has_task_permission(self):
        """Check if user has permission to view this task."""
        try:
            user = self.scope["user"]
            if not user.is_authenticated:
                return False
            
            task = Task.objects.get(id=self.task_id)
            return (
                task.assigned_to.filter(id=user.id).exists() or
                task.created_by == user or
                user.is_staff
            )
        except ObjectDoesNotExist:
            return False
    
    @database_sync_to_async
    def get_user_info(self):
        """Get current user information."""
        user = self.scope["user"]
        return {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user notifications.
    
    Manages real-time notifications for individual users.
    """
    
    async def connect(self):
        """Accept WebSocket connection for user notifications."""
        if self.scope["user"].is_authenticated:
            self.user_id = self.scope["user"].id
            self.room_group_name = f'notifications_{self.user_id}'
            
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close(code=4001)  # Unauthorized
    
    async def disconnect(self, close_code):
        """Leave notification room."""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def notification(self, event):
        """Send notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))
