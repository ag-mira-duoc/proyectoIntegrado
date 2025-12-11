from django.db import models
from django.contrib.postgres.fields import JSONField
from django.db.models import JSONField
from usuarios.models import User
from calificaciones.models import Calificacion
from django.core.exceptions import ValidationError

class LogAuditoria(models.Model):
    ACCIONES = [
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
        ('LOGIN', 'Inicio de Sesión'),
        ('LOGOUT', 'Cierre de Sesión'),
    ]

    # Relaciones y Datos
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=20, choices=ACCIONES)
    
    # Identificación del objeto afectado (Flexible y Opcional)
    tabla_afectada = models.CharField(max_length=100, null=True, blank=True)
    registro_id = models.IntegerField(null=True, blank=True)
    
    # Detalle y Trazabilidad
    detalle = models.TextField()
    valores_anteriores = models.JSONField(null=True, blank=True)
    valores_nuevos = models.JSONField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'log_auditoria'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.user} - {self.accion} - {self.fecha}"