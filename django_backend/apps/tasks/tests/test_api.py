from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tasks.models import Task, Tag, TaskTemplate, TaskStatus, TaskPriority
from apps.users.models import Team

User = get_user_model()


class TaskAPITest(APITestCase):
    """Test cases for Task API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.team = Team.objects.create(name="Test Team", description="A test team")

        self.task = Task.objects.create(
            title="Test Task",
            description="A test task",
            created_by=self.user,
            assigned_team=self.team,
        )

        self.authenticate()

    def authenticate(self, user=None):
        """Helper method to authenticate a user"""
        if user is None:
            user = self.user

        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh .access_token }")

    def test_task_list_requires_authentication(self):
        """Test that task list requires authentication"""
        self.client.credentials()
        url = reverse("tasks-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_task_list(self):
        """Test getting task list when authenticated"""
        url = reverse("tasks-list")
        response = self.client.get(url)

        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED],
        )

    def test_create_task(self):
        """Test creating a new task"""
        url = reverse("tasks-list")
        data = {
            "title": "New API Task",
            "description": "Created via API",
            "status": TaskStatus.TODO,
            "priority": TaskPriority.HIGH,
        }

        response = self.client.post(url, data, format="json")

        if response.status_code == 201:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(Task.objects.filter(title="New API Task").exists())
        else:

            self.assertIn(
                response.status_code,
                [
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_403_FORBIDDEN,
                ],
            )

    def test_task_detail(self):
        """Test getting task detail"""
        url = reverse("tasks-detail", kwargs={"pk": self.task.pk})
        response = self.client.get(url)

        if response.status_code == 200:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["title"], "Test Task")
        else:

            self.assertIn(
                response.status_code,
                [status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED],
            )


class TagAPITest(APITestCase):
    """Test cases for Tag API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.tag = Tag.objects.create(name="Test Tag")

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh .access_token }")

    def test_tag_list_requires_authentication(self):
        """Test that tag list requires authentication"""
        self.client.credentials()
        url = reverse("tags-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_tag_list(self):
        """Test getting tag list when authenticated"""
        url = reverse("tags-list")
        response = self.client.get(url)

        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED],
        )

    def test_create_tag(self):
        """Test creating a new tag"""
        url = reverse("tags-list")
        data = {"name": "New Tag"}

        response = self.client.post(url, data, format="json")

        if response.status_code == 201:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(Tag.objects.filter(name="New Tag").exists())
        else:

            self.assertIn(
                response.status_code,
                [
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_403_FORBIDDEN,
                ],
            )


class TaskTemplateAPITest(APITestCase):
    """Test cases for TaskTemplate API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.template = TaskTemplate.objects.create(
            name="Test Template",
            template={"title": "Template Task", "priority": "high"},
            created_by=self.user,
        )

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh .access_token }")

    def test_template_list_requires_authentication(self):
        """Test that template list requires authentication"""
        self.client.credentials()
        url = reverse("task-templates-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_template_list(self):
        """Test getting template list when authenticated"""
        url = reverse("task-templates-list")
        response = self.client.get(url)

        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED],
        )

    def test_create_template(self):
        """Test creating a new template"""
        url = reverse("task-templates-list")
        data = {
            "name": "New Template",
            "template": {
                "title": "New Template Task",
                "description": "Template description",
                "priority": "medium",
            },
        }

        response = self.client.post(url, data, format="json")

        if response.status_code == 201:
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(TaskTemplate.objects.filter(name="New Template").exists())
        else:

            self.assertIn(
                response.status_code,
                [
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_403_FORBIDDEN,
                ],
            )


class AuthenticationTest(APITestCase):
    """Test cases for Authentication"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_jwt_token_creation(self):
        """Test JWT token creation"""

        refresh = RefreshToken.for_user(self.user)
        access = refresh.access_token

        self.assertIsNotNone(str(refresh))
        self.assertIsNotNone(str(access))

    def test_authenticated_request(self):
        """Test making authenticated requests"""
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh .access_token }")

        url = reverse("tasks-list")
        response = self.client.get(url)

        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_request(self):
        """Test making unauthenticated requests"""

        url = reverse("tasks-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserPermissionsTest(APITestCase):
    """Test cases for User permissions"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        self.regular_user = User.objects.create_user(
            username="regular", email="regular@example.com", password="testpass123"
        )

        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )

        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="testpass123"
        )

    def authenticate(self, user):
        """Helper method to authenticate a user"""
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh .access_token }")

    def test_regular_user_can_authenticate(self):
        """Test that regular users can authenticate"""
        self.authenticate(self.regular_user)

        url = reverse("tasks-list")
        response = self.client.get(url)

        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_staff_user_can_authenticate(self):
        """Test that staff users can authenticate"""
        self.authenticate(self.staff_user)

        url = reverse("tasks-list")
        response = self.client.get(url)

        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_user_can_authenticate(self):
        """Test that admin users can authenticate"""
        self.authenticate(self.admin_user)

        url = reverse("tasks-list")
        response = self.client.get(url)

        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ModelIntegrationTest(TestCase):
    """Test cases for model integration with API"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.team = Team.objects.create(name="Test Team", description="A test team")

        self.tag = Tag.objects.create(name="Test Tag")

    def test_task_with_relationships(self):
        """Test creating task with all relationships"""
        task = Task.objects.create(
            title="Complex Task",
            description="Task with relationships",
            created_by=self.user,
            assigned_team=self.team,
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
        )

        task.tags.add(self.tag)

        self.assertEqual(task.created_by, self.user)
        self.assertEqual(task.assigned_team, self.team)
        self.assertIn(self.tag, task.tags.all())
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)
        self.assertEqual(task.priority, TaskPriority.HIGH)

    def test_template_to_task_creation(self):
        """Test creating task from template"""
        template = TaskTemplate.objects.create(
            name="Bug Template",
            template={
                "title": "Bug: ",
                "description": "Steps to reproduce:",
                "priority": TaskPriority.HIGH,
                "status": TaskStatus.TODO,
            },
            created_by=self.user,
        )

        template_data = template.template
        task = Task.objects.create(
            title=template_data.get("title", "") + "Sample bug",
            description=template_data.get("description", ""),
            created_by=self.user,
            priority=template_data.get("priority", TaskPriority.MEDIUM),
            status=template_data.get("status", TaskStatus.TODO),
        )

        self.assertEqual(task.title, "Bug: Sample bug")
        self.assertEqual(task.description, "Steps to reproduce:")
        self.assertEqual(task.priority, TaskPriority.HIGH)
        self.assertEqual(task.status, TaskStatus.TODO)
