from django.urls import path
from . import views

app_name = 'calificaciones'

urlpatterns = [
    # Listado y Detalles
    path('', views.calificaciones_lista, name='listado'),
    path('<int:pk>/', views.calificacion_detalle, name='detalle'),
    
    # CRUD Manual
    path('crear/', views.calificacion_crear, name='crear'),
    path('<int:pk>/editar/', views.calificacion_editar, name='editar'),
    path('<int:pk>/eliminar/', views.calificacion_eliminar, name='eliminar'),
    
    # Nuevos Módulos (Requeridos por Dashboard)
    path('ingreso-monto/', views.ingreso_por_monto, name='ingreso_monto'),
    path('carga-masiva/', views.carga_masiva_factores, name='carga_masiva'),
    path('carga-masiva/confirmar/', views.confirmar_carga, name='confirmar_carga'),
    
    # Reportes
    path('reporte-agentes/', views.reporte_calificaciones_por_agente, name='reporte_agentes'),
]