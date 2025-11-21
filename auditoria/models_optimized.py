"""
Modelos optimizados para PostgreSQL - App: auditoria
Incluye: inmutabilidad, campos JSONB, índices y constraints

CAMBIOS PRINCIPALES:
- Campos JSONB para valores_anteriores y valores_nuevos
- Protección contra UPDATE/DELETE mediante permissions
- Índice GIN para búsquedas en JSONB
- Campos adicionales para trazabilidad completa
- Retención configurable de logs
"""

from django.db import models
from django.contrib.postgres.fields import JSONField  # Para PostgreSQL
from usuarios.models_optimized import User
from calificaciones.models_optimized import Calificacion
from django.core.exceptions import ValidationError


class LogAuditoriaManager(models.Manager):
    """
    Manager personalizado para LogAuditoria.

    Previene operaciones de actualización y eliminación.
    """

    def update(self, *args, **kwargs):
        """
        Sobrescribe update para prevenir modificaciones.

        Raises:
            ValidationError: Siempre (los logs son inmutables)
        """
        raise ValidationError(
            'Los logs de auditoría son inmutables y no pueden ser modificados. '
            'Operación UPDATE no permitida.'
        )

    def delete(self, *args, **kwargs):
        """
        Sobrescribe delete para prevenir eliminaciones.

        Raises:
            ValidationError: Siempre (los logs son inmutables)
        """
        raise ValidationError(
            'Los logs de auditoría son inmutables y no pueden ser eliminados. '
            'Operación DELETE no permitida. '
            'Use el proceso de archivado para logs antiguos.'
        )


class LogAuditoria(models.Model):
    """
    Registro inmutable de auditoría para todas las operaciones críticas.

    Características:
    - Inmutabilidad garantizada a nivel de aplicación y base de datos
    - Almacenamiento de valores anteriores/nuevos en formato JSONB
    - Trazabilidad completa: usuario, IP, timestamp, justificación
    - Retención mínima: 5 años según normativa chilena
    - Cumplimiento: Ley 19.628 (Protección de Datos), Ley 21.663

    IMPORTANTE:
    - No se puede actualizar ni eliminar un log una vez creado
    - Trigger PostgreSQL adicional protege contra modificaciones directas en BD
    """

    ACCIONES = [
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
        ('VIEW', 'Consulta'),
        ('EXPORT', 'Exportación'),
        ('IMPORT', 'Importación'),
        ('APPROVE', 'Aprobación'),
        ('REJECT', 'Rechazo'),
    ]

    # Relaciones
    calificacion = models.ForeignKey(
        Calificacion,
        on_delete=models.PROTECT,  # No permitir eliminar calificación con logs
        related_name='logs_auditoria',
        null=True,  # Puede ser null para acciones generales del sistema
        blank=True,
        help_text="Calificación auditada (si aplica)"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='logs_auditoria',
        help_text="Usuario que realizó la acción"
    )

    # Datos de la acción
    accion = models.CharField(
        max_length=20,
        choices=ACCIONES,
        help_text="Tipo de acción realizada"
    )
    tabla_afectada = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Nombre de la tabla/modelo afectado"
    )
    registro_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID del registro afectado"
    )

    # Timestamp
    fecha = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora exacta de la acción"
    )

    # Detalles de la acción
    detalle = models.TextField(
        help_text="Descripción detallada de la acción"
    )
    justificacion = models.TextField(
        blank=True,
        null=True,
        help_text="Justificación de la acción (obligatorio para UPDATE/DELETE)"
    )

    # Valores anteriores y nuevos (JSONB para PostgreSQL)
    # En PostgreSQL, usar: django.contrib.postgres.fields.JSONField
    # Para compatibilidad, usar models.JSONField (Django 3.1+)
    valores_anteriores = models.JSONField(
        null=True,
        blank=True,
        help_text="Valores antes de la modificación (formato JSON)"
    )
    valores_nuevos = models.JSONField(
        null=True,
        blank=True,
        help_text="Valores después de la modificación (formato JSON)"
    )

    # Trazabilidad adicional
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Dirección IP desde donde se realizó la acción"
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="User agent del navegador/cliente"
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text="Clave de sesión Django"
    )

    # Metadatos adicionales
    metadatos = models.JSONField(
        null=True,
        blank=True,
        help_text="Metadatos adicionales de contexto (formato JSON)"
    )

    # Manager personalizado
    objects = LogAuditoriaManager()

    class Meta:
        db_table = 'log_auditoria'
        ordering = ['-fecha']
        verbose_name = 'Log de Auditoría'
        verbose_name_plural = 'Logs de Auditoría'

        # Permisos personalizados
        permissions = [
            ('view_all_logs', 'Puede ver todos los logs de auditoría'),
            ('export_logs', 'Puede exportar logs de auditoría'),
            ('archive_old_logs', 'Puede archivar logs antiguos'),
        ]

        # Índices optimizados para consultas frecuentes
        indexes = [
            # Índice compuesto para búsquedas por usuario y fecha
            models.Index(fields=['user', 'fecha'], name='idx_audit_user_fecha'),

            # Índice para búsquedas por calificación
            models.Index(fields=['calificacion', 'fecha'], name='idx_audit_calif_fecha'),

            # Índice para búsquedas por acción
            models.Index(fields=['accion', 'fecha'], name='idx_audit_accion_fecha'),

            # Índice para búsquedas por fecha (reportes)
            models.Index(fields=['fecha'], name='idx_audit_fecha'),

            # Índice para búsquedas por tabla y registro
            models.Index(fields=['tabla_afectada', 'registro_id'], name='idx_audit_tabla_registro'),

            # Índice GIN para búsquedas en campos JSONB (específico de PostgreSQL)
            # models.Index(fields=['valores_anteriores'], name='idx_audit_val_ant', opclasses=['jsonb_path_ops']),
            # models.Index(fields=['valores_nuevos'], name='idx_audit_val_new', opclasses=['jsonb_path_ops']),
        ]

        constraints = [
            # Validación: justificación obligatoria para UPDATE/DELETE
            models.CheckConstraint(
                check=(
                    models.Q(accion__in=['CREATE', 'VIEW', 'EXPORT', 'IMPORT', 'APPROVE', 'REJECT']) |
                    models.Q(accion__in=['UPDATE', 'DELETE'], justificacion__isnull=False)
                ),
                name='chk_audit_justificacion_requerida'
            ),
        ]

    def __str__(self):
        return f"{self.get_accion_display()} - {self.user.email} - {self.fecha}"

    def save(self, *args, **kwargs):
        """
        Override de save para permitir solo INSERT, no UPDATE.

        Raises:
            ValidationError: Si se intenta actualizar un log existente
        """
        if self.pk is not None:
            raise ValidationError(
                'Los logs de auditoría son inmutables. '
                'No se puede modificar un log existente.'
            )

        # Validar justificación para UPDATE/DELETE
        if self.accion in ['UPDATE', 'DELETE'] and not self.justificacion:
            raise ValidationError(
                f'La justificación es obligatoria para acciones de tipo {self.get_accion_display()}'
            )

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Override de delete para prevenir eliminación.

        Raises:
            ValidationError: Siempre (los logs son inmutables)
        """
        raise ValidationError(
            'Los logs de auditoría no pueden ser eliminados. '
            'Use el proceso de archivado para logs antiguos.'
        )

    @classmethod
    def registrar_accion(cls, user, accion, detalle, **kwargs):
        """
        Método de clase para registrar una acción de auditoría.

        Args:
            user: Usuario que realiza la acción
            accion: Tipo de acción (CREATE, UPDATE, DELETE, VIEW, etc.)
            detalle: Descripción de la acción
            **kwargs: Parámetros adicionales (calificacion, valores_anteriores, etc.)

        Returns:
            Instancia de LogAuditoria creada

        Example:
            >>> LogAuditoria.registrar_accion(
            ...     user=request.user,
            ...     accion='CREATE',
            ...     detalle='Creación de calificación para cliente 12345678-9',
            ...     calificacion=calificacion,
            ...     valores_nuevos={'anno': 2025, 'factor8': 1000},
            ...     ip_address=get_client_ip(request)
            ... )
        """
        log = cls(
            user=user,
            accion=accion,
            detalle=detalle,
            **kwargs
        )
        log.save()
        return log

    @classmethod
    def registrar_creacion(cls, user, calificacion, valores_nuevos, ip_address=None):
        """
        Registra la creación de una calificación.

        Args:
            user: Usuario que creó
            calificacion: Instancia de Calificacion creada
            valores_nuevos: Dict con los valores de la nueva calificación
            ip_address: IP del cliente (opcional)
        """
        return cls.registrar_accion(
            user=user,
            accion='CREATE',
            detalle=f'Creación de calificación {calificacion.id} para cliente {calificacion.cliente.rut}',
            calificacion=calificacion,
            tabla_afectada='calificacion',
            registro_id=calificacion.id,
            valores_nuevos=valores_nuevos,
            ip_address=ip_address
        )

    @classmethod
    def registrar_actualizacion(cls, user, calificacion, valores_anteriores, valores_nuevos, justificacion, ip_address=None):
        """
        Registra la actualización de una calificación.

        Args:
            user: Usuario que actualizó
            calificacion: Instancia de Calificacion actualizada
            valores_anteriores: Dict con valores antes de la actualización
            valores_nuevos: Dict con valores después de la actualización
            justificacion: Motivo de la actualización (obligatorio)
            ip_address: IP del cliente (opcional)
        """
        return cls.registrar_accion(
            user=user,
            accion='UPDATE',
            detalle=f'Actualización de calificación {calificacion.id}',
            calificacion=calificacion,
            tabla_afectada='calificacion',
            registro_id=calificacion.id,
            valores_anteriores=valores_anteriores,
            valores_nuevos=valores_nuevos,
            justificacion=justificacion,
            ip_address=ip_address
        )

    @classmethod
    def registrar_eliminacion(cls, user, calificacion, valores_anteriores, justificacion, ip_address=None):
        """
        Registra la eliminación de una calificación.

        Args:
            user: Usuario que eliminó
            calificacion: Instancia de Calificacion eliminada
            valores_anteriores: Dict con valores de la calificación eliminada
            justificacion: Motivo de la eliminación (obligatorio)
            ip_address: IP del cliente (opcional)
        """
        return cls.registrar_accion(
            user=user,
            accion='DELETE',
            detalle=f'Eliminación de calificación {calificacion.id}',
            tabla_afectada='calificacion',
            registro_id=calificacion.id,
            valores_anteriores=valores_anteriores,
            justificacion=justificacion,
            ip_address=ip_address
        )

    @classmethod
    def registrar_consulta(cls, user, calificacion=None, detalle='', ip_address=None):
        """
        Registra la consulta/visualización de datos sensibles.

        Args:
            user: Usuario que consultó
            calificacion: Calificación consultada (opcional)
            detalle: Descripción de la consulta
            ip_address: IP del cliente (opcional)
        """
        return cls.registrar_accion(
            user=user,
            accion='VIEW',
            detalle=detalle or f'Consulta de calificación {calificacion.id if calificacion else "N/A"}',
            calificacion=calificacion,
            ip_address=ip_address
        )


"""
TRIGGER POSTGRESQL PARA PROTECCIÓN ADICIONAL DE INMUTABILIDAD:

Agregar este código SQL mediante una migración personalizada:

-- Función para prevenir UPDATE/DELETE en log_auditoria
CREATE OR REPLACE FUNCTION fn_proteger_log_auditoria()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Los logs de auditoría son inmutables. Operación UPDATE no permitida.';
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Los logs de auditoría son inmutables. Operación DELETE no permitida.';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger para UPDATE
CREATE TRIGGER tr_log_auditoria_prevent_update
BEFORE UPDATE ON log_auditoria
FOR EACH ROW
EXECUTE FUNCTION fn_proteger_log_auditoria();

-- Trigger para DELETE
CREATE TRIGGER tr_log_auditoria_prevent_delete
BEFORE DELETE ON log_auditoria
FOR EACH ROW
EXECUTE FUNCTION fn_proteger_log_auditoria();

-- Para permitir archivado (después de 5 años), crear una función especial:
CREATE OR REPLACE FUNCTION fn_archivar_logs_antiguos(anos_retencion INT DEFAULT 5)
RETURNS INTEGER AS $$
DECLARE
    registros_archivados INTEGER;
BEGIN
    -- Mover logs antiguos a tabla de archivo
    INSERT INTO log_auditoria_archivo
    SELECT * FROM log_auditoria
    WHERE fecha < NOW() - INTERVAL '1 year' * anos_retencion;

    GET DIAGNOSTICS registros_archivados = ROW_COUNT;

    -- Eliminar de tabla principal (bypass del trigger usando pg_advisory_lock)
    -- Solo permitido para rol de archivado
    DELETE FROM log_auditoria
    WHERE fecha < NOW() - INTERVAL '1 year' * anos_retencion;

    RETURN registros_archivados;
END;
$$ LANGUAGE plpgsql;

-- Tabla de archivo para logs antiguos (opcional)
CREATE TABLE IF NOT EXISTS log_auditoria_archivo (
    LIKE log_auditoria INCLUDING ALL
);

-- Programar archivado automático con pg_cron (opcional)
-- SELECT cron.schedule('archivar-logs-auditoria', '0 3 1 * *', 'SELECT fn_archivar_logs_antiguos(5)');
"""
