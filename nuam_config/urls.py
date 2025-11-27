from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from usuarios import views as usuarios_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', usuarios_views.home_view, name='home'),
    path('login/', usuarios_views.login_view, name='login'),
    path('registro/', usuarios_views.registro_view, name='registro'),
    path('logout/', usuarios_views.logout_view, name='logout'),
    path('perfil/', usuarios_views.perfil_view, name='perfil'),
    path('cambiar-password/', usuarios_views.cambiar_password_view, name='cambiar_password'),
    path('dashboard/', usuarios_views.dashboard_view, name='dashboard'),
    path('calificaciones/', include('calificaciones.urls')),
    path('clientes/', include('calificaciones.urls_clientes')),
    path('corredoras/', include('calificaciones.urls_corredoras')),
    path('usuarios/', include('usuarios.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
