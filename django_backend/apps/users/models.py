from django .contrib .auth .models import AbstractUser 
from django .db import models 

class User (AbstractUser ):
    display_name =models .CharField (max_length =150 ,blank =True ,default ="")

    def __str__ (self ):
        return self .username 

class Team (models .Model ):
    name =models .CharField (max_length =150 )
    description =models .TextField (blank =True )
    created_by =models .ForeignKey (
    User ,
    on_delete =models .CASCADE ,
    related_name ="teams_created",
    help_text ="Creator and admin of the team",
    null =True ,
    blank =True 
    )
    members =models .ManyToManyField (
    User ,
    related_name ="teams",
    blank =True 
    )
    created_at =models .DateTimeField (auto_now_add =True )

    def __str__ (self ):
        return self .name 

    def is_admin (self ,user ):
        """Check if user is the admin/creator of the team"""
        return self .created_by ==user 

    def add_member (self ,user ):
        """Add a user to the team"""
        self .members .add (user )

    def remove_member (self ,user ):
        """Remove a user from the team"""
        self .members .remove (user )

    def is_member (self ,user ):
        """Check if user is a member of the team"""
        return self .members .filter (id =user .id ).exists ()

    def can_manage (self ,user ):
        """Check if user can manage the team (admin or staff)"""
        return self .is_admin (user )or user .is_staff 

    @property 
    def member_count (self ):
        """Get the number of members in the team"""
        return self .members .count ()