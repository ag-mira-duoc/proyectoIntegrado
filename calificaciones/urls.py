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
    path('api/extraer-pdf/', views.procesar_pdf_ajax, name='api_extraer_pdf'),
    path('api/guardar-lote/', views.guardar_lote_ajax, name='api_guardar_lote'),

    # Reportes
    path('reporte-agentes/', views.reporte_calificaciones_por_agente, name='reporte_agentes'),
    path('reportes-admin/', views.reportes_admin, name='reportes_admin'),
    path('reportes-admin/descargar/', views.descargar_reportes_excel, name='descargar_reportes_excel'),
]