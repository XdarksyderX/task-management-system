

import django .core .validators 
import django .db .models .deletion 
from django .conf import settings 
from django .db import migrations ,models 


class Migration (migrations .Migration ):

    initial =True 

    dependencies =[
    ('users','0002_team'),
    migrations .swappable_dependency (settings .AUTH_USER_MODEL ),
    ]

    operations =[
    migrations .CreateModel (
    name ='Tag',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('name',models .CharField (max_length =50 ,unique =True )),
    ],
    options ={
    'ordering':['name'],
    },
    ),
    migrations .CreateModel (
    name ='Task',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('title',models .CharField (max_length =200 )),
    ('description',models .TextField (blank =True ,default ='')),
    ('status',models .CharField (choices =[('todo','To Do'),('in_progress','In Progress'),('blocked','Blocked'),('done','Done'),('archived','Archived')],default ='todo',max_length =32 )),
    ('priority',models .CharField (choices =[('low','Low'),('medium','Medium'),('high','High'),('urgent','Urgent')],default ='medium',max_length =16 )),
    ('due_date',models .DateTimeField (blank =True ,null =True )),
    ('estimated_hours',models .DecimalField (decimal_places =2 ,default =0 ,max_digits =6 ,validators =[django .core .validators .MinValueValidator (0 )])),
    ('actual_hours',models .DecimalField (blank =True ,decimal_places =2 ,max_digits =6 ,null =True ,validators =[django .core .validators .MinValueValidator (0 )])),
    ('metadata',models .JSONField (blank =True ,default =dict )),
    ('is_archived',models .BooleanField (default =False )),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('updated_at',models .DateTimeField (auto_now =True )),
    ('assigned_team',models .ForeignKey (blank =True ,null =True ,on_delete =django .db .models .deletion .SET_NULL ,related_name ='tasks',to ='users.team')),
    ('created_by',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='tasks_created',to =settings .AUTH_USER_MODEL )),
    ('parent_task',models .ForeignKey (blank =True ,null =True ,on_delete =django .db .models .deletion .SET_NULL ,related_name ='subtasks',to ='tasks.task')),
    ('tags',models .ManyToManyField (blank =True ,related_name ='tasks',to ='tasks.tag')),
    ],
    options ={
    'ordering':['-created_at'],
    },
    ),
    migrations .CreateModel (
    name ='Comment',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('body',models .TextField ()),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('author',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='task_comments',to =settings .AUTH_USER_MODEL )),
    ('task',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='comments',to ='tasks.task')),
    ],
    options ={
    'ordering':['-created_at'],
    },
    ),
    migrations .CreateModel (
    name ='TaskAssignment',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('role_in_task',models .CharField (blank =True ,choices =[('owner','Owner'),('collaborator','Collaborator')],default ='collaborator',max_length =50 )),
    ('assigned_at',models .DateTimeField (auto_now_add =True )),
    ('assigned_by',models .ForeignKey (blank =True ,null =True ,on_delete =django .db .models .deletion .SET_NULL ,related_name ='assignments_made',to =settings .AUTH_USER_MODEL )),
    ('task',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='assignments',to ='tasks.task')),
    ('user',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='assignments',to =settings .AUTH_USER_MODEL )),
    ],
    ),
    migrations .AddField (
    model_name ='task',
    name ='assigned_to',
    field =models .ManyToManyField (blank =True ,related_name ='tasks_assigned',through ='tasks.TaskAssignment',through_fields =('task','user'),to =settings .AUTH_USER_MODEL ),
    ),
    migrations .CreateModel (
    name ='TaskHistory',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('action',models .CharField (choices =[('created','Created'),('updated','Updated'),('status_changed','Status Changed'),('comment_added','Comment Added'),('archived','Archived')],max_length =100 )),
    ('metadata',models .JSONField (blank =True ,default =dict )),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('task',models .ForeignKey (on_delete =django .db .models .deletion .CASCADE ,related_name ='history',to ='tasks.task')),
    ('user',models .ForeignKey (blank =True ,null =True ,on_delete =django .db .models .deletion .SET_NULL ,related_name ='task_events',to =settings .AUTH_USER_MODEL )),
    ],
    options ={
    'ordering':['-created_at'],
    },
    ),
    migrations .CreateModel (
    name ='TaskTemplate',
    fields =[
    ('id',models .BigAutoField (auto_created =True ,primary_key =True ,serialize =False ,verbose_name ='ID')),
    ('name',models .CharField (max_length =100 ,unique =True )),
    ('template',models .JSONField (blank =True ,default =dict )),
    ('created_at',models .DateTimeField (auto_now_add =True )),
    ('created_by',models .ForeignKey (blank =True ,null =True ,on_delete =django .db .models .deletion .SET_NULL ,related_name ='task_templates',to =settings .AUTH_USER_MODEL )),
    ],
    options ={
    'ordering':['name'],
    },
    ),
    migrations .AddIndex (
    model_name ='taskassignment',
    index =models .Index (fields =['task','user'],name ='tasks_taska_task_id_bf9d8a_idx'),
    ),
    migrations .AddConstraint (
    model_name ='taskassignment',
    constraint =models .UniqueConstraint (fields =('task','user'),name ='uq_task_user'),
    ),
    migrations .AddIndex (
    model_name ='task',
    index =models .Index (fields =['status'],name ='tasks_task_status_4a0a95_idx'),
    ),
    migrations .AddIndex (
    model_name ='task',
    index =models .Index (fields =['priority'],name ='tasks_task_priorit_a900d4_idx'),
    ),
    migrations .AddIndex (
    model_name ='task',
    index =models .Index (fields =['is_archived'],name ='tasks_task_is_arch_7f263a_idx'),
    ),
    migrations .AddIndex (
    model_name ='task',
    index =models .Index (fields =['due_date'],name ='tasks_task_due_dat_bce847_idx'),
    ),
    migrations .AddIndex (
    model_name ='task',
    index =models .Index (fields =['created_at'],name ='tasks_task_created_be1ba2_idx'),
    ),
    migrations .AddIndex (
    model_name ='taskhistory',
    index =models .Index (fields =['task','created_at'],name ='tasks_taskh_task_id_a299e9_idx'),
    ),
    ]
