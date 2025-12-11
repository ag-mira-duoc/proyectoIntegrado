from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from calificaciones.models import Calificacion
from auditoria.models import LogAuditoria
import json
from decimal import Decimal
from datetime import date, datetime

def serializar(data):
    if isinstance(data, dict):
        return {k: serializar(v) for k, v in data.items()}
    if isinstance(data, (Decimal, date, datetime)):
        return str(data)
    return data

@receiver(pre_save, sender=Calificacion)
def capturar_estado_anterior(sender, instance, **kwargs):
    if instance.pk:
        try:
            actual = Calificacion.objects.get(pk=instance.pk)
            instance._estado_anterior = model_to_dict(actual)
        except Calificacion.DoesNotExist:
            instance._estado_anterior = {}
    else:
        instance._estado_anterior = {}

@receiver(post_save, sender=Calificacion)
def auditar_calificacion_save(sender, instance, created, **kwargs):
    accion = 'CREATE' if created else 'UPDATE'
    usuario_responsable = getattr(instance, 'user', None)

    estado_actual = model_to_dict(instance)
    
    valores_anteriores = {}
    valores_nuevos = {}

    if created:
        valores_nuevos = serializar(estado_actual)
        valores_anteriores = None
    else:
        estado_anterior = getattr(instance, '_estado_anterior', {})
        
        for campo, valor_nuevo in estado_actual.items():
            if campo in ['_state', 'user']: 
                continue
            
            valor_antiguo = estado_anterior.get(campo)

            val_ant_str = str(valor_antiguo) if valor_antiguo is not None else ''
            val_nue_str = str(valor_nuevo) if valor_nuevo is not None else ''

            if val_ant_str != val_nue_str:
                valores_anteriores[campo] = serializar(valor_antiguo)
                valores_nuevos[campo] = serializar(valor_nuevo)

    if created or valores_nuevos:
        LogAuditoria.objects.create(
            user=usuario_responsable,
            accion=accion,
            tabla_afectada='Calificacion',
            registro_id=instance.id,
            detalle=f"Operación {accion} en calificación {instance}",
            valores_anteriores=valores_anteriores,
            valores_nuevos=valores_nuevos
        )

@receiver(post_delete, sender=Calificacion)
def auditar_calificacion_delete(sender, instance, **kwargs):
    """
    Registra eliminación guardando el estado final como 'valores_anteriores'.
    """
    estado_final = model_to_dict(instance)
    
    LogAuditoria.objects.create(
        user=instance.user,
        accion='DELETE',
        tabla_afectada='Calificacion',
        registro_id=instance.id,
        detalle=f"Eliminación de calificación: {instance}",
        valores_anteriores=serializar(estado_final),
        valores_nuevos=None
    )