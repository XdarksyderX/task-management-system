from django .conf import settings 
from django .core .validators import MinValueValidator 
from django .db import models 



class TaskStatus (models .TextChoices ):
    TODO ="todo","To Do"
    IN_PROGRESS ="in_progress","In Progress"
    BLOCKED ="blocked","Blocked"
    DONE ="done","Done"
    ARCHIVED ="archived","Archived"


class TaskPriority (models .TextChoices ):
    LOW ="low","Low"
    MEDIUM ="medium","Medium"
    HIGH ="high","High"
    URGENT ="urgent","Urgent"


class TaskRole (models .TextChoices ):
    OWNER ="owner","Owner"
    COLLABORATOR ="collaborator","Collaborator"


class TaskAction (models .TextChoices ):
    CREATED ="created","Created"
    UPDATED ="updated","Updated"
    STATUS_CHANGED ="status_changed","Status Changed"
    COMMENT_ADDED ="comment_added","Comment Added"
    ARCHIVED ="archived","Archived"



class Tag (models .Model ):
    name =models .CharField (max_length =50 ,unique =True )

    class Meta :
        ordering =["name"]

    def __str__ (self )->str :
        return self .name 


class Task (models .Model ):
    title =models .CharField (max_length =200 )
    description =models .TextField (blank =True ,default ="")

    status =models .CharField (
    max_length =32 ,
    choices =TaskStatus .choices ,
    default =TaskStatus .TODO 
    )
    priority =models .CharField (
    max_length =16 ,
    choices =TaskPriority .choices ,
    default =TaskPriority .MEDIUM 
    )

    due_date =models .DateTimeField (null =True ,blank =True )
    estimated_hours =models .DecimalField (
    max_digits =6 ,
    decimal_places =2 ,
    default =0 ,
    validators =[MinValueValidator (0 )]
    )
    actual_hours =models .DecimalField (
    max_digits =6 ,
    decimal_places =2 ,
    null =True ,
    blank =True ,
    validators =[MinValueValidator (0 )]
    )

    created_by =models .ForeignKey (
    settings .AUTH_USER_MODEL ,
    on_delete =models .CASCADE ,
    related_name ="tasks_created"
    )
    assigned_team =models .ForeignKey (
    "users.Team",
    null =True ,
    blank =True ,
    on_delete =models .SET_NULL ,
    related_name ="tasks"
    )
    assigned_to =models .ManyToManyField (
    settings .AUTH_USER_MODEL ,
    through ="TaskAssignment",
    through_fields =('task','user'),
    related_name ="tasks_assigned",
    blank =True 
    )
    tags =models .ManyToManyField ("Tag",blank =True ,related_name ="tasks")

    parent_task =models .ForeignKey (
    "self",
    null =True ,
    blank =True ,
    on_delete =models .SET_NULL ,
    related_name ="subtasks"
    )

    metadata =models .JSONField (default =dict ,blank =True )

    is_archived =models .BooleanField (default =False )

    created_at =models .DateTimeField (auto_now_add =True )
    updated_at =models .DateTimeField (auto_now =True )

    class Meta :
        indexes =[
        models .Index (fields =["status"]),
        models .Index (fields =["priority"]),
        models .Index (fields =["is_archived"]),
        models .Index (fields =["due_date"]),
        models .Index (fields =["created_at"]),
        ]
        ordering =["-created_at"]

    def __str__ (self )->str :
        return self .title 


class TaskAssignment (models .Model ):
    task =models .ForeignKey (Task ,on_delete =models .CASCADE ,related_name ="assignments")
    user =models .ForeignKey (settings .AUTH_USER_MODEL ,on_delete =models .CASCADE ,related_name ="assignments")
    assigned_by =models .ForeignKey (
    settings .AUTH_USER_MODEL ,
    on_delete =models .SET_NULL ,
    null =True ,
    blank =True ,
    related_name ="assignments_made"
    )
    role_in_task =models .CharField (
    max_length =50 ,
    choices =TaskRole .choices ,
    default =TaskRole .COLLABORATOR ,
    blank =True ,
    )
    assigned_at =models .DateTimeField (auto_now_add =True )

    class Meta :
        constraints =[
        models .UniqueConstraint (fields =["task","user"],name ="uq_task_user")
        ]
        indexes =[models .Index (fields =["task","user"])]

    def __str__ (self )->str :
        return f"{self .user_id } -> {self .task_id }"


class Comment (models .Model ):
    task =models .ForeignKey (Task ,on_delete =models .CASCADE ,related_name ="comments")
    author =models .ForeignKey (
    settings .AUTH_USER_MODEL ,
    on_delete =models .CASCADE ,
    related_name ="task_comments"
    )
    body =models .TextField ()
    created_at =models .DateTimeField (auto_now_add =True )
    updated_at =models .DateTimeField (auto_now =True )

    class Meta :
        ordering =["-created_at"]

    def __str__ (self )->str :
        return f"Comment #{self .pk } on {self .task_id }"


class TaskHistory (models .Model ):
    task =models .ForeignKey (Task ,on_delete =models .CASCADE ,related_name ="history")
    user =models .ForeignKey (
    settings .AUTH_USER_MODEL ,
    null =True ,
    blank =True ,
    on_delete =models .SET_NULL ,
    related_name ="task_events"
    )
    action =models .CharField (max_length =100 ,choices =TaskAction .choices )
    metadata =models .JSONField (default =dict ,blank =True )
    created_at =models .DateTimeField (auto_now_add =True )

    class Meta :
        ordering =["-created_at"]
        indexes =[models .Index (fields =["task","created_at"])]

    def __str__ (self )->str :
        return f"{self .action } on {self .task_id }"


class TaskTemplate (models .Model ):
    name =models .CharField (max_length =100 ,unique =True )
    template =models .JSONField (default =dict ,blank =True )

    created_by =models .ForeignKey (
    settings .AUTH_USER_MODEL ,
    on_delete =models .SET_NULL ,
    null =True ,
    blank =True ,
    related_name ="task_templates"
    )
    created_at =models .DateTimeField (auto_now_add =True )

    class Meta :
        ordering =["name"]

    def __str__ (self )->str :
        return self .name 
