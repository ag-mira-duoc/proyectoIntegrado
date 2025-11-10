from django.urls import path
from . import views

app_name = 'calificaciones'

urlpatterns = [
    path('', views.CalificacionListCreateView.as_view(), name="list_calificaciones"),
    path('<int:pk>/', views.CalificacionRetrieveUpdateDeleteView.as_view(), name="calificacion_detail"),
]