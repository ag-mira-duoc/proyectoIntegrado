"""
Vistas para la app usuarios (autenticación, perfil, dashboard)
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime

from .forms import LoginForm, RegistroForm, PerfilForm, CambiarPasswordForm
from .decorators import administrador_requerido
from calificaciones.models import Calificacion, Cliente


def login_view(request):
    """
    Vista de inicio de sesión.
    
    GET: Muestra formulario de login
    POST: Autentica al usuario y redirige al dashboard
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Bienvenido, {user.get_full_name()}!')
            
            # Redirigir a next o al dashboard
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Email o contraseña incorrectos.')
    else:
        form = LoginForm()
    
    return render(request, 'usuarios/login.html', {'form': form})


def registro_view(request):
    """
    Vista de registro de nuevos usuarios.
    
    GET: Muestra formulario de registro
    POST: Crea nuevo usuario y lo autentica
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Cuenta creada exitosamente. Bienvenido, {user.get_full_name()}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = RegistroForm()
    
    return render(request, 'usuarios/registro.html', {'form': form})


def logout_view(request):
    """
    Vista de cierre de sesión.
    """
    logout(request)
    messages.info(request, 'Has cerrado sesión exitosamente.')
    return redirect('login')


@login_required
def perfil_view(request):
    """
    Vista de perfil del usuario.
    
    Muestra información del usuario y permite editar algunos campos.
    """
    password_form = None
    
    if request.method == 'POST':
        if 'change_password' in request.POST:
            password_form = CambiarPasswordForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Contraseña actualizada exitosamente.')
                return redirect('perfil')
        else:
            form = PerfilForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Perfil actualizado exitosamente.')
                return redirect('perfil')
    else:
        form = PerfilForm(instance=request.user)
        password_form = CambiarPasswordForm(request.user)
    
    context = {
        'form': form,
        'password_form': password_form,
    }
    return render(request, 'usuarios/perfil.html', context)


@login_required
def cambiar_password_view(request):
    """
    Vista para cambiar la contraseña del usuario.
    """
    if request.method == 'POST':
        form = CambiarPasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Contraseña actualizada exitosamente.')
            return redirect('perfil')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = CambiarPasswordForm(request.user)
    
    return render(request, 'usuarios/cambiar_password.html', {'form': form})


@login_required
def dashboard_view(request):
    """
    Vista del dashboard principal.
    
    Muestra estadísticas y gráficos de calificaciones.
    """
    anno_actual = datetime.now().year
    
    # Filtrar por corredora si el usuario no es administrador
    calificaciones_qs = Calificacion.objects.all()
    clientes_qs = Cliente.objects.all()
    
    if not (request.user.is_superuser or request.user.es_administrador()):
        if hasattr(request.user, 'corredora') and request.user.corredora:
            calificaciones_qs = calificaciones_qs.filter(corredora=request.user.corredora)
    
    # Estadísticas generales
    stats = {
        'total_calificaciones': calificaciones_qs.count(),
        'calificaciones_aprobadas': calificaciones_qs.filter(estado='APROBADA').count(),
        'calificaciones_revision': calificaciones_qs.filter(estado='REVISION').count(),
        'total_clientes': clientes_qs.filter(activo=True).count(),
    }
    
    # Datos para gráfico de estados
    estados_data = []
    estados_labels = []
    for estado, estado_display in Calificacion.ESTADOS:
        count = calificaciones_qs.filter(estado=estado).count()
        if count > 0:
            estados_data.append(count)
            estados_labels.append(estado_display)
    
    # Datos para gráfico de meses (año actual)
    meses_data = []
    for mes in range(1, 13):
        count = calificaciones_qs.filter(
            created_at__year=anno_actual,
            created_at__month=mes
        ).count()
        meses_data.append(count)
    
    # Calificaciones recientes (últimas 10)
    calificaciones_recientes = calificaciones_qs.order_by('-created_at')[:10]
    
    context = {
        'anno_actual': anno_actual,
        'stats': stats,
        'estados_data': estados_data,
        'estados_labels': estados_labels,
        'meses_data': meses_data,
        'calificaciones_recientes': calificaciones_recientes,
    }
    
    return render(request, 'dashboard/index.html', context)


def home_view(request):
    """
    Vista de página de inicio.
    Redirige al dashboard si está autenticado, sino al login.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


# ============================================================================
# CRUD USUARIOS (Solo Administradores)
# ============================================================================

@login_required
@administrador_requerido
def usuarios_lista(request):
    """Lista todos los usuarios del sistema."""
    usuarios = User.objects.all().select_related('corredora').prefetch_related('groups').order_by('-date_joined')
    return render(request, 'usuarios/lista.html', {'usuarios': usuarios})


@login_required
@administrador_requerido
def usuario_detalle(request, pk):
    """Detalle de un usuario."""
    usuario = get_object_or_404(User, pk=pk)
    return render(request, 'usuarios/detalle.html', {'usuario_detalle': usuario})


@login_required
@administrador_requerido
def usuario_editar(request, pk):
    """Edita un usuario y sus roles."""
    from .forms import EditarUsuarioForm
    from django.shortcuts import get_object_or_404
    
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuario {usuario.get_full_name()} actualizado.')
            return redirect('usuarios:detalle', pk=pk)
    else:
        form = EditarUsuarioForm(instance=usuario)
    
    return render(request, 'usuarios/form.html', {
        'form': form,
        'usuario_editando': usuario,
        'form_title': f'Editar Usuario: {usuario.get_full_name()}'
    })
