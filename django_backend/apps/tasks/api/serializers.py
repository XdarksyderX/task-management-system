from django.contrib.auth import get_user_model
from rest_framework import serializers
from apps.tasks.models import (
    Tag,
    Task,
    Comment,
    TaskAssignment,
    TaskHistory,
    TaskTemplate,
    TaskAction,
    TaskStatus,
)

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class TaskSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    assigned_to = serializers.PrimaryKeyRelatedField(
        many=True, queryset=User.objects.all(), required=False
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), required=False
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "due_date",
            "estimated_hours",
            "actual_hours",
            "created_by",
            "assigned_team",
            "assigned_to",
            "tags",
            "parent_task",
            "metadata",
            "is_archived",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "is_archived",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        request = self.context["request"]
        assignees = validated_data.pop("assigned_to", [])
        tags = validated_data.pop("tags", [])
        task = Task.objects.create(created_by=request.user, **validated_data)
        if assignees:
            TaskAssignment.objects.bulk_create(
                [
                    TaskAssignment(task=task, user=u, assigned_by=request.user)
                    for u in assignees
                ],
                ignore_conflicts=True,
            )
        if tags:
            task.tags.set(tags)
        TaskHistory.objects.create(
            task=task, user=request.user, action=TaskAction.CREATED
        )
        return task

    def update(self, instance, validated_data):
        request = self.context["request"]
        old_status = instance.status
        tags = validated_data.pop("tags", None)
        assignees = validated_data.pop("assigned_to", None)

        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        if tags is not None:
            instance.tags.set(tags)
        if assignees is not None:
            instance.assigned_to.set(assignees)

        if old_status != instance.status:
            TaskHistory.objects.create(
                task=instance,
                user=request.user,
                action=TaskAction.STATUS_CHANGED,
                metadata={"from": old_status, "to": instance.status},
            )
        else:
            TaskHistory.objects.create(
                task=instance, user=request.user, action=TaskAction.UPDATED
            )
        return instance


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "task", "author", "body", "created_at"]
        read_only_fields = ["id", "author", "created_at"]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["author"] = request.user
        obj = super().create(validated_data)
        TaskHistory.objects.create(
            task=obj.task,
            user=request.user,
            action=TaskAction.COMMENT_ADDED,
            metadata={"comment_id": obj.id},
        )
        return obj


class AssignmentRequestSerializer(serializers.Serializer):
    users = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False
    )
    role = serializers.ChoiceField(
        choices=[c[0] for c in TaskAssignment._meta.get_field("role_in_task").choices],
        required=False,
    )


class TaskHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskHistory
        fields = ["id", "action", "metadata", "created_at", "user"]


class TaskTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskTemplate
        fields = ["id", "name", "template", "created_by", "created_at"]
        read_only_fields = ["id", "created_by", "created_at"]

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)
