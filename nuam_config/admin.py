from django.contrib import admin
from usuarios.models import User
from calificaciones.models import Calificacion
from clientes.models import Cliente
from acciones.models import Corredora


admin.site.register(User)

@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ['corredora',
                    'cliente',
                    'user',
                    'anno']
    list_filter=['anno']

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['rut',
                    'telefono',
                    'correo']
    list_filter=['rut']

@admin.register(Corredora)
class CorrdedoraAdmin(admin.ModelAdmin):
    list_display = ['nombre',
                    'telefono',
                    'direccion']
    list_filter = ['nombre']