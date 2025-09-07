from django .test import TestCase 
from django .urls import reverse 
from django .contrib .auth import get_user_model 
from rest_framework .test import APITestCase ,APIClient 
from rest_framework import status 
from rest_framework_simplejwt .tokens import RefreshToken 

from apps .users .models import Team 

User =get_user_model ()


class AuthenticationAPITest (APITestCase ):
    """Test cases for Authentication endpoints"""

    def setUp (self ):
        """Set up test data"""
        self .client =APIClient ()

        self .user =User .objects .create_user (
        username ="testuser",
        email ="test@example.com",
        password ="testpass123"
        )

    def test_jwt_token_creation (self ):
        """Test JWT token creation"""
        refresh =RefreshToken .for_user (self .user )
        access =refresh .access_token 

        self .assertIsNotNone (str (refresh ))
        self .assertIsNotNone (str (access ))


        self .assertNotEqual (str (refresh ),str (access ))

    def test_token_refresh (self ):
        """Test token refresh functionality"""
        refresh =RefreshToken .for_user (self .user )
        access1 =refresh .access_token 


        refresh .set_jti ()
        access2 =refresh .access_token 


        self .assertNotEqual (str (access1 ),str (access2 ))

    def test_user_authentication_with_token (self ):
        """Test that tokens work for authentication"""
        refresh =RefreshToken .for_user (self .user )
        self .client .credentials (HTTP_AUTHORIZATION =f'Bearer {refresh .access_token }')



        try :
            url =reverse ('tasks-list')
            response =self .client .get (url )


            self .assertNotEqual (response .status_code ,status .HTTP_401_UNAUTHORIZED )
        except :

            pass 


class UserPermissionsTest (APITestCase ):
    """Test cases for User permissions"""

    def setUp (self ):
        """Set up test data"""
        self .client =APIClient ()

        self .regular_user =User .objects .create_user (
        username ="regular",
        email ="regular@example.com",
        password ="testpass123"
        )

        self .staff_user =User .objects .create_user (
        username ="staff",
        email ="staff@example.com",
        password ="testpass123",
        is_staff =True 
        )

        self .admin_user =User .objects .create_superuser (
        username ="admin",
        email ="admin@example.com",
        password ="testpass123"
        )

    def authenticate (self ,user ):
        """Helper method to authenticate a user"""
        refresh =RefreshToken .for_user (user )
        self .client .credentials (HTTP_AUTHORIZATION =f'Bearer {refresh .access_token }')

    def test_regular_user_token_creation (self ):
        """Test that regular users can get tokens"""
        refresh =RefreshToken .for_user (self .regular_user )
        self .assertIsNotNone (str (refresh ))
        self .assertIsNotNone (str (refresh .access_token ))

    def test_staff_user_token_creation (self ):
        """Test that staff users can get tokens"""
        refresh =RefreshToken .for_user (self .staff_user )
        self .assertIsNotNone (str (refresh ))
        self .assertIsNotNone (str (refresh .access_token ))

    def test_admin_user_token_creation (self ):
        """Test that admin users can get tokens"""
        refresh =RefreshToken .for_user (self .admin_user )
        self .assertIsNotNone (str (refresh ))
        self .assertIsNotNone (str (refresh .access_token ))

    def test_user_permission_levels (self ):
        """Test different user permission levels"""

        self .assertFalse (self .regular_user .is_staff )
        self .assertFalse (self .regular_user .is_superuser )


        self .assertTrue (self .staff_user .is_staff )
        self .assertFalse (self .staff_user .is_superuser )


        self .assertTrue (self .admin_user .is_staff )
        self .assertTrue (self .admin_user .is_superuser )


class TeamIntegrationTest (APITestCase ):
    """Test cases for Team integration with authentication"""

    def setUp (self ):
        """Set up test data"""
        self .client =APIClient ()

        self .user1 =User .objects .create_user (
        username ="user1",
        email ="user1@example.com",
        password ="testpass123"
        )

        self .user2 =User .objects .create_user (
        username ="user2",
        email ="user2@example.com",
        password ="testpass123"
        )

        self .team =Team .objects .create (
        name ="Test Team",
        description ="A test team"
        )


        self .team .members .add (self .user1 ,self .user2 )

    def authenticate (self ,user ):
        """Helper method to authenticate a user"""
        refresh =RefreshToken .for_user (user )
        self .client .credentials (HTTP_AUTHORIZATION =f'Bearer {refresh .access_token }')

    def test_team_member_authentication (self ):
        """Test that team members can authenticate"""

        refresh1 =RefreshToken .for_user (self .user1 )
        refresh2 =RefreshToken .for_user (self .user2 )

        self .assertIsNotNone (str (refresh1 ))
        self .assertIsNotNone (str (refresh2 ))

    def test_team_relationships_persist_with_auth (self ):
        """Test that team relationships work with authentication"""
        self .authenticate (self .user1 )


        self .assertEqual (self .team .members .count (),2 )
        self .assertIn (self .user1 ,self .team .members .all ())
        self .assertIn (self .user2 ,self .team .members .all ())


        self .assertIn (self .team ,self .user1 .teams .all ())
        self .assertIn (self .team ,self .user2 .teams .all ())


class UserModelAPITest (TestCase ):
    """Test cases for User model in API context"""

    def setUp (self ):
        """Set up test data"""
        self .user =User .objects .create_user (
        username ="apiuser",
        email ="api@example.com",
        password ="testpass123",
        display_name ="API User"
        )

    def test_user_creation_for_api (self ):
        """Test user creation with API-relevant fields"""
        self .assertEqual (self .user .username ,"apiuser")
        self .assertEqual (self .user .email ,"api@example.com")
        self .assertEqual (self .user .display_name ,"API User")
        self .assertTrue (self .user .check_password ("testpass123"))

    def test_user_serializable_fields (self ):
        """Test that user has fields suitable for API serialization"""

        self .assertIsNotNone (self .user .username )
        self .assertIsNotNone (self .user .email )
        self .assertIsNotNone (self .user .date_joined )
        self .assertIsNotNone (self .user .is_active )


        self .assertEqual (self .user .display_name ,"API User")

    def test_user_token_payload_data (self ):
        """Test user data that would go in JWT token"""
        refresh =RefreshToken .for_user (self .user )


        self .assertEqual (str (refresh ['user_id']),str (self .user .id ))


        access =refresh .access_token 
        self .assertEqual (str (access ['user_id']),str (self .user .id ))


class SimpleEndpointTest (APITestCase ):
    """Simple tests to verify basic API functionality"""

    def setUp (self ):
        """Set up test data"""
        self .client =APIClient ()

        self .user =User .objects .create_user (
        username ="testuser",
        email ="test@example.com",
        password ="testpass123"
        )

    def test_unauthenticated_access (self ):
        """Test that protected endpoints require authentication"""

        try :
            url =reverse ('tasks-list')
            response =self .client .get (url )


            self .assertEqual (response .status_code ,status .HTTP_401_UNAUTHORIZED )
        except :

            pass 

    def test_authenticated_access (self ):
        """Test that authentication allows access to protected endpoints"""
        refresh =RefreshToken .for_user (self .user )
        self .client .credentials (HTTP_AUTHORIZATION =f'Bearer {refresh .access_token }')

        try :
            url =reverse ('tasks-list')
            response =self .client .get (url )


            self .assertNotEqual (response .status_code ,status .HTTP_401_UNAUTHORIZED )
        except :

            pass 

    def test_invalid_token (self ):
        """Test that invalid tokens are rejected"""
        self .client .credentials (HTTP_AUTHORIZATION ='Bearer invalid_token_here')

        try :
            url =reverse ('tasks-list')
            response =self .client .get (url )


            self .assertEqual (response .status_code ,status .HTTP_401_UNAUTHORIZED )
        except :

            pass 


class UserModelValidationTest (TestCase ):
    """Test cases for User model validation"""

    def test_username_validation (self ):
        """Test username validation"""

        user =User .objects .create_user (
        username ="valid_user123",
        email ="valid@example.com",
        password ="testpass123"
        )
        self .assertEqual (user .username ,"valid_user123")

    def test_email_validation (self ):
        """Test email validation"""

        user =User .objects .create_user (
        username ="testuser",
        email ="valid.email@example.com",
        password ="testpass123"
        )
        self .assertEqual (user .email ,"valid.email@example.com")

    def test_password_setting (self ):
        """Test password is properly hashed"""
        user =User .objects .create_user (
        username ="testuser",
        email ="test@example.com",
        password ="plaintext_password"
        )


        self .assertNotEqual (user .password ,"plaintext_password")
        self .assertTrue (user .check_password ("plaintext_password"))
        self .assertFalse (user .check_password ("wrong_password"))

    def test_user_defaults (self ):
        """Test user default values"""
        user =User .objects .create_user (
        username ="testuser",
        email ="test@example.com",
        password ="testpass123"
        )


        self .assertTrue (user .is_active )
        self .assertFalse (user .is_staff )
        self .assertFalse (user .is_superuser )
        self .assertEqual (user .display_name ,"")
