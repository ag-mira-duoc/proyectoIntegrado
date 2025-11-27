"""
URLs para la app calificaciones
"""
from django.urls import path
from . import views

app_name = 'calificaciones'

urlpatterns = [
    # Lista y CRUD
    path('', views.calificaciones_lista, name='listado'),
    path('<int:pk>/', views.calificacion_detalle, name='detalle'),
    path('crear/', views.calificacion_crear, name='crear'),
    path('<int:pk>/editar/', views.calificacion_editar, name='editar'),
    path('<int:pk>/eliminar/', views.calificacion_eliminar, name='eliminar'),
    
    # Reportes
    path('reportes/agentes/', views.reporte_calificaciones_por_agente, name='reporte_agentes'),
]
