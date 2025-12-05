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

from .models import Calificacion, Cliente, Corredora
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
    
    calificaciones = calificaciones.order_by('-created_at')
    
    # Paginación
    paginator = Paginator(calificaciones, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Contexto para el modal y filtros
    clientes_list = Cliente.objects.filter(activo=True)
    years = range(2020, datetime.now().year + 2)
    
    context = {
        'calificaciones': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'years': years,
        'clientes_list': clientes_list, # Necesario para el selector del Modal
    }
    
    return render(request, 'calificaciones/lista.html', context)


@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def calificacion_detalle(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk)
    
    if not (request.user.is_superuser or request.user.es_administrador()):
        if hasattr(request.user, 'corredora') and request.user.corredora:
            if calificacion.corredora != request.user.corredora:
                messages.error(request, 'No tienes permiso para ver esta calificación.')
                return redirect('calificaciones:listado')
    
    # --- PREPARACIÓN DE FACTORES PARA EL TEMPLATE ---
    lista_factores = []
    for i in range(8, 38):
        nombre_campo = f'factor{i}'
        # Obtener valor
        valor = getattr(calificacion, nombre_campo)
        # Obtener descripción (help_text) del modelo
        campo = Calificacion._meta.get_field(nombre_campo)
        
        lista_factores.append({
            'numero': i,
            'descripcion': campo.help_text,
            'valor': valor
        })

    context = {
        'calificacion': calificacion,
        'lista_factores': lista_factores, # Pasamos la lista procesada al template
    }
    
    return render(request, 'calificaciones/detalle.html', context)


@login_required
@analista_requerido
def calificacion_crear(request):
    """
    Procesa el formulario del Modal de Ingreso Manual.
    """
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
            # Imprimir errores en consola para depuración y mostrar mensaje al usuario
            print("Errores de validación:", form.errors)
            messages.error(request, f'Error al guardar: {form.errors.as_text()}')
            return redirect('calificaciones:listado') 
    else:
        # GET no se usa aquí porque el formulario está en el modal de la lista
        return redirect('calificaciones:listado')


@login_required
@analista_requerido
def calificacion_editar(request, pk):
    calificacion = get_object_or_404(Calificacion, pk=pk)
    
    if calificacion.estado not in ['BORRADOR', 'REVISION']:
        messages.warning(request, 'Solo se pueden editar calificaciones en Borrador o Revisión.')
        return redirect('calificaciones:detalle', pk=pk)
    
    if not (request.user.is_superuser or request.user.es_administrador()):
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
    """
    Calculadora: Montos -> Factores (División según Excel 3. Tipos de datos).
    """
    if request.method == 'POST':
        form = IngresoMontoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            total = data['monto_total_reparto']
            
            if total == 0:
                messages.error(request, "El monto total no puede ser cero.")
                return redirect('calificaciones:ingreso_monto')

            # Cálculo: Factor = Monto Parcial / Total
            f8 = (data['monto_f8_credito_idpc'] / total).quantize(Decimal("0.00000001"))
            f12 = (data['monto_f12_exento'] / total).quantize(Decimal("0.00000001"))
            
            if f8 > 1 or f12 > 1:
                messages.warning(request, "Advertencia: Algunos factores superan 1.0")

            calificacion = Calificacion(
                cliente=data['cliente'],
                anno=data['anno'],
                factor8=f8,
                factor12=f12,
                user=request.user,
                estado='BORRADOR',
                ingreso_montos=True
            )
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
    """
    Carga CSV alineada con '3.1 Archivo de carga.csv'.
    """
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
                    # Limpieza de datos (Coma a Punto para decimales)
                    def clean_dec(val):
                        if not val: return Decimal(0)
                        return Decimal(val.replace(',', '.'))
                    
                    # Parseo de fecha (DD-MM-AAAA)
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
                        
                        # Factores
                        factor8=clean_dec(row.get('Factor 8')),
                        factor9=clean_dec(row.get('Factor 9')),
                        # ... mapear resto ...
                        
                        user=request.user,
                        estado='BORRADOR',
                        ingreso_montos=False
                    )
                    
                    if hasattr(request.user, 'corredora') and request.user.corredora:
                        nuevo_obj.corredora = request.user.corredora
                        
                    nuevo_obj.save()
                    cont_exito += 1
                except Exception as e:
                    print(f"Error en fila CSV: {e}")
                    pass
            
            messages.success(request, f"Carga finalizada. {cont_exito} registros creados.")
            return redirect('calificaciones:listado')
    else:
        form = CargaMasivaFactoresForm()
    return render(request, 'calificaciones/carga_masiva.html', {'form': form})


@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def reporte_calificaciones_por_agente(request):
    """
    Reporte: Cantidad de calificaciones ingresadas por agentes de una corredora.
    """
    # Obtener corredora
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


# ============================================================================
# VISTAS DE CLIENTES (CRUD)
# ============================================================================

@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def clientes_lista(request):
    clientes = Cliente.objects.filter(activo=True).order_by('rut')
    return render(request, 'clientes/lista.html', {'clientes': clientes})


@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def cliente_detalle(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    return render(request, 'clientes/detalle.html', {'cliente': cliente})


@login_required
@analista_requerido
def cliente_crear(request):
    """
    Vista para crear clientes (Natural o Jurídico).
    Maneja el input 'tipo' para validar solo el formulario correspondiente.
    """
    # Valor por defecto para tipo
    tipo_seleccionado = 'natural' 

    if request.method == 'POST':
        tipo = request.POST.get('tipo', 'natural') # Obtener tipo del form
        tipo_seleccionado = tipo # Mantener selección en caso de error
        
        cliente_form = ClienteForm(request.POST)
        
        # Instanciar el formulario correcto según el tipo
        if tipo == 'natural':
            persona_form = PersonaNaturalForm(request.POST)
            # Deshabilitar validación del otro formulario
            persona_juridica_form = PersonaJuridicaForm() 
        else:
            persona_form = PersonaJuridicaForm(request.POST)
            persona_natural_form = PersonaNaturalForm()

        if cliente_form.is_valid() and persona_form.is_valid():
            try:
                cliente = cliente_form.save()
                persona = persona_form.save(commit=False)
                persona.cliente = cliente
                persona.save()
                messages.success(request, 'Cliente creado exitosamente.')
                return redirect('clientes:detalle', pk=cliente.pk)
            except Exception as e:
                messages.error(request, f'Error al guardar en base de datos: {str(e)}')
        else:
            # Mostrar errores en pantalla
            if not cliente_form.is_valid():
                messages.error(request, f"Error en Datos de Contacto: {cliente_form.errors.as_text()}")
            if not persona_form.is_valid():
                messages.error(request, f"Error en Datos Específicos: {persona_form.errors.as_text()}")
    else:
        cliente_form = ClienteForm()
        persona_natural_form = PersonaNaturalForm()
        persona_juridica_form = PersonaJuridicaForm()
        # En GET no hay 'persona_form' genérico, pasamos los específicos
        persona_form = None 

    context = {
        'cliente_form': cliente_form,
        'persona_natural_form': persona_natural_form if request.method == 'GET' else (persona_form if tipo_seleccionado == 'natural' else PersonaNaturalForm()),
        'persona_juridica_form': persona_juridica_form if request.method == 'GET' else (persona_form if tipo_seleccionado == 'juridica' else PersonaJuridicaForm()),
        'tipo_seleccionado': tipo_seleccionado, 
    }
    
    return render(request, 'clientes/form.html', context)


@login_required
@analista_requerido
def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    es_natural = cliente.es_persona_natural()
    
    if request.method == 'POST':
        cliente_form = ClienteForm(request.POST, instance=cliente)
        if es_natural:
            persona_form = PersonaNaturalForm(request.POST, instance=cliente.persona_natural)
        else:
            persona_form = PersonaJuridicaForm(request.POST, instance=cliente.persona_juridica)
        
        if cliente_form.is_valid() and persona_form.is_valid():
            cliente_form.save()
            persona_form.save()
            messages.success(request, 'Cliente actualizado.')
            return redirect('clientes:detalle', pk=pk)
    else:
        cliente_form = ClienteForm(instance=cliente)
        if es_natural:
            persona_form = PersonaNaturalForm(instance=cliente.persona_natural)
        else:
            persona_form = PersonaJuridicaForm(instance=cliente.persona_juridica)
    
    return render(request, 'clientes/form.html', {
        'cliente_form': cliente_form,
        'persona_form': persona_form,
        'es_natural': es_natural,
        'cliente': cliente,
    })


# ============================================================================
# VISTAS DE CORREDORAS (CRUD)
# ============================================================================

@login_required
@administrador_requerido
def corredoras_lista(request):
    corredoras = Corredora.objects.all().order_by('nombre')
    return render(request, 'corredoras/lista.html', {'corredoras': corredoras})


@login_required
@administrador_requerido
def corredora_detalle(request, pk):
    corredora = get_object_or_404(Corredora, pk=pk)
    return render(request, 'corredoras/detalle.html', {'corredora': corredora})


@login_required
@administrador_requerido
def corredora_crear(request):
    if request.method == 'POST':
        form = CorrederaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Corredora creada.')
            return redirect('corredoras:listado')
    else:
        form = CorrederaForm()
    return render(request, 'corredoras/form.html', {'form': form, 'form_title': 'Nueva Corredora'})


@login_required
@administrador_requerido
def corredora_editar(request, pk):
    corredora = get_object_or_404(Corredora, pk=pk)
    if request.method == 'POST':
        form = CorrederaForm(request.POST, instance=corredora)
        if form.is_valid():
            form.save()
            messages.success(request, 'Corredora actualizada.')
            return redirect('corredoras:detalle', pk=pk)
    else:
        form = CorrederaForm(instance=corredora)
    return render(request, 'corredoras/form.html', {'form': form, 'form_title': f'Editar {corredora.nombre}'})