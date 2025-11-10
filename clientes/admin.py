from django.contrib import admin

from .models import Cliente, PersonaNatural, PersonaJuridica


class PersonaNaturalInline(admin.StackedInline):
    model = PersonaNatural
    extra = 0
    max_num = 1

class PersonaJuridicaInline(admin.StackedInline):
    model = PersonaJuridica
    extra = 0
    max_num = 1

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('rut', 'telefono', 'correo', 'es_persona_natural')
    search_fields = ('rut', 'telefono', 'correo')
    
    inlines = [PersonaNaturalInline, PersonaJuridicaInline]

    @admin.display(description='Tipo')
    def es_persona_natural(self, obj):
        if hasattr(obj, 'personanatural'):
            return "Natural"
        elif hasattr(obj, 'personajuridica'):
            return "Jurídica"
        return "N/A"

@admin.register(PersonaNatural)
class PersonaNaturalAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'cliente_rut', 'created')
    search_fields = ('nombre', 'apellido', 'cliente__rut')
    list_filter = ('created',)
    
    @admin.display(description='Nombre Completo')
    def nombre_completo(self, obj):
        return f"{obj.nombre} {obj.apellido}"
        
    @admin.display(description='RUT Cliente')
    def cliente_rut(self, obj):
        return obj.cliente.rut

@admin.register(PersonaJuridica)
class PersonaJuridicaAdmin(admin.ModelAdmin):
    list_display = ('razon_social', 'cliente_rut', 'domicilio_tributario', 'created')
    search_fields = ('razon_social', 'domicilio_tributario', 'cliente__rut')
    list_filter = ('created',)

    @admin.display(description='RUT Cliente')
    def cliente_rut(self, obj):
        return obj.cliente.rut
