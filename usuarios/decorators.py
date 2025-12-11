"""
Decoradores para control de acceso basado en roles (RBAC)
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def rol_requerido(*roles):
    """
    Decorador para restringir acceso a vistas según roles.
    
    Uso:
        @rol_requerido('Administradores')
        def vista_admin(request):
            ...
        
        @rol_requerido('Administradores', 'Analistas')
        def vista_admin_analista(request):
            ...
    
    Args:
        *roles: Nombres de grupos permitidos (Administradores, Analistas, Auditores)
    
    Raises:
        PermissionDenied: Si el usuario no tiene el rol requerido
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            user_groups = request.user.groups.values_list('name', flat=True)
            
            # Superusuarios tienen acceso total
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Verificar si el usuario tiene alguno de los roles permitidos
            if any(role in user_groups for role in roles):
                return view_func(request, *args, **kwargs)
            
            # Usuario no autorizado
            messages.error(request, 'No tienes permisos para acceder a esta página.')
            raise PermissionDenied
        
        return wrapped_view
    return decorator


def administrador_requerido(view_func):
    """
    Decorador para vistas que solo pueden ser accedidas por administradores.
    
    Uso:
        @administrador_requerido
        def vista_admin(request):
            ...
    """
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser or request.user.es_administrador():
            return view_func(request, *args, **kwargs)
        
        messages.error(request, 'Solo administradores pueden acceder a esta página.')
        raise PermissionDenied
    
    return wrapped_view


def analista_requerido(view_func):
    """
    Decorador para vistas que solo pueden ser accedidas por analistas o administradores.
    
    Uso:
        @analista_requerido
        def vista_analista(request):
            ...
    """
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if (request.user.is_superuser or 
            request.user.es_administrador() or 
            request.user.es_analista()):
            return view_func(request, *args, **kwargs)
        
        messages.error(request, 'Solo analistas pueden acceder a esta página.')
        raise PermissionDenied
    
    return wrapped_view


def auditor_requerido(view_func):
    """
    Decorador para vistas que solo pueden ser accedidas por auditores o administradores.
    
    Uso:
        @auditor_requerido
        def vista_auditor(request):
            ...
    """
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if (request.user.is_superuser or 
            request.user.es_administrador() or 
            request.user.es_auditor()):
            return view_func(request, *args, **kwargs)
        
        messages.error(request, 'Solo auditores pueden acceder a esta página.')
        raise PermissionDenied
    
    return wrapped_view


def corredora_propia(view_func):
    """
    Decorador para asegurar que el usuario solo accede a datos de su corredora.
    
    Este decorador debe usarse en conjunto con otros decoradores de rol.
    
    Uso:
        @analista_requerido
        @corredora_propia
        def vista_datos_corredora(request):
            # request.user.corredora está disponible
            ...
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Superusuarios y admins pueden ver todo
        if request.user.is_superuser or request.user.es_administrador():
            return view_func(request, *args, **kwargs)
        
        # Verificar que el usuario tenga corredora asignada
        if not hasattr(request.user, 'corredora') or request.user.corredora is None:
            messages.error(request, 'No tienes una corredora asignada.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view
