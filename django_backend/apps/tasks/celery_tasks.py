from datetime import timedelta 

from celery import shared_task 
from django .conf import settings 
from django .contrib .auth import get_user_model 
from django .core .mail import send_mail 
from django .db .models import Count 
from django .utils import timezone 

from apps .tasks .models import (
Task ,TaskHistory ,TaskAction ,TaskStatus 
)

User =get_user_model ()



def _emails (users ):
	return sorted ({u .email for u in users if getattr (u ,"email",None )})

def _notify (users ,subject ,body ):
	recipients =_emails (users )
	if not recipients :
		return 0 
	send_mail (subject ,body ,settings .DEFAULT_FROM_EMAIL ,recipients ,fail_silently =True )
	return len (recipients )

def _task_recipients (task ):
	assignees =list (task .assigned_to .all ())
	if assignees :
		return assignees 
	return [task .created_by ]if task .created_by and task .created_by .email else []



@shared_task 
def send_task_notification (task_id ,notification_type ):
	"""
	Send email notifications for task events.
	notification_type: created | assigned | status_changed | comment_added | overdue | updated
	"""
	try :
		task =Task .objects .select_related ("created_by").prefetch_related ("assigned_to","tags").get (pk =task_id )
	except Task .DoesNotExist :
		return 0 

	users =_task_recipients (task )
	if not users :
		return 0 

	nt =notification_type 
	if nt =="created":
		subject =f"[Task Created] {task .title }"
		body =f"The task '{task .title }' was created (priority: {task .priority })."
	elif nt =="assigned":
		subject =f"[Assignment] {task .title }"
		body =f"You have been assigned to the task '{task .title }'."
	elif nt =="status_changed":
		subject =f"[Status Changed] {task .title }"
		body =f"The status of '{task .title }' is now: {task .status }."
	elif nt =="comment_added":
		subject =f"[New Comment] {task .title }"
		body =f"A comment was added to the task '{task .title }'."
	elif nt =="overdue":
		subject =f"[Overdue] {task .title }"
		body =f"The task '{task .title }' is overdue (due_date: {task .due_date })."
	else :
		subject =f"[Update] {task .title }"
		body =f"The task '{task .title }' has been updated."

	return _notify (users ,subject ,body )


@shared_task 
def generate_daily_summary ():
	"""
	Send a daily summary to each user with:
	  - newly assigned in the last 24h
	  - completed in the last 24h
	  - overdue
	  - pending (todo / in_progress / blocked)
	Returns the number of emails sent.
	"""
	now =timezone .now ()
	yesterday =now -timedelta (days =1 )


	users =(
	User .objects .filter (is_active =True )
	.annotate (
	t_cnt =Count ("tasks_assigned",distinct =True )+Count ("tasks_created",distinct =True )
	)
	.filter (t_cnt__gt =0 )
	)

	total_sent =0 
	for u in users :
		if not u .email :
			continue 

		newly_assigned =Task .objects .filter (
		assigned_to =u ,
		created_at__gte =yesterday ,
		).count ()

		completed_last_24h =Task .objects .filter (
		assigned_to =u ,
		status =TaskStatus .DONE ,
		updated_at__gte =yesterday ,
		).count ()

		overdue =Task .objects .filter (
		assigned_to =u ,
		is_archived =False ,
		due_date__lt =now ,
		).exclude (status__in =[TaskStatus .DONE ,TaskStatus .ARCHIVED ]).count ()

		pending =Task .objects .filter (
		assigned_to =u ,
		is_archived =False ,
		status__in =[TaskStatus .TODO ,TaskStatus .IN_PROGRESS ,TaskStatus .BLOCKED ],
		).count ()

		if not any ([newly_assigned ,completed_last_24h ,overdue ,pending ]):
			continue 

		subject ="[Daily Summary] Tasks"
		body =(
		f"Hello {u .username },\n\n"
		f"Newly assigned (24h): {newly_assigned }\n"
		f"Completed (24h): {completed_last_24h }\n"
		f"Overdue: {overdue }\n"
		f"Pending: {pending }\n\n"
		f"Cut-off time: {now .strftime ('%Y-%m-%d %H:%M')}\n"
		)
		total_sent +=_notify ([u ],subject ,body )

	return total_sent 


@shared_task 
def check_overdue_tasks ():
	"""
	Mark overdue tasks (not DONE/ARCHIVED) as 'blocked' and notify assignees.
	Returns the number of tasks marked as overdue.
	"""
	now =timezone .now ()
	qs =(
	Task .objects .select_related ("created_by")
	.prefetch_related ("assigned_to")
	.filter (
	is_archived =False ,
	due_date__lt =now ,
	)
	.exclude (status__in =[TaskStatus .DONE ,TaskStatus .ARCHIVED ])
	)

	updated =0 
	for t in qs :
		old =t .status 
		if old ==TaskStatus .BLOCKED :

			continue 
		t .status =TaskStatus .BLOCKED 
		t .save (update_fields =["status","updated_at"])
		TaskHistory .objects .create (
		task =t ,
		user =None ,
		action =TaskAction .STATUS_CHANGED ,
		metadata ={"from":old ,"to":TaskStatus .BLOCKED },
		)
		send_task_notification .delay (t .id ,"overdue")
		updated +=1 

	return updated 


@shared_task 
def cleanup_archived_tasks ():
	"""
	Delete archived tasks older than 30 days since their last update.
	Returns the number of deleted tasks.
	"""
	cutoff =timezone .now ()-timedelta (days =30 )
	old =Task .objects .filter (is_archived =True ,updated_at__lt =cutoff )
	count =old .count ()
	if count :
		old .delete ()
	return count 


@shared_task 
def send_websocket_comment (task_id ,comment_id ,event_type ):
	"""
	Send WebSocket notifications for comment events.
	event_type: comment_added | comment_edited | comment_deleted
	"""
	try :
		from channels .layers import get_channel_layer 
		from asgiref .sync import async_to_sync 
		from apps .tasks .models import Task ,Comment 


		task =Task .objects .get (pk =task_id )

		if event_type =="comment_deleted":
			comment_data ={"id":comment_id }
		else :
			comment =Comment .objects .select_related ('author').get (pk =comment_id )
			comment_data ={
			'id':comment .id ,
			'content':comment .content ,
			'author':{
			'id':comment .author .id ,
			'username':comment .author .username ,
			'first_name':comment .author .first_name ,
			'last_name':comment .author .last_name ,
			},
			'created_at':comment .created_at .isoformat (),
			'updated_at':comment .updated_at .isoformat (),
			}


		channel_layer =get_channel_layer ()
		room_group_name =f'task_comments_{task_id }'

		async_to_sync (channel_layer .group_send )(
		room_group_name ,
		{
		'type':f'comment_{event_type .split ("_")[1 ]}',
		'comment':comment_data 
		}
		)

		return True 

	except Exception as e :
		print (f"Error sending WebSocket comment notification: {e }")
		return False 


@shared_task 
def send_websocket_task_update (task_id ,update_data ,user_id ):
	"""
	Send WebSocket notifications for task updates.
	"""
	try :
		from channels .layers import get_channel_layer 
		from asgiref .sync import async_to_sync 
		from django .contrib .auth import get_user_model 

		User =get_user_model ()
		user =User .objects .get (pk =user_id )


		channel_layer =get_channel_layer ()
		room_group_name =f'task_room_{task_id }'

		async_to_sync (channel_layer .group_send )(
		room_group_name ,
		{
		'type':'task_updated',
		'update_data':update_data ,
		'user':{
		'id':user .id ,
		'username':user .username ,
		'first_name':user .first_name ,
		'last_name':user .last_name ,
		}
		}
		)

		return True 

	except Exception as e :
		print (f"Error sending WebSocket task update: {e }")
		return False 
