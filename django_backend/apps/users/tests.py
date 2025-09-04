"""
Main test runner for Users app

This module imports all test cases from the tests directory.
Run with: python manage.py test apps.users
"""

# Import all test cases from tests directory
from apps.users.tests.test_models import (
    CustomUserModelTest,
    TeamModelTest,
    UserManagerTest,
    UserModelMethodsTest,
    TeamModelMethodsTest,
    ModelRelationshipsTest,
)

from apps.users.tests.test_api import (
    AuthenticationAPITest,
    UserPermissionsTest,
    TeamIntegrationTest,
    UserModelAPITest,
    SimpleEndpointTest,
    UserModelValidationTest,
)

__all__ = [
    # Model tests
    'CustomUserModelTest',
    'TeamModelTest',
    'UserManagerTest',
    'UserModelMethodsTest',
    'TeamModelMethodsTest',
    'ModelRelationshipsTest',
    
    # API tests
    'AuthenticationAPITest',
    'UserPermissionsTest',
    'TeamIntegrationTest',
    'UserModelAPITest',
    'SimpleEndpointTest',
    'UserModelValidationTest',
]
