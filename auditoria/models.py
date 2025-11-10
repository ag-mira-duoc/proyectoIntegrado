from django.db import models

class LogAuditoria(models.Model):
    """
    Modelo para registrar auditoría de acciones sobre calificaciones
    """
    ACCIONES = [
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
        ('VIEW', 'Consulta'),
    ]
    
    user = models.ForeignKey(
        'usuarios.User', 
        on_delete=models.DO_NOTHING,
        related_name='logs_auditoria',
        verbose_name='Usuario'
    )
    
    calificacion = models.ForeignKey(
        'calificaciones.Calificacion',
        on_delete=models.DO_NOTHING,
        related_name='logs_auditoria',
        verbose_name='Calificación',
        null=True,
        blank=True
    )
    
    accion = models.CharField(
        max_length=255, 
        choices=ACCIONES,
        verbose_name='Acción'
    )
    
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha y Hora'
    )
    
    detalle = models.TextField(
        blank=True,
        null=True,
        verbose_name='Detalle'
    )
    
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        verbose_name='Dirección IP'
    )
    
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = True
        db_table = 'log_auditoria'
        ordering = ['-fecha']
        verbose_name = 'Log de Auditoría'
        verbose_name_plural = 'Logs de Auditoría'
        indexes = [
            models.Index(fields=['-fecha']),
            models.Index(fields=['user', '-fecha']),
            models.Index(fields=['accion', '-fecha']),
        ]
    
    def __str__(self):
        return f"{self.get_accion_display()} - {self.user.email} - {self.fecha.strftime('%Y-%m-%d %H:%M')}"
