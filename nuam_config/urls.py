"""
URL configuration for nuam_config project.

Sistema NUAM - Calificaciones Tributarias
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from usuarios import views as usuarios_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Autenticación
    path('', usuarios_views.home_view, name='home'),
    path('login/', usuarios_views.login_view, name='login'),
    path('registro/', usuarios_views.registro_view, name='registro'),
    path('logout/', usuarios_views.logout_view, name='logout'),
    path('perfil/', usuarios_views.perfil_view, name='perfil'),
    path('cambiar-password/', usuarios_views.cambiar_password_view, name='cambiar_password'),

    # Dashboard
    path('dashboard/', usuarios_views.dashboard_view, name='dashboard'),

    # Apps
    path('calificaciones/', include('calificaciones.urls')),
    path('usuarios/', include('usuarios.urls')),
    # path('auditoria/', include('auditoria.urls')),  # Por implementar
    # path('documentos/', include('documentos.urls')),  # Por implementar
]

# Media files (development only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Django Debug Toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
