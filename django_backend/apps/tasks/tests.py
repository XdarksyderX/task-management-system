"""
Main test runner for Tasks app

This module imports all test cases from the tests directory.
Run with: python manage.py test apps.tasks
"""

# Import all test cases from tests directory
from apps.tasks.tests.test_models import (
    TagModelTest,
    TaskModelTest,
    TaskAssignmentModelTest,
    CommentModelTest,
    TaskHistoryModelTest,
    TaskTemplateModelTest,
    UserModelTest,
    TeamModelTest,
    TaskChoicesTest,
)

from apps.tasks.tests.test_api import (
    TaskAPITest,
    TagAPITest,
    TaskTemplateAPITest,
    AuthenticationTest,
    UserPermissionsTest,
    ModelIntegrationTest,
)

__all__ = [
    # Model tests
    'TagModelTest',
    'TaskModelTest', 
    'TaskAssignmentModelTest',
    'CommentModelTest',
    'TaskHistoryModelTest',
    'TaskTemplateModelTest',
    'UserModelTest',
    'TeamModelTest',
    'TaskChoicesTest',
    
    # API tests
    'TaskAPITest',
    'TagAPITest',
    'TaskTemplateAPITest',
    'AuthenticationTest',
    'UserPermissionsTest',
    'ModelIntegrationTest',
]
