"""
Modelos para la app documentos - Integración Firebase Storage + Tesseract OCR

ARQUITECTURA HÍBRIDA:
- Metadatos: PostgreSQL (búsqueda rápida, relaciones)
- Archivos PDF: Firebase Storage (almacenamiento masivo, CDN)
- Texto extraído OCR: PostgreSQL (búsqueda full-text)

FEATURES:
- Carga masiva de PDFs
- Procesamiento asíncrono con Celery
- Extracción OCR con Tesseract
- Sincronización PostgreSQL ↔ Firebase via triggers
"""

from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
import os


class Documento(models.Model):
    """
    Representa un documento PDF asociado a una calificación tributaria.

    Arquitectura:
    - PDF original: Firebase Storage (gs://nuam-documentos/)
    - Metadatos: PostgreSQL (esta tabla)
    - Texto OCR: PostgreSQL (campo texto_extraido con full-text search)

    Workflow:
    1. Usuario carga PDF → Django guarda en Firebase Storage
    2. Se crea registro en PostgreSQL con url_firebase
    3. Trigger PostgreSQL notifica cambio via NOTIFY
    4. Celery task procesa PDF con Tesseract OCR
    5. Texto extraído se guarda en texto_extraido
    6. Si hay errores, se marca para revisión manual
    """

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

    # Relaciones (importadas dinámicamente para evitar imports circulares)
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

    # Almacenamiento Firebase
    url_firebase = models.URLField(
        max_length=500,
        help_text="URL del archivo en Firebase Storage"
    )
    firebase_path = models.CharField(
        max_length=500,
        help_text="Ruta completa en Firebase Storage (gs://bucket/path)"
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
            # Índice GIN para full-text search en PostgreSQL
            GinIndex(fields=['search_vector'], name='idx_doc_search_vector'),
        ]

    def __str__(self):
        return f"{self.nombre_archivo} ({self.get_estado_display()})"

    def get_extension(self) -> str:
        """Retorna la extensión del archivo."""
        return os.path.splitext(self.nombre_archivo)[1].lower()

    def es_pdf(self) -> bool:
        """Verifica si el documento es un PDF."""
        return self.get_extension() == '.pdf'

    def marcar_como_procesando(self, task_id: str):
        """
        Marca el documento como en procesamiento.

        Args:
            task_id: ID de la tarea Celery
        """
        from django.utils import timezone
        self.estado = 'PROCESANDO'
        self.celery_task_id = task_id
        self.fecha_inicio_procesamiento = timezone.now()
        self.save()

    def marcar_como_completado(self, texto_extraido: str, datos_extraidos: dict, confianza: float):
        """
        Marca el documento como procesado exitosamente.

        Args:
            texto_extraido: Texto extraído por OCR
            datos_extraidos: Diccionario con datos estructurados
            confianza: Nivel de confianza del OCR (0-100)
        """
        from django.utils import timezone
        self.estado = 'COMPLETADO'
        self.texto_extraido = texto_extraido
        self.datos_extraidos = datos_extraidos
        self.confianza_ocr = confianza
        self.fecha_fin_procesamiento = timezone.now()

        if self.fecha_inicio_procesamiento:
            delta = self.fecha_fin_procesamiento - self.fecha_inicio_procesamiento
            self.tiempo_procesamiento_segundos = int(delta.total_seconds())

        # Verificar si requiere revisión manual (baja confianza)
        if confianza < 80:
            self.requiere_revision = True
            self.estado = 'REVISION_MANUAL'

        self.save()

        # Actualizar vector de búsqueda
        self.actualizar_search_vector()

    def marcar_como_error(self, error_mensaje: str, error_traceback: str = None):
        """
        Marca el documento con error en el procesamiento.

        Args:
            error_mensaje: Mensaje de error
            error_traceback: Traceback del error (opcional)
        """
        from django.utils import timezone
        self.estado = 'ERROR'
        self.error_mensaje = error_mensaje
        self.error_traceback = error_traceback
        self.fecha_fin_procesamiento = timezone.now()
        self.requiere_revision = True
        self.save()

    def actualizar_search_vector(self):
        """
        Actualiza el vector de búsqueda para full-text search.

        Usa PostgreSQL SearchVector para indexar texto_extraido.
        """
        if self.texto_extraido:
            from django.contrib.postgres.search import SearchVector
            Documento.objects.filter(pk=self.pk).update(
                search_vector=SearchVector('texto_extraido', 'nombre_archivo', 'descripcion')
            )

    @classmethod
    def buscar_texto(cls, query: str):
        """
        Búsqueda full-text en documentos procesados.

        Args:
            query: Texto a buscar

        Returns:
            QuerySet con documentos que contienen el texto

        Example:
            >>> Documento.buscar_texto('12345678-9')
            <QuerySet [<Documento: form_1851_cliente_12345678.pdf>]>
        """
        from django.contrib.postgres.search import SearchQuery
        return cls.objects.filter(
            search_vector=SearchQuery(query, search_type='phrase')
        )


class CargaMasiva(models.Model):
    """
    Registro de una carga masiva de documentos.

    Agrupa múltiples documentos cargados en una sola operación.
    Permite seguimiento del progreso y estadísticas.
    """

    ESTADOS = [
        ('INICIADA', 'Iniciada'),
        ('EN_PROCESO', 'En Proceso'),
        ('COMPLETADA', 'Completada'),
        ('COMPLETADA_CON_ERRORES', 'Completada con Errores'),
        ('CANCELADA', 'Cancelada'),
    ]

    # Usuario que inició la carga
    usuario = models.ForeignKey(
        'usuarios.User',
        on_delete=models.PROTECT,
        related_name='cargas_masivas'
    )

    # Estadísticas
    total_archivos = models.IntegerField(
        default=0,
        help_text="Total de archivos en la carga"
    )
    archivos_procesados = models.IntegerField(
        default=0,
        help_text="Archivos procesados exitosamente"
    )
    archivos_con_error = models.IntegerField(
        default=0,
        help_text="Archivos con errores"
    )
    archivos_pendientes = models.IntegerField(
        default=0,
        help_text="Archivos pendientes de procesar"
    )

    # Estado
    estado = models.CharField(
        max_length=30,
        choices=ESTADOS,
        default='INICIADA'
    )

    # Progreso
    progreso_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Porcentaje de progreso (0-100)"
    )

    # Timestamps
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(
        null=True,
        blank=True
    )

    # Metadatos
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción de la carga masiva"
    )
    metadatos = models.JSONField(
        null=True,
        blank=True,
        help_text="Metadatos adicionales (tamaño total, tipos de archivo, etc.)"
    )

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
        """
        Actualiza las estadísticas y progreso de la carga.
        """
        from usuarios.models import User

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

        # Actualizar estado
        if self.archivos_pendientes == 0 and self.total_archivos > 0:
            if self.archivos_con_error > 0:
                self.estado = 'COMPLETADA_CON_ERRORES'
            else:
                self.estado = 'COMPLETADA'

            if not self.fecha_fin:
                from django.utils import timezone
                self.fecha_fin = timezone.now()

        self.save()

    def cancelar(self):
        """
        Cancela la carga masiva en proceso.
        """
        from django.utils import timezone
        self.estado = 'CANCELADA'
        self.fecha_fin = timezone.now()
        self.save()
