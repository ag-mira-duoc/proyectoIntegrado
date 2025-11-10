from django.contrib import admin
from .models import Calificacion

@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):

    list_display = (
        'id', 'anno', 'cliente_rut', 'corredora_nombre', 'instrumento', 
        'fecha_pago', 'dividendo', 'valor_historico'
    )

    list_filter = ('anno', 'mercado', 'instrumento', 'corredora', 'cliente')
    
    search_fields = (
        'cliente__rut', 'corredora__nombre', 'instrumento', 'descripcion'
    )
    
    readonly_fields = ('factor_actualizacion', 'created')

    fieldsets = (
        ('Información Principal', {
            'fields': ('corredora', 'cliente', 'user', 'anno', 'mercado', 'instrumento')
        }),
        ('Detalles del Evento', {
            'fields': ('fecha_pago', 'secuencia_evento', 'dividendo', 'descripcion', 'valor_historico', 'ingreso_montos', 'isfut')
        }),
        ('Factores Tributarios', {
            'classes': ('collapse',),
            'fields': (
                ('factor8', 'factor9', 'factor10', 'factor11', 'factor12', 'factor13', 'factor14', 'factor15', 'factor16', 'factor17', 'factor18'),
                ('factor19', 'factor20', 'factor21', 'factor22', 'factor23', 'factor24', 'factor25', 'factor26', 'factor27', 'factor28', 'factor29'),
                ('factor30', 'factor31', 'factor32', 'factor33', 'factor34', 'factor35', 'factor36', 'factor37'),
            )
        }),
        ('Fechas', {
            'fields': ('factor_actualizacion', 'created')
        }),
    )

    @admin.display(description='RUT Cliente')
    def cliente_rut(self, obj):
        return obj.cliente.rut
        
    @admin.display(description='Corredora')
    def corredora_nombre(self, obj):
        return obj.corredora.nombre
