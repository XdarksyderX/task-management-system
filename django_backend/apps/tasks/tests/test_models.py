from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta

from apps.tasks.models import (
    Task,
    Tag,
    TaskTemplate,
    TaskAssignment,
    Comment,
    TaskHistory,
    TaskStatus,
    TaskPriority,
    TaskRole,
    TaskAction,
)
from apps.users.models import Team, User

User = get_user_model()


class TagModelTest(TestCase):
    """Test cases for Tag model"""

    def test_create_tag(self):
        """Test creating a basic tag"""
        tag = Tag.objects.create(name="Bug")

        self.assertEqual(tag.name, "Bug")
        self.assertEqual(str(tag), "Bug")

    def test_tag_name_unique(self):
        """Test that tag names must be unique"""
        Tag.objects.create(name="Bug")

        with self.assertRaises(IntegrityError):
            Tag.objects.create(name="Bug")

    def test_tag_ordering(self):
        """Test that tags are ordered by name"""
        Tag.objects.create(name="Zebra")
        Tag.objects.create(name="Alpha")
        Tag.objects.create(name="Beta")

        tags = list(Tag.objects.all())
        self.assertEqual([tag.name for tag in tags], ["Alpha", "Beta", "Zebra"])


class TaskModelTest(TestCase):
    """Test cases for Task model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.team = Team.objects.create(name="Test Team", description="A test team")

    def test_create_basic_task(self):
        """Test creating a basic task"""
        task = Task.objects.create(
            title="Test Task", description="A test task", created_by=self.user
        )

        self.assertEqual(task.title, "Test Task")
        self.assertEqual(task.description, "A test task")
        self.assertEqual(task.created_by, self.user)
        self.assertEqual(task.status, TaskStatus.TODO)
        self.assertEqual(task.priority, TaskPriority.MEDIUM)

    def test_task_string_representation(self):
        """Test task string representation"""
        task = Task.objects.create(title="Test Task", created_by=self.user)

        self.assertEqual(str(task), "Test Task")

    def test_task_with_team(self):
        """Test creating task with team assignment"""
        task = Task.objects.create(
            title="Team Task", created_by=self.user, assigned_team=self.team
        )

        self.assertEqual(task.assigned_team, self.team)

    def test_task_with_tags(self):
        """Test adding tags to a task"""
        tag1 = Tag.objects.create(name="Bug")
        tag2 = Tag.objects.create(name="Critical")

        task = Task.objects.create(title="Tagged Task", created_by=self.user)

        task.tags.add(tag1, tag2)

        self.assertEqual(task.tags.count(), 2)
        self.assertIn(tag1, task.tags.all())
        self.assertIn(tag2, task.tags.all())


class TaskAssignmentModelTest(TestCase):
    """Test cases for TaskAssignment model"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )

        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )

        self.task = Task.objects.create(title="Test Task", created_by=self.user1)

    def test_create_task_assignment(self):
        """Test creating a task assignment"""
        assignment = TaskAssignment.objects.create(
            task=self.task,
            user=self.user2,
            assigned_by=self.user1,
            role_in_task=TaskRole.COLLABORATOR,
        )

        self.assertEqual(assignment.task, self.task)
        self.assertEqual(assignment.user, self.user2)
        self.assertEqual(assignment.assigned_by, self.user1)
        self.assertEqual(assignment.role_in_task, TaskRole.COLLABORATOR)

    def test_unique_assignment_per_user_task(self):
        """Test that a user can only have one assignment per task"""
        TaskAssignment.objects.create(
            task=self.task, user=self.user2, assigned_by=self.user1
        )

        with self.assertRaises(IntegrityError):
            TaskAssignment.objects.create(
                task=self.task, user=self.user2, assigned_by=self.user1
            )


class CommentModelTest(TestCase):
    """Test cases for Comment model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.task = Task.objects.create(title="Test Task", created_by=self.user)

    def test_create_comment(self):
        """Test creating a comment"""
        comment = Comment.objects.create(
            task=self.task, author=self.user, body="This is a test comment"
        )

        self.assertEqual(comment.task, self.task)
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.body, "This is a test comment")

    def test_comment_string_representation(self):
        """Test comment string representation"""
        comment = Comment.objects.create(
            task=self.task, author=self.user, body="Test comment"
        )

        expected = f"Comment #{comment .pk } on {self .task .pk }"
        self.assertEqual(str(comment), expected)


class TaskHistoryModelTest(TestCase):
    """Test cases for TaskHistory model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.task = Task.objects.create(title="Test Task", created_by=self.user)

    def test_create_history_entry(self):
        """Test creating a history entry"""
        history = TaskHistory.objects.create(
            task=self.task,
            user=self.user,
            action=TaskAction.STATUS_CHANGED,
            metadata={"old_status": "todo", "new_status": "in_progress"},
        )

        self.assertEqual(history.task, self.task)
        self.assertEqual(history.user, self.user)
        self.assertEqual(history.action, TaskAction.STATUS_CHANGED)
        self.assertEqual(history.metadata["old_status"], "todo")

    def test_history_string_representation(self):
        """Test history string representation"""
        history = TaskHistory.objects.create(
            task=self.task, user=self.user, action=TaskAction.CREATED
        )

        expected = f"created on {self .task .pk }"
        self.assertEqual(str(history), expected)


class TaskTemplateModelTest(TestCase):
    """Test cases for TaskTemplate model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_create_task_template(self):
        """Test creating a task template"""
        template = TaskTemplate.objects.create(
            name="Bug Report Template",
            template={
                "title": "Bug: ",
                "description": "Steps to reproduce:\n1.\n2.\n3.",
                "priority": "high",
                "tags": ["bug"],
            },
            created_by=self.user,
        )

        self.assertEqual(template.name, "Bug Report Template")
        self.assertEqual(template.created_by, self.user)
        self.assertIn("title", template.template)

    def test_template_string_representation(self):
        """Test template string representation"""
        template = TaskTemplate.objects.create(
            name="Test Template", created_by=self.user
        )

        self.assertEqual(str(template), "Test Template")


class UserModelTest(TestCase):
    """Test cases for User model"""

    def test_create_user(self):
        """Test creating a user"""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            display_name="Test User",
        )

        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.display_name, "Test User")
        self.assertTrue(user.check_password("testpass123"))

    def test_user_string_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.assertEqual(str(user), "testuser")


class TeamModelTest(TestCase):
    """Test cases for Team model"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )

        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )

    def test_create_team(self):
        """Test creating a team"""
        team = Team.objects.create(
            name="Development Team", description="Backend development team"
        )

        self.assertEqual(team.name, "Development Team")
        self.assertEqual(team.description, "Backend development team")

    def test_team_string_representation(self):
        """Test team string representation"""
        team = Team.objects.create(name="Test Team")

        self.assertEqual(str(team), "Test Team")

    def test_team_members(self):
        """Test adding members to team"""
        team = Team.objects.create(name="Test Team")
        team.members.add(self.user1, self.user2)

        self.assertEqual(team.members.count(), 2)
        self.assertIn(self.user1, team.members.all())
        self.assertIn(self.user2, team.members.all())


class TaskChoicesTest(TestCase):
    """Test cases for choice fields"""

    def test_task_status_choices(self):
        """Test TaskStatus choices"""
        choices = dict(TaskStatus.choices)

        self.assertIn(TaskStatus.TODO, choices)
        self.assertIn(TaskStatus.IN_PROGRESS, choices)
        self.assertIn(TaskStatus.DONE, choices)
        self.assertEqual(choices[TaskStatus.TODO], "To Do")

    def test_task_priority_choices(self):
        """Test TaskPriority choices"""
        choices = dict(TaskPriority.choices)

        self.assertIn(TaskPriority.LOW, choices)
        self.assertIn(TaskPriority.HIGH, choices)
        self.assertEqual(choices[TaskPriority.MEDIUM], "Medium")

    def test_task_role_choices(self):
        """Test TaskRole choices"""
        choices = dict(TaskRole.choices)

        self.assertIn(TaskRole.OWNER, choices)
        self.assertIn(TaskRole.COLLABORATOR, choices)
        self.assertEqual(choices[TaskRole.OWNER], "Owner")

    def test_task_action_choices(self):
        """Test TaskAction choices"""
        choices = dict(TaskAction.choices)

        self.assertIn(TaskAction.CREATED, choices)
        self.assertIn(TaskAction.UPDATED, choices)
        self.assertIn(TaskAction.STATUS_CHANGED, choices)
        self.assertEqual(choices[TaskAction.CREATED], "Created")
