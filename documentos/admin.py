from django.contrib import admin
from .models import Documento, CargaMasiva

@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    # Columnas que verás en la lista
    list_display = (
        'nombre_archivo', 
        'estado', 
        'confianza_ocr', 
        'tipo_documento', 
        'created_at'
    )
    
    # Filtros laterales
    list_filter = ('estado', 'tipo_documento', 'requiere_revision')
    
    # Barra de búsqueda (busca por nombre o por el texto que extrajo Docling)
    search_fields = ('nombre_archivo', 'texto_extraido', 'descripcion')
    
    # Campos que no se deben editar manualmente para no romper la data
    readonly_fields = (
        'texto_extraido', 
        'datos_extraidos', 
        'celery_task_id', 
        'search_vector'
    )

@admin.register(CargaMasiva)
class CargaMasivaAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'estado', 'progreso_porcentaje', 'fecha_inicio')
    list_filter = ('estado',)