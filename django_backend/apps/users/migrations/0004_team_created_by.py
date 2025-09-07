

import django .db .models .deletion 
from django .conf import settings 
from django .db import migrations ,models 


class Migration (migrations .Migration ):

    dependencies =[
    ('users','0003_alter_user_is_active'),
    ]

    operations =[
    migrations .AddField (
    model_name ='team',
    name ='created_by',
    field =models .ForeignKey (blank =True ,help_text ='Creator and admin of the team',null =True ,on_delete =django .db .models .deletion .CASCADE ,related_name ='teams_created',to =settings .AUTH_USER_MODEL ),
    ),
    ]
