"""
URLs para la app usuarios
"""
from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # CRUD Usuarios (admin)
    path('', views.usuarios_lista, name='listado'),
    path('<int:pk>/', views.usuario_detalle, name='detalle'),
    path('<int:pk>/editar/', views.usuario_editar, name='editar'),
]
