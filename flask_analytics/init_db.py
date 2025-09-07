from sqlalchemy import create_engine ,MetaData 
from sqlalchemy .ext .automap import automap_base 
from sqlalchemy .orm import sessionmaker 

def init_db (db_url :str ):
    engine =create_engine (
    db_url ,
    pool_pre_ping =True ,
    pool_size =10 ,
    max_overflow =5 ,
    connect_args ={"application_name":"flask_analytics"},
    )

    metadata =MetaData ()
    metadata .reflect (
    bind =engine ,
    only =[
    "tasks_task",
    "tasks_tag",
    "tasks_task_tags",
    "tasks_taskassignment",
    "tasks_comment",
    "tasks_taskhistory",
    "users_user",
    "users_team",
    ]
    )

    Base =automap_base (metadata =metadata )
    Base .prepare ()

    Session =sessionmaker (bind =engine ,autoflush =False ,expire_on_commit =False )

    return {
    "engine":engine ,
    "Session":Session ,
    "Task":Base .classes .tasks_task ,
    "Tag":Base .classes .tasks_tag ,
    "TaskTag":Base .classes .tasks_task_tags ,
    "TaskAssignment":Base .classes .tasks_taskassignment ,
    "Comment":Base .classes .tasks_comment ,
    "TaskHistory":Base .classes .tasks_taskhistory ,
    "User":Base .classes .users_user ,
    "Team":Base .classes .users_team ,
    }
