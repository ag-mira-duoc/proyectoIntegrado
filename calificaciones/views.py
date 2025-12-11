"""
Vistas para la app calificaciones (CRUD, reportes, cálculos y cargas masivas)
"""
import csv
import io
import json
from decimal import Decimal
from datetime import datetime

from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import Calificacion, Cliente, Corredora, User, PersonaNatural, PersonaJuridica 
from .forms import (
    CalificacionForm, ClienteForm, PersonaNaturalForm, PersonaJuridicaForm, CorredoraForm   ,
    IngresoMontoForm, CargaMasivaFactoresForm
)
from .services import procesar_archivo_pdf
#from documentos.firebase_utils import subir_archivo_firebase

from usuarios.decorators import analista_requerido, administrador_requerido, rol_requerido

# ============================================================================
# HELPER: Contexto común para la lista (Evita duplicar código)
# ============================================================================
def get_lista_context(request):
    """Retorna el contexto base para lista.html con lógica de negocio corregida"""
    
    # --- 1. QuerySet Base y Seguridad de Visibilidad ---
    calificaciones = Calificacion.objects.select_related('cliente', 'user', 'corredora').all()
    
    es_privilegiado = (request.user.is_superuser or 
                       getattr(request.user, 'es_administrador', lambda: False)() or 
                       getattr(request.user, 'es_auditor', lambda: False)())
    
    # LÓGICA DE VISIBILIDAD:
    # Si es analista/corredor, SOLO ve calificaciones de SU corredora.
    if not es_privilegiado:
        if hasattr(request.user, 'corredora') and request.user.corredora:
            calificaciones = calificaciones.filter(corredora=request.user.corredora)
        else:
            calificaciones = calificaciones.filter(user=request.user)

    # --- 2. Aplicación de Filtros (Búsqueda) ---
    
    # A) Búsqueda por Texto
    search_query = request.GET.get('search', '').strip()
    if search_query:
        calificaciones = calificaciones.filter(instrumento__icontains=search_query)

    # B) Año
    anno = request.GET.get('anno')
    if anno:
        calificaciones = calificaciones.filter(anno=anno)

    # C) Mercado
    mercado = request.GET.get('mercado')
    if mercado:
        calificaciones = calificaciones.filter(mercado=mercado)

    # D) Origen (Usuario)
    origen = request.GET.get('origen')
    if origen:
        calificaciones = calificaciones.filter(user__id=origen)


    # --- 3. Generación de Listas para los Desplegables ---
    
    # Lógica para llenar el select de "Origen":
    if es_privilegiado:
        # Admins ven a todos los usuarios activos
        usuarios_list = User.objects.filter(is_active=True).order_by('apellido')
    elif hasattr(request.user, 'corredora') and request.user.corredora:
        # Analistas SOLO ven usuarios de SU MISMA corredora
        usuarios_list = User.objects.filter(
            is_active=True, 
            corredora=request.user.corredora
        ).order_by('apellido')
    else:
        usuarios_list = User.objects.filter(pk=request.user.pk)

    # Orden y Paginación final
    calificaciones = calificaciones.order_by('-anno', '-created_at')
    paginator = Paginator(calificaciones, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    clientes_list = Cliente.objects.filter(activo=True)
    years = range(2020, datetime.now().year + 2)

    return {
        'calificaciones': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'years': years,
        'clientes_list': clientes_list,
        'usuarios_list': usuarios_list, # Ahora contiene la lista filtrada correctamente
        'es_privilegiado': es_privilegiado,
    }


# ============================================================================
# VISTAS DE CALIFICACIONES (CRUD + PROCESOS)
# ============================================================================

@login_required
@rol_requerido('Administradores', 'Analistas', 'Auditores')
def calificaciones_lista(request):
    context = get_lista_context(request)
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
        rut_ingresado = request.POST.get('rut_cliente')
        nombre_instrumento = request.POST.get('instrumento')
        # El input type="date" siempre envía la fecha como 'YYYY-MM-DD'
        fecha_pago_raw = request.POST.get('fecha_pago') 
        
        if not rut_ingresado or not nombre_instrumento:
            messages.error(request, 'El RUT y el Instrumento son obligatorios.')
            return redirect('calificaciones:listado')

        try:
            with transaction.atomic():
                # 1. BUSCAR O CREAR CLIENTE
                cliente = Cliente.objects.filter(rut=rut_ingresado).first()
                if not cliente:
                    cliente = Cliente.objects.create(rut=rut_ingresado, activo=True)
                    PersonaJuridica.objects.create(
                        cliente=cliente, 
                        razon_social=nombre_instrumento,
                        domicilio_tributario="Sin Domicilio",
                        giro="Sin Giro"
                    )
                
                # 2. PREPARAR DATOS
                data = request.POST.copy()
                data['cliente'] = cliente.id
                
                data['fecha_pago'] = fecha_pago_raw 

                form = CalificacionForm(data, user=request.user)
                
                if form.is_valid():
                    calificacion = form.save(commit=False)
                    calificacion.user = request.user
                    calificacion.cliente = cliente
                    
                    if hasattr(request.user, 'corredora') and request.user.corredora:
                        calificacion.corredora = request.user.corredora
                    
                    calificacion.save()
                    messages.success(request, f'Calificación creada para {nombre_instrumento}.')
                    return redirect('calificaciones:listado')
                else:
                    messages.error(request, f'Error al guardar: {form.errors.as_text()}')
                    return redirect('calificaciones:listado')

        except Exception as e:
            messages.error(request, f'Error crítico: {str(e)}')
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

@login_required
@require_POST
def procesar_pdf_ajax(request):
    """
    Recibe un archivo PDF, llama a Docling y devuelve JSON para la previsualización.
    """
    if 'archivo_pdf' not in request.FILES:
        return JsonResponse({'error': 'No se recibió ningún archivo PDF.'}, status=400)

    archivo = request.FILES['archivo_pdf']
    
    try:
        # Llamamos al servicio actualizado
        datos_json = procesar_archivo_pdf(archivo)
        
        if 'error' in datos_json:
            return JsonResponse({'error': datos_json['error']}, status=500)
            
        return JsonResponse(datos_json)

    except Exception as e:
        return JsonResponse({'error': f"Error interno: {str(e)}"}, status=500)


@login_required
@require_POST
def guardar_lote_ajax(request):
    """
    Recibe el JSON confirmado por el usuario y guarda los registros en BD.
    """
    try:
        data = json.loads(request.body)
        registros_guardados = 0
        errores = []

        for item in data:
            try:
                # 1. Gestionar Cliente (Buscar o Crear)
                rut_cliente = item.get('rut_emisor') # Si Docling lo extrajo
                nombre_cliente = item.get('instrumento') # Usamos instrumento como fallback de nombre
                
                # Buscamos por nombre si no hay RUT, o creamos uno dummy
                cliente = None
                if nombre_cliente:
                    cliente = Cliente.objects.filter(persona_juridica__razon_social__icontains=nombre_cliente).first()
                
                if not cliente:
                    # Crear cliente temporal o asignar a "Sin Clasificar"
                    # Por ahora requerimos que exista o lo creamos básico
                    cliente, created = Cliente.objects.get_or_create(
                        rut='99.999.999-9', # Rut dummy si no se extrajo
                        defaults={'activo': True}
                    )
                    if created:
                        PersonaJuridica.objects.create(cliente=cliente, razon_social=nombre_cliente or "Cliente Nuevo")

                # 2. Crear Calificación
                fecha_str = item.get('fecha_pago')
                fecha_obj = None
                if fecha_str:
                    try:
                        fecha_obj = datetime.strptime(fecha_str, '%d/%m/%Y').date()
                    except:
                        fecha_obj = timezone.now().date()

                nueva_calificacion = Calificacion(
                    user=request.user,
                    cliente=cliente,
                    anno=item.get('ejercicio') or datetime.now().year,
                    mercado=item.get('mercado', 'AC'),
                    instrumento=item.get('instrumento') or "Sin Nombre",
                    fecha_pago=fecha_obj,
                    secuencia_evento=item.get('secuencia'),
                    
                    isfut=(item.get('acogidoISFUT') == 'S'),
                    #origen=item.get('origen'),
                    estado='BORRADOR' # Siempre entran como borrador para revisión final
                )
                
                # Asignar corredora si corresponde
                if hasattr(request.user, 'corredora') and request.user.corredora:
                    nueva_calificacion.corredora = request.user.corredora

                # 3. Asignar Factores 8-37
                factores = item.get('factores', {})
                for i in range(8, 38):
                    k = str(i)
                    if k in factores:
                        val_str = factores[k].get('valor_decimal', '0')
                        val_dec = Decimal(val_str)
                        setattr(nueva_calificacion, f'factor{i}', val_dec)

                nueva_calificacion.save()
                registros_guardados += 1

            except Exception as e_row:
                errores.append(f"Fila {item.get('instrumento')}: {str(e_row)}")

        if registros_guardados > 0:
            return JsonResponse({'mensaje': f'{registros_guardados} registros guardados exitosamente.'})
        else:
            msg_error = "No se guardó nada."
            if errores: msg_error += f" Errores: {', '.join(errores)}"
            return JsonResponse({'error': msg_error}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
        form = CorredoraForm(request.POST)
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