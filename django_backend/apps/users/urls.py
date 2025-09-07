from django .urls import path ,include 
from .views import login_page ,register_page ,logout_view ,team_list ,team_detail ,team_edit 

app_name ='users'

urlpatterns =[

path ("login/",login_page ,name ="login"),
path ("register/",register_page ,name ="register"),
path ("logout/",logout_view ,name ="logout"),


path ("",team_list ,name ="team_list"),
path ("<int:team_id>/",team_detail ,name ="team_detail"),
path ("<int:team_id>/edit/",team_edit ,name ="team_edit"),
]
