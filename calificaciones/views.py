"""
Vistas para la app calificaciones (CRUD, reportes, cálculos y cargas masivas)
"""
import csv
import io
import json
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta

from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, F, Case, When, FloatField
from django.db.models.functions import TruncWeek, TruncMonth, ExtractWeekDay
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import Calificacion, Cliente, Corredora, User, PersonaNatural, PersonaJuridica 
from .forms import (
    CalificacionForm, ClienteForm, PersonaNaturalForm, PersonaJuridicaForm, CorredoraForm   ,
    IngresoMontoForm, CargaMasivaFactoresForm
)

from documentos.services import gestionar_carga_documento 
from documentos.models import Documento

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
    if not es_privilegiado:
        if hasattr(request.user, 'corredora') and request.user.corredora:
            calificaciones = calificaciones.filter(corredora=request.user.corredora)
        else:
            calificaciones = calificaciones.filter(user=request.user)

    # --- 2. Aplicación de Filtros (Búsqueda) ---
    search_query = request.GET.get('search', '').strip()
    if search_query:
        calificaciones = calificaciones.filter(instrumento__icontains=search_query)

    anno = request.GET.get('anno')
    if anno:
        calificaciones = calificaciones.filter(anno=anno)

    mercado = request.GET.get('mercado')
    if mercado:
        calificaciones = calificaciones.filter(mercado=mercado)

    origen = request.GET.get('origen')
    if origen:
        calificaciones = calificaciones.filter(user__id=origen)

    # --- 3. Generación de Listas para los Desplegables ---
    if es_privilegiado:
        usuarios_list = User.objects.filter(is_active=True).order_by('apellido')
    elif hasattr(request.user, 'corredora') and request.user.corredora:
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
        'usuarios_list': usuarios_list,
        'es_privilegiado': es_privilegiado,
    }

from decimal import Decimal, ROUND_HALF_UP

def procesar_montos_a_factores(data):
    # Si no es modo monto, retornar data original
    if data.get('modo_ingreso') != 'monto':
        return data

    data_procesada = data.copy()
    PRECISION = Decimal("0.00000001")
    rango_completo = range(8, 38)
    
    # -------------------------------------------------------
    # 1. Sumar TODOS los montos ingresados
    # -------------------------------------------------------
    suma_montos = Decimal(0)
    for i in rango_completo:
        key_monto = f'monto_factor{i}'
        valor = data.get(key_monto)
        if valor and str(valor).strip():
            suma_montos += Decimal(str(valor))
            
    # Si la suma es 0, limpiamos y salimos
    if suma_montos == 0:
        for i in rango_completo:
            data_procesada[f'factor{i}'] = 0
        return data_procesada

    # -------------------------------------------------------
    # 2. Calcular factores preliminares y guardarlos
    # -------------------------------------------------------
    suma_factores_calculados = Decimal(0)
    mayor_factor_valor = Decimal(-1)
    mayor_factor_index = -1

    for i in rango_completo:
        key_monto = f'monto_factor{i}'
        key_destino = f'factor{i}'
        val_original = data.get(key_monto)
        
        factor_redondeado = Decimal(0)

        if val_original and str(val_original).strip():
            monto = Decimal(str(val_original))
            # Cálculo: Monto / SumaTotal
            factor_raw = monto / suma_montos
            # Redondeo individual
            factor_redondeado = factor_raw.quantize(PRECISION, rounding=ROUND_HALF_UP)

        data_procesada[key_destino] = factor_redondeado
        suma_factores_calculados += factor_redondeado

        # Rastreamos cuál es el factor más grande para ajustar diferencias ahí
        if factor_redondeado > mayor_factor_valor:
            mayor_factor_valor = factor_redondeado
            mayor_factor_index = i

    # -------------------------------------------------------
    # 3. EL CUADRE FINAL (Ajuste de residuos)
    # -------------------------------------------------------
    # Verificamos si la suma difiere de 1.00000000
    objetivo = Decimal("1.00000000")
    diferencia = objetivo - suma_factores_calculados

    # Si hay diferencia (ej: 0.00000001) y encontramos un factor donde ajustarla
    if diferencia != 0 and mayor_factor_index != -1:
        key_ajuste = f'factor{mayor_factor_index}'
        valor_actual = data_procesada[key_ajuste]
        
        # Le sumamos (o restamos) la diferencia al factor más grande
        data_procesada[key_ajuste] = valor_actual + diferencia
        
        # (Opcional) Print para debug
        print(f"DEBUG: Ajuste de cuadre aplicado en F-{mayor_factor_index}. Diff: {diferencia}")

    return data_procesada

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
        fecha_pago_raw = request.POST.get('fecha_pago')

        if not rut_ingresado or not nombre_instrumento:
            messages.error(request, 'El RUT y el Instrumento son obligatorios.')
            return redirect('calificaciones:listado')

        try:
            with transaction.atomic():
                cliente = Cliente.objects.filter(rut=rut_ingresado).first()
                if not cliente:
                    print("   Creando cliente nuevo...")
                    cliente = Cliente.objects.create(rut=rut_ingresado, activo=True)
                    PersonaJuridica.objects.create(
                        cliente=cliente, 
                        razon_social=nombre_instrumento,
                        domicilio_tributario="Sin Domicilio",
                        giro="Sin Giro"
                    )
                
                # Copia y Procesamiento
                data = request.POST.copy()
                data = procesar_montos_a_factores(data)
                
                # Completar datos
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
                    errores = form.errors.as_text()
                    
                    messages.error(request, f'Error al guardar: {errores}')
                    return redirect('calificaciones:listado')

        except Exception as e:
            print(f"ERROR CRITICO EXCEPTION: {str(e)}")
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


# ============================================================================
# --- CORRECCIÓN 2: Vista procesar_pdf_ajax actualizada ---
# ============================================================================
@login_required
@require_POST
@login_required
@require_POST
def procesar_pdf_ajax(request):
    if 'archivo_pdf' not in request.FILES:
        return JsonResponse({'error': 'No se recibió archivo.'}, status=400)

    archivo = request.FILES['archivo_pdf']
    try:
        # 1. Sube a Azure y crea el registro Documento inmediatamente
        doc_creado = gestionar_carga_documento(
            archivo_memoria=archivo,
            usuario=request.user,
            tipo_doc='CERT_70'
        )
        
        # 2. Obtenemos los datos extraídos por Docling
        datos = doc_creado.datos_extraidos or {}
        
        # 3. ¡IMPORTANTE! Inyectamos el ID del documento en la respuesta
        datos['documento_id'] = doc_creado.id 
        #datos['url_azure'] = doc_creado.url_firebase
        
        return JsonResponse(datos)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
                # 1. Gestionar Cliente
                rut_cliente = item.get('rut_emisor')
                nombre_cliente = item.get('instrumento')
                
                cliente = None
                if nombre_cliente:
                    cliente = Cliente.objects.filter(persona_juridica__razon_social__icontains=nombre_cliente).first()
                
                if not cliente:
                    cliente, created = Cliente.objects.get_or_create(
                        rut='99.999.999-9',
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
                    estado='BORRADOR'
                )
                
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
                
                # --- LÓGICA DE VINCULACIÓN ---
                doc_id = item.get('documento_id')
                if doc_id:
                    try:
                        # Buscamos el documento que subimos en la previsualización
                        documento = Documento.objects.get(pk=doc_id, usuario_carga=request.user)
                        
                        # Lo vinculamos a la calificación recién creada
                        documento.calificacion = nueva_calificacion
                        documento.estado = 'COMPLETADO'
                        documento.save()
                    except Documento.DoesNotExist:
                        pass

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
    tipo_seleccionado = 'natural' 

    if request.method == 'POST':
        tipo = request.POST.get('tipo', 'natural')
        tipo_seleccionado = tipo
        
        cliente_form = ClienteForm(request.POST)
        
        if tipo == 'natural':
            persona_form = PersonaNaturalForm(request.POST)
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
            if not cliente_form.is_valid():
                messages.error(request, f"Error en Datos de Contacto: {cliente_form.errors.as_text()}")
            if not persona_form.is_valid():
                messages.error(request, f"Error en Datos Específicos: {persona_form.errors.as_text()}")
    else:
        cliente_form = ClienteForm()
        persona_natural_form = PersonaNaturalForm()
        persona_juridica_form = PersonaJuridicaForm()
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
    
    context = {
        'cliente_form': cliente_form,
        'persona_form': persona_form, 
        'es_natural': es_natural,     
        'cliente': cliente,
        'edit_mode': True             
    }

    return render(request, 'clientes/form.html', context)


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
        form = CorredoraForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Corredora creada exitosamente.')
            return redirect('corredoras:listado')
        else:
            messages.error(request, 'Error al crear la corredora. Verifique los datos.')
    else:
        form = CorredoraForm()
    
    return render(request, 'corredoras/form.html', {
        'form': form, 
        'form_title': 'Nueva Corredora'
    })


@login_required
@administrador_requerido
def corredora_editar(request, pk):
    corredora = get_object_or_404(Corredora, pk=pk)
    
    if request.method == 'POST':
        form = CorredoraForm(request.POST, instance=corredora)
        if form.is_valid():
            form.save()
            messages.success(request, 'Corredora actualizada exitosamente.')
            return redirect('corredoras:detalle', pk=pk)
        else:
            messages.error(request, 'Error al actualizar. Verifique los datos.')
    else:
        form = CorredoraForm(instance=corredora)
    
    return render(request, 'corredoras/form.html', {
        'form': form, 
        'form_title': f'Editar {corredora.nombre}'
    })

@login_required
@administrador_requerido
def reportes_admin(request):
    """
    Vista de reportes administrativos con 8 reportes diferentes.
    Solo accesible para administradores.
    """
    
    # ==========================================
    # REPORTE 1: Top 10 Clientes
    # ==========================================
    top_clientes = Calificacion.objects.values(
        'cliente__rut'
    ).annotate(
        total=Count('id'),
        aprobadas=Count('id', filter=Q(estado='APROBADA')),
        en_revision=Count('id', filter=Q(estado='REVISION'))
    ).order_by('-total')[:10]
    
    # ==========================================
    # REPORTE 2: Distribución por Estado
    # ==========================================
    distribucion_estados = []
    for estado_code, estado_display in Calificacion.ESTADOS:
        count = Calificacion.objects.filter(estado=estado_code).count()
        if count > 0:
            distribucion_estados.append({
                'estado': estado_display,
                'cantidad': count
            })
    
    # ==========================================
    # REPORTE 3: Tendencia Semanal (últimas 8 semanas)
    # ==========================================
    fecha_inicio_tendencia = datetime.now() - timedelta(weeks=8)
    tendencia_semanal = Calificacion.objects.filter(
        created_at__gte=fecha_inicio_tendencia
    ).annotate(
        semana=TruncWeek('created_at')
    ).values('semana').annotate(
        cantidad=Count('id')
    ).order_by('semana')
    
    # ==========================================
    # REPORTE 4: Top 10 Corredoras
    # ==========================================
    top_corredoras = Calificacion.objects.values(
        'corredora__nombre'
    ).annotate(
        total=Count('id'),
        aprobadas=Count('id', filter=Q(estado='APROBADA'))
    ).order_by('-total')[:10]
    
    # ==========================================
    # REPORTE 5: Productividad por Analista (Top 10)
    # ==========================================
    productividad_analistas = Calificacion.objects.values(
        'user__nombre', 'user__apellido', 'user__email'
    ).annotate(
        total=Count('id'),
        aprobadas=Count('id', filter=Q(estado='APROBADA')),
        en_revision=Count('id', filter=Q(estado='REVISION')),
        borradores=Count('id', filter=Q(estado='BORRADOR'))
    ).order_by('-total')[:10]
    
    # ==========================================
    # REPORTE 6: Tasa de Aprobación por Corredora
    # ==========================================
    tasa_aprobacion_corredoras = Calificacion.objects.values(
        'corredora__nombre'
    ).annotate(
        total=Count('id'),
        aprobadas=Count('id', filter=Q(estado='APROBADA'))
    ).filter(total__gte=5).order_by('-total')[:10]  # Mínimo 5 calificaciones
    
    # Calcular tasa de aprobación manualmente (para evitar división por cero)
    for item in tasa_aprobacion_corredoras:
        if item['total'] > 0:
            item['tasa'] = round((item['aprobadas'] / item['total']) * 100, 1)
        else:
            item['tasa'] = 0
    
    # ==========================================
    # REPORTE 7: Actividad por Día de la Semana
    # ==========================================
    actividad_semanal = Calificacion.objects.annotate(
        dia=ExtractWeekDay('created_at')  # 1=Domingo, 2=Lunes, ..., 7=Sábado
    ).values('dia').annotate(
        cantidad=Count('id')
    ).order_by('dia')
    
    # Mapear números a nombres de días
    dias_nombres = {
        1: 'Domingo',
        2: 'Lunes',
        3: 'Martes',
        4: 'Miércoles',
        5: 'Jueves',
        6: 'Viernes',
        7: 'Sábado'
    }
    
    actividad_semanal_formateada = []
    for item in actividad_semanal:
        actividad_semanal_formateada.append({
            'dia': dias_nombres.get(item['dia'], 'Desconocido'),
            'dia_num': item['dia'],
            'cantidad': item['cantidad']
        })
    
    # ==========================================
    # REPORTE 8: Comparación Mes Actual vs Anterior
    # ==========================================
    ahora = datetime.now()
    
    # Mes actual
    mes_actual_stats = Calificacion.objects.filter(
        created_at__month=ahora.month,
        created_at__year=ahora.year
    ).aggregate(
        total=Count('id'),
        aprobadas=Count('id', filter=Q(estado='APROBADA')),
        en_revision=Count('id', filter=Q(estado='REVISION'))
    )
    
    # Mes anterior
    if ahora.month == 1:
        mes_anterior_num = 12
        año_anterior = ahora.year - 1
    else:
        mes_anterior_num = ahora.month - 1
        año_anterior = ahora.year
    
    mes_anterior_stats = Calificacion.objects.filter(
        created_at__month=mes_anterior_num,
        created_at__year=año_anterior
    ).aggregate(
        total=Count('id'),
        aprobadas=Count('id', filter=Q(estado='APROBADA')),
        en_revision=Count('id', filter=Q(estado='REVISION'))
    )
    
    # Calcular crecimiento
    def calcular_crecimiento(actual, anterior):
        if anterior and anterior > 0:
            return round(((actual - anterior) / anterior) * 100, 1)
        elif actual > 0:
            return 100.0  # Si no había nada antes y ahora hay, es 100% de crecimiento
        return 0.0
    
    crecimiento_total = calcular_crecimiento(
        mes_actual_stats.get('total', 0),
        mes_anterior_stats.get('total', 0)
    )
    
    crecimiento_aprobadas = calcular_crecimiento(
        mes_actual_stats.get('aprobadas', 0),
        mes_anterior_stats.get('aprobadas', 0)
    )
    
    # Nombres de meses
    meses_nombres = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    
    mes_actual_nombre = meses_nombres.get(ahora.month)
    mes_anterior_nombre = meses_nombres.get(mes_anterior_num)
    
    # ==========================================
    # ESTADÍSTICAS GENERALES
    # ==========================================
    total_calificaciones = Calificacion.objects.count()
    total_aprobadas = Calificacion.objects.filter(estado='APROBADA').count()
    total_revision = Calificacion.objects.filter(estado='REVISION').count()
    total_clientes = Cliente.objects.filter(activo=True).count()
    
    context = {
        # Reportes
        'top_clientes': top_clientes,
        'distribucion_estados': distribucion_estados,
        'tendencia_semanal': tendencia_semanal,
        'top_corredoras': top_corredoras,
        'productividad_analistas': productividad_analistas,
        'tasa_aprobacion_corredoras': tasa_aprobacion_corredoras,
        'actividad_semanal': actividad_semanal_formateada,
        'mes_actual_stats': mes_actual_stats,
        'mes_anterior_stats': mes_anterior_stats,
        'crecimiento_total': crecimiento_total,
        'crecimiento_aprobadas': crecimiento_aprobadas,
        'mes_actual_nombre': mes_actual_nombre,
        'mes_anterior_nombre': mes_anterior_nombre,
        
        # Estadísticas generales
        'total_calificaciones': total_calificaciones,
        'total_aprobadas': total_aprobadas,
        'total_revision': total_revision,
        'total_clientes': total_clientes,
    }
    
    return render(request, 'calificaciones/reportes_admin.html', context)

@login_required
@administrador_requerido
def descargar_reportes_excel(request):
    """
    Genera un archivo Excel con todos los reportes administrativos.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    
    wb = Workbook()
    
    # ==========================================
    # HOJA 1: Top 10 Clientes
    # ==========================================
    ws1 = wb.active
    ws1.title = "Top Clientes"
    
    # Título
    ws1['A1'] = 'Top 10 Clientes con Más Calificaciones'
    ws1['A1'].font = Font(bold=True, size=14)
    ws1.merge_cells('A1:D1')
    
    # Encabezados
    headers = ['#', 'RUT Cliente', 'Total', 'Aprobadas', 'En Revisión']
    for col, header in enumerate(headers, 1):
        cell = ws1.cell(row=3, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF")
    
    # Datos
    top_clientes = Calificacion.objects.values(
        'cliente__rut'
    ).annotate(
        total=Count('id'),
        aprobadas=Count('id', filter=Q(estado='APROBADA')),
        en_revision=Count('id', filter=Q(estado='REVISION'))
    ).order_by('-total')[:10]
    
    for idx, item in enumerate(top_clientes, 1):
        ws1.cell(row=3+idx, column=1, value=idx)
        ws1.cell(row=3+idx, column=2, value=item['cliente__rut'] or 'Sin RUT')
        ws1.cell(row=3+idx, column=3, value=item['total'])
        ws1.cell(row=3+idx, column=4, value=item['aprobadas'])
        ws1.cell(row=3+idx, column=5, value=item['en_revision'])
    
    # Ajustar ancho de columnas
    for col in range(1, 6):
        ws1.column_dimensions[get_column_letter(col)].width = 20
    
    # ==========================================
    # HOJA 2: Distribución por Estado
    # ==========================================
    ws2 = wb.create_sheet("Distribución Estados")
    
    ws2['A1'] = 'Distribución de Calificaciones por Estado'
    ws2['A1'].font = Font(bold=True, size=14)
    ws2.merge_cells('A1:C1')
    
    headers = ['Estado', 'Cantidad', 'Porcentaje']
    for col, header in enumerate(headers, 1):
        cell = ws2.cell(row=3, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF")
    
    total_calificaciones = Calificacion.objects.count()
    row = 4
    for estado_code, estado_display in Calificacion.ESTADOS:
        count = Calificacion.objects.filter(estado=estado_code).count()
        if count > 0:
            porcentaje = (count / total_calificaciones * 100) if total_calificaciones > 0 else 0
            ws2.cell(row=row, column=1, value=estado_display)
            ws2.cell(row=row, column=2, value=count)
            ws2.cell(row=row, column=3, value=f"{porcentaje:.1f}%")
            row += 1
    
    for col in range(1, 4):
        ws2.column_dimensions[get_column_letter(col)].width = 20
    
    # ==========================================
    # HOJA 3: Tendencia Semanal
    # ==========================================
    ws3 = wb.create_sheet("Tendencia Semanal")
    
    ws3['A1'] = 'Tendencia de Calificaciones - Últimas 8 Semanas'
    ws3['A1'].font = Font(bold=True, size=14)
    ws3.merge_cells('A1:B1')
    
    headers = ['Semana', 'Cantidad']
    for col, header in enumerate(headers, 1):
        cell = ws3.cell(row=3, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="FFC000", end_color="FFC000", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF")
    
    fecha_inicio_tendencia = datetime.now() - timedelta(weeks=8)
    tendencia_semanal = Calificacion.objects.filter(
        created_at__gte=fecha_inicio_tendencia
    ).annotate(
        semana=TruncWeek('created_at')
    ).values('semana').annotate(
        cantidad=Count('id')
    ).order_by('semana')
    
    for idx, item in enumerate(tendencia_semanal, 4):
        ws3.cell(row=idx, column=1, value=item['semana'].strftime('%d/%m/%Y'))
        ws3.cell(row=idx, column=2, value=item['cantidad'])
    
    for col in range(1, 3):
        ws3.column_dimensions[get_column_letter(col)].width = 20
    
    # ==========================================
    # HOJA 4: Top Corredoras
    # ==========================================
    ws4 = wb.create_sheet("Top Corredoras")
    
    ws4['A1'] = 'Top 10 Corredoras Más Activas'
    ws4['A1'].font = Font(bold=True, size=14)
    ws4.merge_cells('A1:D1')
    
    headers = ['#', 'Corredora', 'Total', 'Aprobadas']
    for col, header in enumerate(headers, 1):
        cell = ws4.cell(row=3, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
        cell.font = Font(bold=True)
    
    top_corredoras = Calificacion.objects.values(
        'corredora__nombre'
    ).annotate(
        total=Count('id'),
        aprobadas=Count('id', filter=Q(estado='APROBADA'))
    ).order_by('-total')[:10]
    
    for idx, item in enumerate(top_corredoras, 1):
        ws4.cell(row=3+idx, column=1, value=idx)
        ws4.cell(row=3+idx, column=2, value=item['corredora__nombre'] or 'Sin Corredora')
        ws4.cell(row=3+idx, column=3, value=item['total'])
        ws4.cell(row=3+idx, column=4, value=item['aprobadas'])
    
    for col in range(1, 5):
        ws4.column_dimensions[get_column_letter(col)].width = 25
    
    # ==========================================
    # HOJA 5: Productividad Analistas
    # ==========================================
    ws5 = wb.create_sheet("Productividad Analistas")
    
    ws5['A1'] = 'Top 10 Analistas Más Productivos'
    ws5['A1'].font = Font(bold=True, size=14)
    ws5.merge_cells('A1:F1')
    
    headers = ['#', 'Nombre', 'Email', 'Total', 'Aprobadas', '% Aprobación']
    for col, header in enumerate(headers, 1):
        cell = ws5.cell(row=3, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="5B9BD5", end_color="5B9BD5", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF")
    
    productividad_analistas = Calificacion.objects.values(
        'user__nombre', 'user__apellido', 'user__email'
    ).annotate(
        total=Count('id'),
        aprobadas=Count('id', filter=Q(estado='APROBADA'))
    ).order_by('-total')[:10]
    
    for idx, item in enumerate(productividad_analistas, 1):
        nombre_completo = f"{item['user__nombre']} {item['user__apellido']}"
        porcentaje = (item['aprobadas'] / item['total'] * 100) if item['total'] > 0 else 0
        
        ws5.cell(row=3+idx, column=1, value=idx)
        ws5.cell(row=3+idx, column=2, value=nombre_completo)
        ws5.cell(row=3+idx, column=3, value=item['user__email'])
        ws5.cell(row=3+idx, column=4, value=item['total'])
        ws5.cell(row=3+idx, column=5, value=item['aprobadas'])
        ws5.cell(row=3+idx, column=6, value=f"{porcentaje:.1f}%")
    
    for col in range(1, 7):
        ws5.column_dimensions[get_column_letter(col)].width = 22
    
    # ==========================================
    # HOJA 6: Actividad por Día de Semana
    # ==========================================
    ws6 = wb.create_sheet("Actividad Semanal")
    
    ws6['A1'] = 'Actividad por Día de la Semana'
    ws6['A1'].font = Font(bold=True, size=14)
    ws6.merge_cells('A1:B1')
    
    headers = ['Día', 'Cantidad']
    for col, header in enumerate(headers, 1):
        cell = ws6.cell(row=3, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="44546A", end_color="44546A", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF")
    
    actividad_semanal = Calificacion.objects.annotate(
        dia=ExtractWeekDay('created_at')
    ).values('dia').annotate(
        cantidad=Count('id')
    ).order_by('dia')
    
    dias_nombres = {
        1: 'Domingo', 2: 'Lunes', 3: 'Martes', 4: 'Miércoles',
        5: 'Jueves', 6: 'Viernes', 7: 'Sábado'
    }
    
    for item in actividad_semanal:
        dia_num = item['dia']
        idx = dia_num + 3
        ws6.cell(row=idx, column=1, value=dias_nombres.get(dia_num, 'Desconocido'))
        ws6.cell(row=idx, column=2, value=item['cantidad'])
    
    for col in range(1, 3):
        ws6.column_dimensions[get_column_letter(col)].width = 20
    
    # ==========================================
    # HOJA 7: Comparación Mensual
    # ==========================================
    ws7 = wb.create_sheet("Comparación Mensual")
    
    ws7['A1'] = 'Comparación Mes Actual vs Mes Anterior'
    ws7['A1'].font = Font(bold=True, size=14)
    ws7.merge_cells('A1:D1')
    
    headers = ['Métrica', 'Mes Actual', 'Mes Anterior', 'Crecimiento']
    for col, header in enumerate(headers, 1):
        cell = ws7.cell(row=3, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        cell.font = Font(bold=True, color="FFFFFF")
    
    ahora = datetime.now()
    
    mes_actual_stats = Calificacion.objects.filter(
        created_at__month=ahora.month,
        created_at__year=ahora.year
    ).aggregate(
        total=Count('id'),
        aprobadas=Count('id', filter=Q(estado='APROBADA'))
    )
    
    if ahora.month == 1:
        mes_anterior_num = 12
        año_anterior = ahora.year - 1
    else:
        mes_anterior_num = ahora.month - 1
        año_anterior = ahora.year
    
    mes_anterior_stats = Calificacion.objects.filter(
        created_at__month=mes_anterior_num,
        created_at__year=año_anterior
    ).aggregate(
        total=Count('id'),
        aprobadas=Count('id', filter=Q(estado='APROBADA'))
    )
    
    # Total
    actual_total = mes_actual_stats.get('total', 0)
    anterior_total = mes_anterior_stats.get('total', 0)
    crecimiento_total = ((actual_total - anterior_total) / anterior_total * 100) if anterior_total > 0 else 0
    
    ws7.cell(row=4, column=1, value='Total Calificaciones')
    ws7.cell(row=4, column=2, value=actual_total)
    ws7.cell(row=4, column=3, value=anterior_total)
    ws7.cell(row=4, column=4, value=f"{crecimiento_total:+.1f}%")
    
    # Aprobadas
    actual_aprobadas = mes_actual_stats.get('aprobadas', 0)
    anterior_aprobadas = mes_anterior_stats.get('aprobadas', 0)
    crecimiento_aprobadas = ((actual_aprobadas - anterior_aprobadas) / anterior_aprobadas * 100) if anterior_aprobadas > 0 else 0
    
    ws7.cell(row=5, column=1, value='Aprobadas')
    ws7.cell(row=5, column=2, value=actual_aprobadas)
    ws7.cell(row=5, column=3, value=anterior_aprobadas)
    ws7.cell(row=5, column=4, value=f"{crecimiento_aprobadas:+.1f}%")
    
    for col in range(1, 5):
        ws7.column_dimensions[get_column_letter(col)].width = 22
    
    # ==========================================
    # GENERAR RESPUESTA HTTP
    # ==========================================
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="reportes_admin_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    
    wb.save(response)
    return response