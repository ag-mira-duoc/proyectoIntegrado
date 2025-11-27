"""
Vistas para la app calificaciones (CRUD, reportes)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime
import json

from .models import Calificacion, Cliente, PersonaNatural, PersonaJuridica, Corredora
from .forms import CalificacionForm, ClienteForm, PersonaNaturalForm, PersonaJuridicaForm, CorrederaForm
from usuarios.decorators import analista_requerido, administrador_requerido, rol_requerido


@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def calificaciones_lista(request):
    """
    Vista de lista de calificaciones con filtros.
    
    Filtros disponibles:
    - Año
    - Estado
    - Búsqueda por cliente (RUT o nombre)
    """
    # Base queryset
    calificaciones = Calificacion.objects.select_related('cliente', 'user', 'corredora').all()
    
    # Filtrar por corredora si no es administrador
    if not (request.user.is_superuser or request.user.es_administrador()):
        if hasattr(request.user, 'corredora') and request.user.corredora:
            calificaciones = calificaciones.filter(corredora=request.user.corredora)
    
    # Filtros
    anno = request.GET.get('anno')
    estado = request.GET.get('estado')
    search = request.GET.get('search')
    
    if anno:
        calificaciones = calificaciones.filter(anno=anno)
    
    if estado:
        calificaciones = calificaciones.filter(estado=estado)
    
    if search:
        calificaciones = calificaciones.filter(
            Q(cliente__rut__icontains=search) |
            Q(cliente__persona_natural__nombre__icontains=search) |
            Q(cliente__persona_natural__apellido__icontains=search) |
            Q(cliente__persona_juridica__razon_social__icontains=search)
        )
    
    # Ordenar por fecha de creación (más reciente primero)
    calificaciones = calificaciones.order_by('-created_at')
    
    # Paginación
    paginator = Paginator(calificaciones, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Años disponibles para filtro
    years = range(2020, datetime.now().year + 2)
    
    context = {
        'calificaciones': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'years': years,
    }
    
    return render(request, 'calificaciones/lista.html', context)


@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def calificacion_detalle(request, pk):
    """
    Vista de detalle de una calificación.
    """
    calificacion = get_object_or_404(Calificacion, pk=pk)
    
    # Verificar acceso por corredora
    if not (request.user.is_superuser or request.user.es_administrador()):
        if hasattr(request.user, 'corredora') and request.user.corredora:
            if calificacion.corredora != request.user.corredora:
                messages.error(request, 'No tienes permiso para ver esta calificación.')
                return redirect('calificaciones:listado')
    
    context = {
        'calificacion': calificacion,
    }
    
    return render(request, 'calificaciones/detalle.html', context)


@login_required
@analista_requerido
def calificacion_crear(request):
    """
    Vista para crear una nueva calificación.
    """
    if request.method == 'POST':
        form = CalificacionForm(request.POST, user=request.user)
        if form.is_valid():
            calificacion = form.save(commit=False)
            calificacion.user = request.user
            
            # Asignar corredora del usuario
            if hasattr(request.user, 'corredora') and request.user.corredora:
                calificacion.corredora = request.user.corredora
            
            calificacion.save()
            messages.success(request, 'Calificación creada exitosamente.')
            return redirect('calificaciones:detalle', pk=calificacion.pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = CalificacionForm(user=request.user)
    
    context = {
        'form': form,
        'form_title': 'Nueva Calificación Tributaria',
    }
    
    return render(request, 'calificaciones/form.html', context)


@login_required
@analista_requerido
def calificacion_editar(request, pk):
    """
    Vista para editar una calificación existente.
    """
    calificacion = get_object_or_404(Calificacion, pk=pk)
    
    # Solo se pueden editar calificaciones en BORRADOR o REVISION
    if calificacion.estado not in ['BORRADOR', 'REVISION']:
        messages.warning(request, 'Solo se pueden editar calificaciones en estado Borrador o En Revisión.')
        return redirect('calificaciones:detalle', pk=pk)
    
    # Verificar acceso por corredora
    if not (request.user.is_superuser or request.user.es_administrador()):
        if hasattr(request.user, 'corredora') and request.user.corredora:
            if calificacion.corredora != request.user.corredora:
                messages.error(request, 'No tienes permiso para editar esta calificación.')
                return redirect('calificaciones:listado')
    
    if request.method == 'POST':
        form = CalificacionForm(request.POST, instance=calificacion, user=request.user)
        if form.is_valid():
            calificacion = form.save(commit=False)
            calificacion.user = request.user  # Actualizar usuario que modifica
            calificacion.save()
            messages.success(request, 'Calificación actualizada exitosamente.')
            return redirect('calificaciones:detalle', pk=pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = CalificacionForm(instance=calificacion, user=request.user)
    
    context = {
        'form': form,
        'form_title': f'Editar Calificación #{calificacion.id}',
        'calificacion': calificacion,
    }
    
    return render(request, 'calificaciones/form.html', context)


@login_required
@administrador_requerido
def calificacion_eliminar(request, pk):
    """
    Vista para eliminar una calificación (solo administradores).
    """
    calificacion = get_object_or_404(Calificacion, pk=pk)
    
    if request.method == 'POST':
        calificacion.delete()
        messages.success(request, 'Calificación eliminada exitosamente.')
        return redirect('calificaciones:listado')
    
    context = {
        'calificacion': calificacion,
    }
    
    return render(request, 'calificaciones/confirmar_eliminar.html', context)


@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def reporte_calificaciones_por_agente(request):
    """
    Reporte: Cantidad de calificaciones ingresadas por agentes de una corredora.
    
    Muestra estadísticas de cuántas calificaciones ha creado cada usuario (agente)
    de la corredora en un período determinado.
    """
    # Obtener corredora
    if request.user.is_superuser or request.user.es_administrador():
        # Administradores pueden elegir corredora
        corredora_id = request.GET.get('corredora')
        if corredora_id:
            corredora = get_object_or_404(Corredora, pk=corredora_id)
        else:
            corredora = None
        corredoras = Corredora.objects.filter(activa=True)
    else:
        # Otros usuarios ven solo su corredora
        corredora = request.user.corredora
        corredoras = [corredora] if corredora else []
    
    # Filtros de fecha
    anno = request.GET.get('anno', datetime.now().year)
    
    # Consulta
    if corredora:
        estadisticas = Calificacion.objects.filter(
            corredora=corredora,
            anno=anno
        ).values(
            'user__id',
            'user__nombre',
            'user__apellido',
            'user__email'
        ).annotate(
            total_calificaciones=Count('id'),
            aprobadas=Count('id', filter=Q(estado='APROBADA')),
            en_revision=Count('id', filter=Q(estado='REVISION')),
            borradores=Count('id', filter=Q(estado='BORRADOR')),
        ).order_by('-total_calificaciones')
    else:
        estadisticas = []
    
    context = {
        'corredora': corredora,
        'corredoras': corredoras,
        'anno': anno,
        'estadisticas': estadisticas,
        'years': range(2020, datetime.now().year + 2),
    }
    
    return render(request, 'calificaciones/reporte_agentes.html', context)
