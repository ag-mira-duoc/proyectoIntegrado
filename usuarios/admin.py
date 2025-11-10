
# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, TipoUsuario

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Administrador personalizado para el modelo User
    """
    list_display = ['email', 'first_name', 'last_name', 'rut', 'is_staff', 'is_active', 'created']
    list_filter = ['is_staff', 'is_active', 'is_superuser', 'created']
    search_fields = ['email', 'first_name', 'last_name', 'rut']
    ordering = ['-created']
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('email', 'rut', 'first_name', 'last_name', 'password')
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Información Adicional', {
            'fields': ('corredora', 'created'),
        }),
    )
    
    add_fieldsets = (
        ('Crear Usuario', {
            'classes': ('wide',),
            'fields': ('email', 'rut', 'first_name', 'last_name', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )
    
    readonly_fields = ['created']

@admin.register(TipoUsuario)
class TipoUsuarioAdmin(admin.ModelAdmin):
    list_display = ['id', 'descripcion']
    search_fields = ['descripcion']