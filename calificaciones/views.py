"""
Vistas para la app calificaciones (CRUD, reportes, cálculos y cargas masivas)
"""
import csv
import io
from decimal import Decimal
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponse
from django.utils import timezone

from .models import Calificacion, Cliente, Corredora, User
from .forms import (
    CalificacionForm, ClienteForm, PersonaNaturalForm, PersonaJuridicaForm, CorrederaForm,
    IngresoMontoForm, CargaMasivaFactoresForm
)
from usuarios.decorators import analista_requerido, administrador_requerido, rol_requerido


# ============================================================================
# VISTAS DE CALIFICACIONES (CRUD + PROCESOS)
# ============================================================================

@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def calificaciones_lista(request):
    """
    Vista de lista de calificaciones con filtros y modal de ingreso.
    """
    # Optimización: prefetch_related para evitar N+1 queries
    calificaciones = Calificacion.objects.select_related('cliente', 'user', 'corredora').all()
    
    # --- VISIBILIDAD ---
    # Auditores y Administradores ven todo.
    # Analistas solo ven lo de su corredora.
    es_privilegiado = (
        request.user.is_superuser or 
        getattr(request.user, 'es_administrador', lambda: False)() or 
        getattr(request.user, 'es_auditor', lambda: False)()
    )

    if not es_privilegiado:
        if hasattr(request.user, 'corredora') and request.user.corredora:
            calificaciones = calificaciones.filter(corredora=request.user.corredora)
        else:
            calificaciones = calificaciones.filter(user=request.user)
    
    # --- FILTROS ---
    anno = request.GET.get('anno')
    origen = request.GET.get('origen') # Ahora filtra por ID de USUARIO
    mercado = request.GET.get('mercado')
    search = request.GET.get('search')
    
    if anno:
        calificaciones = calificaciones.filter(anno=anno)
    
    if mercado:
        calificaciones = calificaciones.filter(mercado=mercado)

    if origen:
        # Filtra por el usuario que ingresó la calificación
        calificaciones = calificaciones.filter(user__id=origen)

    if search:
        calificaciones = calificaciones.filter(
            Q(instrumento__icontains=search) |
            Q(cliente__rut__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    # Orden solicitado: Ejercicio descendente
    calificaciones = calificaciones.order_by('-anno', 'instrumento')
    
    # Paginación
    paginator = Paginator(calificaciones, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Contexto
    clientes_list = Cliente.objects.filter(activo=True)
    years = range(2020, datetime.now().year + 2)
    
    # Lista de usuarios para el filtro de "Origen" (Solo para Admins/Auditores)
    # Mostramos usuarios activos ordenados por nombre para facilitar la búsqueda
    usuarios_list = []
    if es_privilegiado:
        usuarios_list = User.objects.filter(is_active=True).order_by('nombre', 'apellido')

    context = {
        'calificaciones': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'years': years,
        'clientes_list': clientes_list,
        'usuarios_list': usuarios_list, # Lista de usuarios para el filtro
        'es_privilegiado': es_privilegiado,
    }
    
    return render(request, 'calificaciones/lista.html', context)


@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def calificacion_detalle(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk)
    
    # Verificación de permisos
    es_privilegiado = (
        request.user.is_superuser or 
        getattr(request.user, 'es_administrador', lambda: False)() or 
        getattr(request.user, 'es_auditor', lambda: False)()
    )

    if not es_privilegiado:
        if hasattr(request.user, 'corredora') and request.user.corredora:
            if calificacion.corredora != request.user.corredora:
                messages.error(request, 'No tienes permiso para ver esta calificación.')
                return redirect('calificaciones:listado')
    
    # Factores
    lista_factores = []
    for i in range(8, 38):
        nombre_campo = f'factor{i}'
        valor = getattr(calificacion, nombre_campo)
        try:
            campo = Calificacion._meta.get_field(nombre_campo)
            descripcion = campo.help_text
        except:
            descripcion = f"Factor {i}"

        lista_factores.append({
            'numero': i,
            'descripcion': descripcion,
            'valor': valor
        })

    return render(request, 'calificaciones/detalle.html', {
        'calificacion': calificacion,
        'lista_factores': lista_factores
    })

@login_required
@analista_requerido
def calificacion_crear(request):
    if request.method == 'POST':
        form = CalificacionForm(request.POST, user=request.user)
        if form.is_valid():
            calificacion = form.save(commit=False)
            calificacion.user = request.user
            if hasattr(request.user, 'corredora') and request.user.corredora:
                calificacion.corredora = request.user.corredora
            calificacion.save()
            messages.success(request, 'Calificación creada exitosamente.')
            return redirect('calificaciones:detalle', pk=calificacion.pk)
        else:
            messages.error(request, f'Error al guardar: {form.errors.as_text()}')
            return redirect('calificaciones:listado')
    else:
        return redirect('calificaciones:listado')

@login_required
@analista_requerido
def calificacion_editar(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk)
    if calificacion.estado not in ['BORRADOR', 'REVISION']:
        messages.warning(request, 'Solo se pueden editar calificaciones en Borrador o Revisión.')
        return redirect('calificaciones:detalle', pk=pk)
    
    es_privilegiado = (request.user.is_superuser or getattr(request.user, 'es_administrador', lambda: False)())
    if not es_privilegiado:
        if hasattr(request.user, 'corredora') and request.user.corredora:
            if calificacion.corredora != request.user.corredora:
                messages.error(request, 'Sin permiso.')
                return redirect('calificaciones:listado')

    if request.method == 'POST':
        form = CalificacionForm(request.POST, instance=calificacion, user=request.user)
        if form.is_valid():
            calificacion = form.save(commit=False)
            calificacion.user = request.user
            calificacion.save()
            messages.success(request, 'Calificación actualizada.')
            return redirect('calificaciones:detalle', pk=pk)
        else:
            messages.error(request, 'Corrija los errores.')
    else:
        form = CalificacionForm(instance=calificacion, user=request.user)
    return render(request, 'calificaciones/form.html', {'form': form, 'form_title': f'Editar #{calificacion.id}'})


@login_required
@administrador_requerido
def calificacion_eliminar(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk)
    if request.method == 'POST':
        calificacion.delete()
        messages.success(request, 'Eliminado correctamente.')
        return redirect('calificaciones:listado')
    return render(request, 'calificaciones/confirmar_eliminar.html', {'calificacion': calificacion})

@login_required
@analista_requerido
def ingreso_por_monto(request):
    if request.method == 'POST':
        form = IngresoMontoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            total = data['monto_total_reparto']
            if total == 0:
                messages.error(request, "El monto total no puede ser cero.")
                return redirect('calificaciones:ingreso_monto')
            
            f8 = (data['monto_f8_credito_idpc'] / total).quantize(Decimal("0.00000001"))
            f12 = (data['monto_f12_exento'] / total).quantize(Decimal("0.00000001"))
            
            calificacion = Calificacion(
                cliente=data['cliente'],
                anno=data['anno'],
                factor8=f8,
                factor12=f12,
                user=request.user,
                estado='BORRADOR',
                ingreso_montos=True
            )
            # Guardar factor_actualizacion si viene en el form
            if 'factor_actualizacion' in data:
                calificacion.factor_actualizacion = data['factor_actualizacion']

            if hasattr(request.user, 'corredora') and request.user.corredora:
                calificacion.corredora = request.user.corredora
            calificacion.save()
            messages.success(request, "Cálculo realizado y guardado.")
            return redirect('calificaciones:listado')
    else:
        form = IngresoMontoForm()
    return render(request, 'calificaciones/ingreso_monto.html', {'form': form})

@login_required
@analista_requerido
def carga_masiva_factores(request):
    if request.method == 'POST':
        form = CargaMasivaFactoresForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['archivo_csv']
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            cont_exito = 0
            for row in reader:
                try:
                    def clean_dec(val):
                        if not val: return Decimal(0)
                        return Decimal(val.replace(',', '.'))
                    
                    fecha_str = row.get('Fecha', '')
                    fecha_obj = None
                    if fecha_str:
                        fecha_obj = datetime.strptime(fecha_str, '%d-%m-%Y').date()

                    nuevo_obj = Calificacion(
                        anno=int(row['Ejercicio']),
                        mercado=row['Mercado'][:3],
                        instrumento=row['Instrumento'][:50],
                        fecha_pago=fecha_obj,
                        secuencia_evento=int(row['Secuencia']),
                        numero_dividendo=int(row.get('Numero de dividendo', 0)),
                        tipo_sociedad=row.get('Tipo sociedad', '')[:1],
                        valor_historico=clean_dec(row.get('Valor Historico')),
                        factor8=clean_dec(row.get('Factor 8')),
                        factor9=clean_dec(row.get('Factor 9')),
                        # ... resto de factores ...
                        user=request.user,
                        estado='BORRADOR',
                        ingreso_montos=False
                    )
                    if hasattr(request.user, 'corredora') and request.user.corredora:
                        nuevo_obj.corredora = request.user.corredora
                    nuevo_obj.save()
                    cont_exito += 1
                except Exception:
                    pass
            messages.success(request, f"Carga finalizada. {cont_exito} registros creados.")
            return redirect('calificaciones:listado')
    else:
        form = CargaMasivaFactoresForm()
    return render(request, 'calificaciones/carga_masiva.html', {'form': form})


@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def reporte_calificaciones_por_agente(request):
    if request.user.is_superuser or request.user.es_administrador():
        corredora_id = request.GET.get('corredora')
        if corredora_id:
            corredora = get_object_or_404(Corredora, pk=corredora_id)
        else:
            corredora = None
        corredoras = Corredora.objects.filter(activa=True)
    else:
        corredora = request.user.corredora
        corredoras = [corredora] if corredora else []
    
    anno = request.GET.get('anno', datetime.now().year)
    estadisticas = []
    if corredora:
        estadisticas = Calificacion.objects.filter(corredora=corredora, anno=anno).values(
            'user__id', 'user__nombre', 'user__apellido', 'user__email'
        ).annotate(
            total_calificaciones=Count('id'),
            aprobadas=Count('id', filter=Q(estado='APROBADA')),
            en_revision=Count('id', filter=Q(estado='REVISION')),
            borradores=Count('id', filter=Q(estado='BORRADOR')),
        ).order_by('-total_calificaciones')
    
    return render(request, 'calificaciones/reporte_agentes.html', {
        'corredora': corredora, 'corredoras': corredoras, 'anno': anno, 'estadisticas': estadisticas, 'years': range(2020, datetime.now().year + 2)
    })


# ============================================================================
# VISTAS DE CLIENTES (CRUD)
# ============================================================================

@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def clientes_lista(request):
    """
    Lista todos los clientes activos.
    """
    clientes = Cliente.objects.filter(activo=True).order_by('rut')
    return render(request, 'clientes/lista.html', {'clientes': clientes})


@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def cliente_detalle(request, pk):
    """
    Muestra el detalle de un cliente específico.
    """
    cliente = get_object_or_404(Cliente, pk=pk)
    return render(request, 'clientes/detalle.html', {'cliente': cliente})


@login_required
@analista_requerido
def cliente_crear(request):
    """
    Crea un nuevo cliente. Maneja la lógica de pestañas (Natural/Jurídica)
    validando solo los formularios correspondientes al tipo seleccionado.
    """
    tipo_seleccionado = 'natural' 

    if request.method == 'POST':
        tipo = request.POST.get('tipo', 'natural')
        tipo_seleccionado = tipo
        
        # El formulario base (ClienteForm) siempre se valida
        cliente_form = ClienteForm(request.POST)
        
        # Inicializamos los formularios específicos
        if tipo == 'natural':
            persona_form = PersonaNaturalForm(request.POST)
            persona_juridica_form = PersonaJuridicaForm() 
        else:
            persona_form = PersonaJuridicaForm(request.POST)
            persona_natural_form = PersonaNaturalForm() 

        # Validamos Cliente + El formulario específico seleccionado
        if cliente_form.is_valid() and persona_form.is_valid():
            try:
                # 1. Guardar Cliente Base
                cliente = cliente_form.save()
                
                # 2. Guardar Persona Específica vinculada al cliente
                persona = persona_form.save(commit=False)
                persona.cliente = cliente
                persona.save()
                
                messages.success(request, 'Cliente creado exitosamente.')
                return redirect('clientes:detalle', pk=cliente.pk)
            except Exception as e:
                messages.error(request, f'Error al guardar en base de datos: {str(e)}')
        else:
            # Feedback de errores
            if not cliente_form.is_valid():
                messages.error(request, f"Error en Datos de Contacto: {cliente_form.errors.as_text()}")
            if not persona_form.is_valid():
                messages.error(request, f"Error en Datos Específicos: {persona_form.errors.as_text()}")
    else:
        # GET: Formularios vacíos
        cliente_form = ClienteForm()
        persona_natural_form = PersonaNaturalForm()
        persona_juridica_form = PersonaJuridicaForm()
        persona_form = None

    context = {
        'cliente_form': cliente_form,
        # Pasamos los formularios específicos para que se rendericen en el HTML
        'persona_natural_form': persona_natural_form if request.method == 'GET' else (persona_form if tipo_seleccionado == 'natural' else PersonaNaturalForm()),
        'persona_juridica_form': persona_juridica_form if request.method == 'GET' else (persona_form if tipo_seleccionado == 'juridica' else PersonaJuridicaForm()),
        'tipo_seleccionado': tipo_seleccionado, 
    }
    
    return render(request, 'clientes/form.html', context)


@login_required
@analista_requerido
def cliente_editar(request, pk):
    """
    Edita un cliente existente. Detecta automáticamente si es Natural o Jurídica.
    """
    cliente = get_object_or_404(Cliente, pk=pk)
    
    # Determinar tipo de cliente actual
    es_natural = hasattr(cliente, 'persona_natural')
    tipo_seleccionado = 'natural' if es_natural else 'juridica'
    
    if request.method == 'POST':
        cliente_form = ClienteForm(request.POST, instance=cliente)
        
        if es_natural:
            persona_form = PersonaNaturalForm(request.POST, instance=cliente.persona_natural)
        else:
            persona_form = PersonaJuridicaForm(request.POST, instance=cliente.persona_juridica)
        
        if cliente_form.is_valid() and persona_form.is_valid():
            cliente_form.save()
            persona_form.save()
            messages.success(request, 'Cliente actualizado correctamente.')
            return redirect('clientes:detalle', pk=pk)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        cliente_form = ClienteForm(instance=cliente)
        if es_natural:
            persona_form = PersonaNaturalForm(instance=cliente.persona_natural)
        else:
            persona_form = PersonaJuridicaForm(instance=cliente.persona_juridica)
    
    # Para el template de edición, simplificamos pasando solo el form activo
    context = {
        'cliente_form': cliente_form,
        'persona_form': persona_form, # Este se renderizará genéricamente en el template
        'es_natural': es_natural,     # Flag para saber qué mostrar
        'cliente': cliente,
        'edit_mode': True             # Para adaptar el template si es necesario
    }

    return render(request, 'clientes/form.html', context)


# ============================================================================
# VISTAS DE CORREDORAS (CRUD)
# ============================================================================

@login_required
@administrador_requerido
def corredoras_lista(request):
    """
    Lista todas las corredoras registradas.
    """
    corredoras = Corredora.objects.all().order_by('nombre')
    return render(request, 'corredoras/lista.html', {'corredoras': corredoras})


@login_required
@administrador_requerido
def corredora_detalle(request, pk):
    """
    Muestra el detalle de una corredora.
    """
    corredora = get_object_or_404(Corredora, pk=pk)
    return render(request, 'corredoras/detalle.html', {'corredora': corredora})


@login_required
@administrador_requerido
def corredora_crear(request):
    """
    Crea una nueva corredora.
    """
    if request.method == 'POST':
        # Nota: Usamos CorrederaForm según tu archivo forms.py (ojo con el typo 'Corredera' vs 'Corredora')
        form = CorrederaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Corredora creada exitosamente.')
            return redirect('corredoras:listado')
        else:
            messages.error(request, 'Error al crear la corredora. Verifique los datos.')
    else:
        form = CorrederaForm()
    
    return render(request, 'corredoras/form.html', {
        'form': form, 
        'form_title': 'Nueva Corredora'
    })


@login_required
@administrador_requerido
def corredora_editar(request, pk):
    """
    Edita una corredora existente.
    """
    corredora = get_object_or_404(Corredora, pk=pk)
    
    if request.method == 'POST':
        form = CorrederaForm(request.POST, instance=corredora)
        if form.is_valid():
            form.save()
            messages.success(request, 'Corredora actualizada exitosamente.')
            return redirect('corredoras:detalle', pk=pk)
        else:
            messages.error(request, 'Error al actualizar. Verifique los datos.')
    else:
        form = CorrederaForm(instance=corredora)
    
    return render(request, 'corredoras/form.html', {
        'form': form, 
        'form_title': f'Editar {corredora.nombre}'
    })