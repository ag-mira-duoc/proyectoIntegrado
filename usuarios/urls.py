"""
URLs para la app usuarios
"""
from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # Listado de usuarios (para administradores)
    # path('', views.usuarios_lista, name='listado'),  # Por implementar
]
