from django .test import TestCase 
from django .contrib .auth import get_user_model 
from django .core .exceptions import ValidationError 
from django .db import IntegrityError 

from apps .users .models import Team 

User =get_user_model ()


class CustomUserModelTest (TestCase ):
    """Test cases for Custom User model"""

    def test_create_user (self ):
        """Test creating a basic user"""
        user =User .objects .create_user (
        username ="testuser",
        email ="test@example.com",
        password ="testpass123"
        )

        self .assertEqual (user .username ,"testuser")
        self .assertEqual (user .email ,"test@example.com")
        self .assertTrue (user .check_password ("testpass123"))
        self .assertTrue (user .is_active )
        self .assertFalse (user .is_staff )
        self .assertFalse (user .is_superuser )

    def test_create_user_with_display_name (self ):
        """Test creating user with display name"""
        user =User .objects .create_user (
        username ="testuser",
        email ="test@example.com",
        password ="testpass123",
        display_name ="John Doe"
        )

        self .assertEqual (user .display_name ,"John Doe")

    def test_create_superuser (self ):
        """Test creating a superuser"""
        user =User .objects .create_superuser (
        username ="admin",
        email ="admin@example.com",
        password ="adminpass123"
        )

        self .assertEqual (user .username ,"admin")
        self .assertTrue (user .is_active )
        self .assertTrue (user .is_staff )
        self .assertTrue (user .is_superuser )

    def test_user_string_representation (self ):
        """Test user string representation"""
        user =User .objects .create_user (
        username ="testuser",
        email ="test@example.com",
        password ="testpass123"
        )

        self .assertEqual (str (user ),"testuser")

    def test_user_email_normalization (self ):
        """Test that email is normalized"""
        user =User .objects .create_user (
        username ="testuser",
        email ="Test@EXAMPLE.COM",
        password ="testpass123"
        )

        self .assertEqual (user .email ,"Test@example.com")

    def test_username_required (self ):
        """Test that username is required"""
        with self .assertRaises (ValueError ):
            User .objects .create_user (
            username ="",
            email ="test@example.com",
            password ="testpass123"
            )

    def test_unique_username (self ):
        """Test that username must be unique"""
        User .objects .create_user (
        username ="testuser",
        email ="test1@example.com",
        password ="testpass123"
        )

        with self .assertRaises (IntegrityError ):
            User .objects .create_user (
            username ="testuser",
            email ="test2@example.com",
            password ="testpass123"
            )

    def test_unique_email_not_enforced (self ):
        """Test that email uniqueness is not enforced by default in Django User model"""
        User .objects .create_user (
        username ="user1",
        email ="test@example.com",
        password ="testpass123"
        )



        user2 =User .objects .create_user (
        username ="user2",
        email ="test@example.com",
        password ="testpass123"
        )

        self .assertEqual (user2 .email ,"test@example.com")


class TeamModelTest (TestCase ):
    """Test cases for Team model"""

    def setUp (self ):
        """Set up test data"""
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

    def test_create_team (self ):
        """Test creating a basic team"""
        team =Team .objects .create (
        name ="Development Team",
        description ="Backend development team"
        )

        self .assertEqual (team .name ,"Development Team")
        self .assertEqual (team .description ,"Backend development team")
        self .assertIsNotNone (team .created_at )

    def test_team_string_representation (self ):
        """Test team string representation"""
        team =Team .objects .create (
        name ="Test Team"
        )

        self .assertEqual (str (team ),"Test Team")

    def test_team_members_relationship (self ):
        """Test team members many-to-many relationship"""
        team =Team .objects .create (
        name ="Test Team",
        description ="A test team"
        )


        team .members .add (self .user1 ,self .user2 )


        self .assertEqual (team .members .count (),2 )
        self .assertIn (self .user1 ,team .members .all ())
        self .assertIn (self .user2 ,team .members .all ())
        self .assertIn (team ,self .user1 .teams .all ())
        self .assertIn (team ,self .user2 .teams .all ())

    def test_team_without_members (self ):
        """Test creating team without members"""
        team =Team .objects .create (
        name ="Empty Team",
        description ="Team with no members"
        )

        self .assertEqual (team .members .count (),0 )

    def test_remove_team_member (self ):
        """Test removing member from team"""
        team =Team .objects .create (name ="Test Team")
        team .members .add (self .user1 ,self .user2 )


        team .members .remove (self .user1 )

        self .assertEqual (team .members .count (),1 )
        self .assertNotIn (self .user1 ,team .members .all ())
        self .assertIn (self .user2 ,team .members .all ())


class TeamAdminTest (TestCase ):
    """Test cases for Team admin functionality"""

    def setUp (self ):
        self .admin_user =User .objects .create_user (
        username ="admin",
        email ="admin@example.com",
        password ="testpass123"
        )
        self .member_user =User .objects .create_user (
        username ="member",
        email ="member@example.com",
        password ="testpass123"
        )
        self .other_user =User .objects .create_user (
        username ="other",
        email ="other@example.com",
        password ="testpass123"
        )

        self .team =Team .objects .create (
        name ="Test Team",
        description ="A test team",
        created_by =self .admin_user 
        )

    def test_team_creation_with_admin (self ):
        """Test creating team with admin"""
        self .assertEqual (self .team .created_by ,self .admin_user )
        self .assertTrue (self .team .is_admin (self .admin_user ))
        self .assertFalse (self .team .is_admin (self .member_user ))

    def test_is_admin_method (self ):
        """Test is_admin method"""
        self .assertTrue (self .team .is_admin (self .admin_user ))
        self .assertFalse (self .team .is_admin (self .member_user ))
        self .assertFalse (self .team .is_admin (self .other_user ))

    def test_add_member_method (self ):
        """Test add_member method"""
        self .team .add_member (self .member_user )
        self .assertTrue (self .team .is_member (self .member_user ))
        self .assertEqual (self .team .member_count ,1 )

    def test_remove_member_method (self ):
        """Test remove_member method"""
        self .team .add_member (self .member_user )
        self .team .add_member (self .other_user )

        self .team .remove_member (self .member_user )

        self .assertFalse (self .team .is_member (self .member_user ))
        self .assertTrue (self .team .is_member (self .other_user ))
        self .assertEqual (self .team .member_count ,1 )

    def test_is_member_method (self ):
        """Test is_member method"""
        self .assertFalse (self .team .is_member (self .member_user ))

        self .team .add_member (self .member_user )
        self .assertTrue (self .team .is_member (self .member_user ))

    def test_can_manage_method (self ):
        """Test can_manage method"""

        self .assertTrue (self .team .can_manage (self .admin_user ))


        self .assertFalse (self .team .can_manage (self .member_user ))


        staff_user =User .objects .create_user (
        username ="staff",
        email ="staff@example.com",
        password ="testpass123",
        is_staff =True 
        )
        self .assertTrue (self .team .can_manage (staff_user ))

    def test_member_count_property (self ):
        """Test member_count property"""
        self .assertEqual (self .team .member_count ,0 )

        self .team .add_member (self .member_user )
        self .assertEqual (self .team .member_count ,1 )

        self .team .add_member (self .other_user )
        self .assertEqual (self .team .member_count ,2 )

        self .team .remove_member (self .member_user )
        self .assertEqual (self .team .member_count ,1 )

    def test_team_admin_cascade_deletion (self ):
        """Test that deleting admin deletes the team"""
        team_id =self .team .id 
        self .admin_user .delete ()


        with self .assertRaises (Team .DoesNotExist ):
            Team .objects .get (id =team_id )


class UserManagerTest (TestCase ):
    """Test cases for custom User manager"""

    def test_create_user_without_username_raises_error (self ):
        """Test that creating user without username raises ValueError"""
        with self .assertRaises (ValueError )as context :
            User .objects .create_user (username ='',email ='test@example.com',password ='pass')

        self .assertIn ('username',str (context .exception ).lower ())

    def test_create_superuser_with_is_staff_false_raises_error (self ):
        """Test that creating superuser with is_staff=False raises ValueError"""
        with self .assertRaises (ValueError ):
            User .objects .create_superuser (
            username ='admin',
            email ='admin@example.com',
            password ='pass',
            is_staff =False 
            )

    def test_create_superuser_with_is_superuser_false_raises_error (self ):
        """Test that creating superuser with is_superuser=False raises ValueError"""
        with self .assertRaises (ValueError ):
            User .objects .create_superuser (
            username ='admin',
            email ='admin@example.com',
            password ='pass',
            is_superuser =False 
            )


class UserModelMethodsTest (TestCase ):
    """Test cases for User model methods"""

    def setUp (self ):
        """Set up test data"""
        self .user =User .objects .create_user (
        username ="testuser",
        email ="test@example.com",
        password ="testpass123",
        first_name ="John",
        last_name ="Doe",
        display_name ="Johnny"
        )

    def test_get_full_name (self ):
        """Test get_full_name method"""
        self .assertEqual (self .user .get_full_name (),"John Doe")

    def test_get_full_name_no_names (self ):
        """Test get_full_name when no first/last name"""
        user =User .objects .create_user (
        username ="noname",
        email ="noname@example.com",
        password ="testpass123"
        )

        self .assertEqual (user .get_full_name (),"")

    def test_get_short_name (self ):
        """Test get_short_name method"""
        self .assertEqual (self .user .get_short_name (),"John")

    def test_get_short_name_no_first_name (self ):
        """Test get_short_name when no first name"""
        user =User .objects .create_user (
        username ="noname",
        email ="noname@example.com",
        password ="testpass123"
        )

        self .assertEqual (user .get_short_name (),"")

    def test_display_name_field (self ):
        """Test display_name field"""
        self .assertEqual (self .user .display_name ,"Johnny")


        user2 =User .objects .create_user (
        username ="user2",
        email ="user2@example.com",
        password ="testpass123"
        )

        self .assertEqual (user2 .display_name ,"")


class TeamModelMethodsTest (TestCase ):
    """Test cases for Team model methods"""

    def setUp (self ):
        """Set up test data"""
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

    def test_team_member_count (self ):
        """Test counting team members"""

        self .assertEqual (self .team .members .count (),0 )


        self .team .members .add (self .user1 )
        self .assertEqual (self .team .members .count (),1 )

        self .team .members .add (self .user2 )
        self .assertEqual (self .team .members .count (),2 )

    def test_team_creation_timestamp (self ):
        """Test that teams have creation timestamp"""
        self .assertIsNotNone (self .team .created_at )


        import time 
        time .sleep (0.01 )

        team2 =Team .objects .create (name ="Team 2")
        self .assertGreater (team2 .created_at ,self .team .created_at )


class ModelRelationshipsTest (TestCase ):
    """Test cases for model relationships"""

    def setUp (self ):
        """Set up test data"""
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

        self .team1 =Team .objects .create (name ="Team 1")
        self .team2 =Team .objects .create (name ="Team 2")

    def test_user_multiple_teams (self ):
        """Test that users can belong to multiple teams"""
        self .team1 .members .add (self .user1 )
        self .team2 .members .add (self .user1 )

        self .assertEqual (self .user1 .teams .count (),2 )
        self .assertIn (self .team1 ,self .user1 .teams .all ())
        self .assertIn (self .team2 ,self .user1 .teams .all ())

    def test_team_multiple_members (self ):
        """Test that teams can have multiple members"""
        self .team1 .members .add (self .user1 ,self .user2 )

        self .assertEqual (self .team1 .members .count (),2 )
        self .assertIn (self .user1 ,self .team1 .members .all ())
        self .assertIn (self .user2 ,self .team1 .members .all ())

    def test_cascade_behavior (self ):
        """Test what happens when user is deleted"""
        self .team1 .members .add (self .user1 )


        user_id =self .user1 .id 
        self .user1 .delete ()


        self .team1 .refresh_from_db ()
        self .assertEqual (self .team1 .members .count (),0 )
        self .assertFalse (User .objects .filter (id =user_id ).exists ())
