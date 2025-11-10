from django.contrib import admin
from .models import Corredora

@admin.register(Corredora)
class CorredoraAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'direccion', 'created')
    search_fields = ('nombre', 'telefono', 'direccion')
    list_filter = ('created',)
    list_display_links = ('nombre',)

