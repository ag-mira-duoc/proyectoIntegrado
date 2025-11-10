from django.urls import path
from . import views

app_name = 'calificaciones'

urlpatterns = [
    path('', views.calificaciones_page, name='calificaciones_page'),
    path('api', views.CalificacionListCreateView.as_view(), name="list_calificaciones"),
    path('api/<int:pk>/', views.CalificacionRetrieveUpdateDeleteView.as_view(), name="calificacion_detail"),
]