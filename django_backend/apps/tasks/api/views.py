from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from apps.tasks.models import Tag, Task, Comment, TaskAssignment, TaskHistory, TaskTemplate, TaskAction
from apps.tasks.celery_tasks import send_task_notification
from .serializers import (
    TagSerializer, TaskSerializer, CommentSerializer,
    AssignmentRequestSerializer, TaskHistorySerializer,
    TaskTemplateSerializer
)
from .permissions import IsOwnerOrAssigneeOrAdmin

User = get_user_model()


def scoped_tasks(request):
    qs = Task.objects.select_related("created_by","parent_task","assigned_team") \
                     .prefetch_related("assigned_to","tags")
    if request.user.is_staff:
        return qs
    return qs.filter(Q(created_by=request.user) | Q(assigned_to=request.user)).distinct()


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by("name")
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAssigneeOrAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status","priority","is_archived","tags","assigned_to","assigned_team"]
    search_fields = ["title","description"]
    ordering_fields = ["due_date","priority","created_at","updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return scoped_tasks(self.request)

    def perform_create(self, serializer):
        task = serializer.save()
        transaction.on_commit(lambda: send_task_notification.delay(task.id, "created"))

    def perform_update(self, serializer):
        old_status = self.get_object().status
        task = serializer.save()

        if old_status != task.status:
            TaskHistory.objects.create(
                task=task, 
                user=self.request.user, 
                action=TaskAction.STATUS_CHANGED,
                metadata={"from": old_status, "to": task.status}
            )
            transaction.on_commit(lambda: send_task_notification.delay(task.id, "status_changed"))
        else:
            TaskHistory.objects.create(task=task, user=self.request.user, action=TaskAction.UPDATED)
            transaction.on_commit(lambda: send_task_notification.delay(task.id, "updated"))

    def perform_destroy(self, instance):
        instance.is_archived = True
        instance.save(update_fields=["is_archived"])
        TaskHistory.objects.create(task=instance, user=self.request.user, action=TaskAction.ARCHIVED)
        # Send notification when task is archived
        transaction.on_commit(lambda: send_task_notification.delay(instance.id, "updated"))

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        task = self.get_object()
        ser = AssignmentRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ids = ser.validated_data["users"]
        role = ser.validated_data.get("role")

        users = list(User.objects.filter(id__in=ids))
        newly_assigned = []
        
        for u in users:
            obj, created = TaskAssignment.objects.get_or_create(
                task=task, user=u, defaults={"assigned_by": request.user}
            )
            if created:
                newly_assigned.append(u.id)
            if role:
                obj.role_in_task = role
                if created:
                    obj.assigned_by = request.user
                obj.save(update_fields=["role_in_task","assigned_by"])

        TaskHistory.objects.create(
            task=task, user=request.user, action=TaskAction.UPDATED,
            metadata={"assigned_users": ids, **({"role": role} if role else {})}
        )
        if newly_assigned:
            transaction.on_commit(lambda: send_task_notification.delay(task.id, "assigned"))
        
        return Response(TaskSerializer(task, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def comments(self, request, pk=None):
        task = self.get_object()
        ser = CommentSerializer(
            data={"task": task.id, **request.data},
            context={"request": request}
        )
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        TaskHistory.objects.create(
            task=task, 
            user=request.user, 
            action=TaskAction.UPDATED,
            metadata={"comment_added": True, "comment_id": obj.id}
        )
        transaction.on_commit(lambda: send_task_notification.delay(task.id, "comment_added"))
        
        return Response(CommentSerializer(obj).data, status=status.HTTP_201_CREATED)

    @comments.mapping.get
    def list_comments(self, request, pk=None):
        task = self.get_object()
        qs = task.comments.select_related("author").order_by("-created_at")
        return Response(CommentSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        task = self.get_object()
        qs = task.history.select_related("user").order_by("-created_at")
        return Response(TaskHistorySerializer(qs, many=True).data)


class TaskTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = TaskTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = TaskTemplate.objects.all().order_by("name")
        return qs if self.request.user.is_staff else qs.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
