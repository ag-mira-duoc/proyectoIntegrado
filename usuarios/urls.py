from django.urls import path, include
from . import views

app_name = 'usuarios'


urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name="signup"),
    path('login/', views.LoginView.as_view(), name="login"),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.user_profile, name='profile'),
    path('current_user/', views.get_calificaciones_for_current_user, name="current_user"),
    # Panel de administracion
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/approve/<int:user_id>/', views.approve_user, name='approve_user'),
    path('admin/reject/<int:user_id>/', views.reject_user, name='reject_user'),
    path('admin/pending/', views.pending_users_list, name='pending_users'),
]