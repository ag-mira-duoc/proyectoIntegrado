# Register your models here.
from django.contrib import admin
from .models import LogAuditoria

@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ['user', 'accion', 'calificacion', 'fecha', 'ip_address']
    list_filter = ['accion', 'fecha']
    search_fields = ['detalle']
    readonly_fields = ['user', 'calificacion', 'accion', 'fecha', 'detalle', 'ip_address', 'created']
    
    def has_add_permission(self, request):
        return False  # No crear logs manualmente