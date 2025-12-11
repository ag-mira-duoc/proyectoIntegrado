from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.utils import timezone
from datetime import datetime, timedelta
import os


try:
    from nuam_config.azure_config import AZURE_CONNECTION_STRING, CONTAINER_NAME
    from azure.storage.blob import generate_blob_sas, BlobSasPermissions
except ImportError:

    AZURE_CONNECTION_STRING = None
    CONTAINER_NAME = None


class Documento(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente de Procesamiento'),
        ('PROCESANDO', 'Procesando OCR'),
        ('COMPLETADO', 'Procesamiento Completado'),
        ('ERROR', 'Error en Procesamiento'),
        ('REVISION_MANUAL', 'Requiere Revisión Manual'),
    ]

    TIPOS_DOCUMENTO = [
        ('CERT_70', 'Certificado 70 (DJ 1948)'),
        ('CERT_44', 'Certificado 44 (DJ 1922)'),
        ('COMPROBANTE', 'Comprobante de Dividendos'),
        ('OTRO', 'Otro Documento'),
    ]

    # Relaciones
    calificacion = models.ForeignKey(
        'calificaciones.Calificacion',
        on_delete=models.CASCADE,
        related_name='documentos',
        null=True,
        blank=True,
        help_text="Calificación asociada (si ya existe)"
    )
    usuario_carga = models.ForeignKey(
        'usuarios.User',
        on_delete=models.PROTECT,
        related_name='documentos_cargados',
        help_text="Usuario que cargó el documento"
    )

    # Datos del documento
    tipo_documento = models.CharField(
        max_length=20,
        choices=TIPOS_DOCUMENTO,
        default='CERT_70',
        help_text="Tipo de documento tributario"
    )
    nombre_archivo = models.CharField(
        max_length=255,
        help_text="Nombre original del archivo"
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción adicional del documento"
    )

    # Almacenamiento Cloud (Azure Blob Storage)
    # NOTA: Mantenemos nombres 'firebase' para evitar migraciones, pero ahora apuntan a Azure.
    url_firebase = models.URLField(
        max_length=500,
        help_text="URL Base del archivo en Azure (sin token SAS)"
    )
    firebase_path = models.CharField(
        max_length=500,
        help_text="Nombre del Blob en Azure (ej: user/2025/archivo.pdf)"
    )
    tamaño_bytes = models.BigIntegerField(
        help_text="Tamaño del archivo en bytes"
    )
    checksum_md5 = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text="Checksum MD5 para verificación de integridad"
    )

    # Procesamiento OCR
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PENDIENTE',
        help_text="Estado del procesamiento OCR"
    )
    texto_extraido = models.TextField(
        blank=True,
        null=True,
        help_text="Texto extraído por Tesseract OCR"
    )
    # Vector de búsqueda para full-text search (PostgreSQL)
    search_vector = SearchVectorField(
        null=True,
        blank=True,
        help_text="Vector de búsqueda para full-text search"
    )

    # Datos extraídos estructurados (JSONB)
    datos_extraidos = models.JSONField(
        null=True,
        blank=True,
        help_text="Datos estructurados extraídos del documento (factores, RUT, etc.)"
    )
    confianza_ocr = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Nivel de confianza del OCR (0-100%)"
    )

    # Procesamiento
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="ID de la tarea Celery que procesa este documento"
    )
    fecha_inicio_procesamiento = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha/hora de inicio del procesamiento OCR"
    )
    fecha_fin_procesamiento = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha/hora de finalización del procesamiento"
    )
    tiempo_procesamiento_segundos = models.IntegerField(
        null=True,
        blank=True,
        help_text="Tiempo total de procesamiento en segundos"
    )

    # Errores
    error_mensaje = models.TextField(
        blank=True,
        null=True,
        help_text="Mensaje de error si el procesamiento falló"
    )
    error_traceback = models.TextField(
        blank=True,
        null=True,
        help_text="Traceback completo del error (para debugging)"
    )

    # Revisión manual
    requiere_revision = models.BooleanField(
        default=False,
        help_text="Si el documento requiere revisión manual"
    )
    revisado_por = models.ForeignKey(
        'usuarios.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_revisados',
        help_text="Usuario que revisó manualmente el documento"
    )
    fecha_revision = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha/hora de la revisión manual"
    )
    notas_revision = models.TextField(
        blank=True,
        null=True,
        help_text="Notas de la revisión manual"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documento'
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['calificacion'], name='idx_doc_calificacion'),
            models.Index(fields=['usuario_carga', 'created_at'], name='idx_doc_user_created'),
            models.Index(fields=['estado'], name='idx_doc_estado'),
            models.Index(fields=['tipo_documento'], name='idx_doc_tipo'),
            models.Index(fields=['created_at'], name='idx_doc_created'),
            models.Index(fields=['celery_task_id'], name='idx_doc_task_id'),
            GinIndex(fields=['search_vector'], name='idx_doc_search_vector'),
        ]

    def __str__(self):
        return f"{self.nombre_archivo} ({self.get_estado_display()})"

    def get_extension(self) -> str:
        return os.path.splitext(self.nombre_archivo)[1].lower()

    def es_pdf(self) -> bool:
        return self.get_extension() == '.pdf'

    def obtener_url_firmada(self, expiracion_minutos=30):
        """
        Genera una URL temporal (SAS Token) para ver el archivo privado en Azure.
        """
        if not self.firebase_path or not AZURE_CONNECTION_STRING:
            return None

        try:
            # Parsear la Connection String para obtener AccountName y AccountKey
            # Formato: "DefaultEndpointsProtocol=https;AccountName=x;AccountKey=y;..."
            parts = dict(s.split('=', 1) for s in AZURE_CONNECTION_STRING.split(';') if s)
            account_name = parts.get('AccountName')
            account_key = parts.get('AccountKey')

            if not account_name or not account_key:
                return None

            # Generar token SAS (Shared Access Signature)
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=CONTAINER_NAME,
                blob_name=self.firebase_path,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(minutes=expiracion_minutos)
            )

            # Construir URL firmada
            url = f"https://{account_name}.blob.core.windows.net/{CONTAINER_NAME}/{self.firebase_path}?{sas_token}"
            return url

        except Exception as e:
            print(f"Error generando SAS token para documento {self.pk}: {e}")
            return None

    def marcar_como_procesando(self, task_id: str):
        self.estado = 'PROCESANDO'
        self.celery_task_id = task_id
        self.fecha_inicio_procesamiento = timezone.now()
        self.save()

    def marcar_como_completado(self, texto_extraido: str, datos_extraidos: dict, confianza: float):
        self.estado = 'COMPLETADO'
        self.texto_extraido = texto_extraido
        self.datos_extraidos = datos_extraidos
        self.confianza_ocr = confianza
        self.fecha_fin_procesamiento = timezone.now()

        if self.fecha_inicio_procesamiento:
            delta = self.fecha_fin_procesamiento - self.fecha_inicio_procesamiento
            self.tiempo_procesamiento_segundos = int(delta.total_seconds())

        if confianza < 80:
            self.requiere_revision = True
            self.estado = 'REVISION_MANUAL'

        self.save()
        self.actualizar_search_vector()

    def marcar_como_error(self, error_mensaje: str, error_traceback: str = None):
        self.estado = 'ERROR'
        self.error_mensaje = error_mensaje
        self.error_traceback = error_traceback
        self.fecha_fin_procesamiento = timezone.now()
        self.requiere_revision = True
        self.save()

    def actualizar_search_vector(self):
        if self.texto_extraido:
            from django.contrib.postgres.search import SearchVector
            Documento.objects.filter(pk=self.pk).update(
                search_vector=SearchVector('texto_extraido', 'nombre_archivo', 'descripcion')
            )

    @classmethod
    def buscar_texto(cls, query: str):
        from django.contrib.postgres.search import SearchQuery
        return cls.objects.filter(
            search_vector=SearchQuery(query, search_type='phrase')
        )


class CargaMasiva(models.Model):
    """
    Registro de una carga masiva de documentos.
    """
    ESTADOS = [
        ('INICIADA', 'Iniciada'),
        ('EN_PROCESO', 'En Proceso'),
        ('COMPLETADA', 'Completada'),
        ('COMPLETADA_CON_ERRORES', 'Completada con Errores'),
        ('CANCELADA', 'Cancelada'),
    ]

    usuario = models.ForeignKey(
        'usuarios.User',
        on_delete=models.PROTECT,
        related_name='cargas_masivas'
    )

    total_archivos = models.IntegerField(default=0, help_text="Total de archivos en la carga")
    archivos_procesados = models.IntegerField(default=0, help_text="Archivos procesados exitosamente")
    archivos_con_error = models.IntegerField(default=0, help_text="Archivos con errores")
    archivos_pendientes = models.IntegerField(default=0, help_text="Archivos pendientes de procesar")
    
    estado = models.CharField(max_length=30, choices=ESTADOS, default='INICIADA')
    
    progreso_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, help_text="Porcentaje de progreso (0-100)"
    )

    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    descripcion = models.TextField(blank=True, null=True, help_text="Descripción de la carga masiva")
    metadatos = models.JSONField(null=True, blank=True, help_text="Metadatos adicionales")

    class Meta:
        db_table = 'carga_masiva'
        verbose_name = 'Carga Masiva'
        verbose_name_plural = 'Cargas Masivas'
        ordering = ['-fecha_inicio']
        indexes = [
            models.Index(fields=['usuario', 'fecha_inicio'], name='idx_cm_user_fecha'),
            models.Index(fields=['estado'], name='idx_cm_estado'),
        ]

    def __str__(self):
        return f"Carga Masiva {self.id} - {self.usuario.email} ({self.get_estado_display()})"

    def actualizar_progreso(self):
        documentos = Documento.objects.filter(
            usuario_carga=self.usuario,
            created_at__gte=self.fecha_inicio
        )

        self.total_archivos = documentos.count()
        self.archivos_procesados = documentos.filter(estado='COMPLETADO').count()
        self.archivos_con_error = documentos.filter(estado='ERROR').count()
        self.archivos_pendientes = documentos.filter(estado='PENDIENTE').count()

        if self.total_archivos > 0:
            self.progreso_porcentaje = (
                (self.archivos_procesados + self.archivos_con_error) / self.total_archivos
            ) * 100
        else:
            self.progreso_porcentaje = 0

        if self.archivos_pendientes == 0 and self.total_archivos > 0:
            if self.archivos_con_error > 0:
                self.estado = 'COMPLETADA_CON_ERRORES'
            else:
                self.estado = 'COMPLETADA'

            if not self.fecha_fin:
                self.fecha_fin = timezone.now()

        self.save()

    def cancelar(self):
        self.estado = 'CANCELADA'
        self.fecha_fin = timezone.now()
        self.save()