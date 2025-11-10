
# Register your models here.
from django.contrib import admin
from .models import Corredora, Accion, ClienteAccion

@admin.register(Corredora)
class CorredonaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'telefono', 'direccion', 'created']
    search_fields = ['nombre']

@admin.register(Accion)
class AccionAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'mercado', 'cliente', 'corredora', 'created']
    list_filter = ['mercado']
    search_fields = ['empresa']

