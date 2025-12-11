from django.urls import path
from . import views

app_name = 'auditoria'

urlpatterns = [
    path('exportar/', views.exportar_logs_excel, name='exportar_excel'),
]