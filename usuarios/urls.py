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
    path('lista/', views.usuarios_lista, name='lista'),
    #path('cambiar-rol/<int:pk>/', views.usuario_cambiar_rol, name='cambiar_rol'),
]
