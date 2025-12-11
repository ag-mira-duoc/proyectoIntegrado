from django.urls import path
from . import views

app_name = 'corredoras'

urlpatterns = [
    path('', views.corredoras_lista, name='listado'),
    path('<int:pk>/', views.corredora_detalle, name='detalle'),
    path('crear/', views.corredora_crear, name='crear'),
    path('<int:pk>/editar/', views.corredora_editar, name='editar'),
]
