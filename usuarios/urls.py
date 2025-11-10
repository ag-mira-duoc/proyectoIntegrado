from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name="signup"),
    path('login/', views.LoginView.as_view(), name="login"),
    path('current_user/', views.get_calificaciones_for_current_user, name="current_user"),
]