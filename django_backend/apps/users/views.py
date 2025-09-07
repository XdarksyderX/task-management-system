from django .shortcuts import render ,get_object_or_404 ,redirect 
from django .contrib .auth .decorators import login_required 
from django .contrib import messages 
from django .http import Http404 ,HttpResponse 
from django .db import models 
from django .conf import settings 
from apps .users .models import Team 
from django .core .paginator import Paginator 


from .producer import (
publish_team_deleted ,
publish_team_member_left ,
publish_team_member_added ,
publish_team_member_removed ,
publish_team_updated ,
publish_user_logout 
)


def login_page (request ):
    return render (request ,"auth/login.html")

def register_page (request ):
    return render (request ,"auth/register.html")


def logout_view (request ):
    """Web logout view that clears JWT cookies and redirects to login"""

    if request .user and request .user .is_authenticated :
        publish_user_logout (request .user .id ,request .user .username )


    response =redirect ('users:login')
    response .delete_cookie (getattr (settings ,'AUTH_COOKIE_ACCESS','access_token'))
    response .delete_cookie (getattr (settings ,'AUTH_COOKIE_REFRESH','refresh_token'))

    return response 




@login_required 
def team_list (request ):
    """View for displaying the team list with SSR data"""

    user_teams =Team .objects .filter (
    models .Q (created_by =request .user )|
    models .Q (members =request .user )
    ).distinct ().order_by ('name')


    if request .method =='POST':
        action =request .POST .get ('action')

        if action =='delete_team':
            team_id =request .POST .get ('team_id')
            if team_id :
                try :
                    team =Team .objects .get (id =team_id ,created_by =request .user )
                    team_name =team .name 
                    team_id_for_event =team .id 
                    team .delete ()

                    publish_team_deleted (request .user .id ,team_id_for_event ,team_name )
                    messages .success (request ,f'Team "{team_name }" deleted successfully.')
                except Team .DoesNotExist :
                    messages .error (request ,'Team not found or you do not have permission to delete it.')

        elif action =='leave_team':
            team_id =request .POST .get ('team_id')
            if team_id :
                try :
                    team =Team .objects .get (id =team_id )
                    if request .user in team .members .all ():
                        team .members .remove (request .user )

                        publish_team_member_left (request .user .id ,team .id ,team .name )
                        messages .success (request ,f'You have left the team "{team .name }".')
                    else :
                        messages .error (request ,'You are not a member of this team.')
                except Team .DoesNotExist :
                    messages .error (request ,'Team not found.')

        return redirect ('users:team_list')

    context ={
    'teams':user_teams ,
    'user':request .user 
    }
    return render (request ,'teams/team_list.html',context )


@login_required 
def team_detail (request ,team_id ):
    """View for displaying team detail with SSR data"""
    team =get_object_or_404 (Team ,id =team_id )


    if not (team .created_by ==request .user or request .user in team .members .all ()):
        messages .error (request ,'You do not have permission to access this team.')
        return redirect ('users:team_list')


    if request .method =='POST':
        action =request .POST .get ('action')

        if action =='add_member'and team .created_by ==request .user :
            user_id =request .POST .get ('user_id')
            if user_id :
                try :
                    from django .contrib .auth import get_user_model 
                    User =get_user_model ()
                    user_to_add =User .objects .get (id =user_id )

                    if user_to_add not in team .members .all ()and user_to_add !=team .created_by :
                        team .members .add (user_to_add )

                        publish_team_member_added (
                        request .user .id ,
                        team .id ,
                        team .name ,
                        user_to_add .id ,
                        user_to_add .username 
                        )
                        messages .success (request ,f'User {user_to_add .username } added to team.')
                    else :
                        messages .warning (request ,'User is already a member of this team.')
                except User .DoesNotExist :
                    messages .error (request ,'User not found.')

        elif action =='remove_member'and team .created_by ==request .user :
            user_id =request .POST .get ('user_id')
            if user_id :
                try :
                    from django .contrib .auth import get_user_model 
                    User =get_user_model ()
                    user_to_remove =User .objects .get (id =user_id )
                    team .members .remove (user_to_remove )

                    publish_team_member_removed (
                    request .user .id ,
                    team .id ,
                    team .name ,
                    user_to_remove .id ,
                    user_to_remove .username 
                    )
                    messages .success (request ,f'User {user_to_remove .username } removed from team.')
                except User .DoesNotExist :
                    messages .error (request ,'User not found.')

        elif action =='leave_team'and request .user in team .members .all ():
            team .members .remove (request .user )

            publish_team_member_left (request .user .id ,team .id ,team .name )
            messages .success (request ,f'You have left the team "{team .name }".')
            return redirect ('users:team_list')

        elif action =='delete_team'and team .created_by ==request .user :
            team_name =team .name 
            team_id_for_event =team .id 
            team .delete ()

            publish_team_deleted (request .user .id ,team_id_for_event ,team_name )
            messages .success (request ,f'Team "{team_name }" has been deleted successfully.')
            return redirect ('users:team_list')

        return redirect ('users:team_detail',team_id =team .id )

    context ={
    'team':team ,
    'members':team .members .exclude (id =team .created_by .id ),
    'is_admin':team .created_by ==request .user ,
    'is_member':request .user in team .members .all (),
    'user':request .user 
    }
    return render (request ,'teams/team_detail.html',context )


@login_required 
def team_edit (request ,team_id ):
    """View for editing team with SSR data"""
    team =get_object_or_404 (Team ,id =team_id )


    if team .created_by !=request .user :
        messages .error (request ,'You do not have permission to edit this team.')
        return redirect ('users:team_detail',team_id =team .id )

    if request .method =='POST':
        action =request .POST .get ('action')

        if action =='delete_team':

            team_name =team .name 
            team_id_for_event =team .id 
            team .delete ()

            publish_team_deleted (request .user .id ,team_id_for_event ,team_name )
            messages .success (request ,f'Team "{team_name }" has been deleted successfully.')
            return redirect ('users:team_list')

        else :

            name =request .POST .get ('name','').strip ()
            description =request .POST .get ('description','').strip ()

            if name :

                changes ={}
                if team .name !=name :
                    changes ['name']={'old':team .name ,'new':name }
                if team .description !=description :
                    changes ['description']={'old':team .description ,'new':description }

                team .name =name 
                team .description =description 
                team .save ()


                if changes :
                    publish_team_updated (request .user .id ,team .id ,team .name ,changes )

                messages .success (request ,f'Team "{team .name }" updated successfully!')
                return redirect ('users:team_detail',team_id =team .id )
            else :
                messages .error (request ,'Team name is required.')

    context ={
    'team':team ,
    'user':request .user 
    }
    return render (request ,'teams/team_edit.html',context )
