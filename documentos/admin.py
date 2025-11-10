# Register your models here.
from django.contrib import admin
from .models import Documento

@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'cliente', 'calificacion', 'fecha_emision', 'fecha_ingreso']
    list_filter = ['tipo', 'fecha_emision']
    search_fields = ['tipo']