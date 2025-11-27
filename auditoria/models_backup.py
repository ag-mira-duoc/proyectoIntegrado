from django.db import models

# Create your models here.
from django.db import models
from usuarios.models import User
from calificaciones.models import Calificacion

class LogAuditoria(models.Model):
    ACCIONES = [
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
        ('VIEW', 'Consulta'),
    ]
    
    calificacion = models.ForeignKey(Calificacion, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    accion = models.CharField(max_length=255, choices=ACCIONES)
    fecha = models.DateTimeField(auto_now_add=True)
    detalle = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'log_auditoria'
        ordering = ['-fecha']
        verbose_name = 'Log de Auditoría'
        verbose_name_plural = 'Logs de Auditoría'
    
    def __str__(self):
        return f"{self.accion} - {self.user.email} - {self.fecha}"
