from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm 

from .models import User

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        # AÑADIMOS 'corredora' aquí
        fields = ('email', 'rut', 'corredora') 

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    
    list_display = ('email', 'rut', 'corredora_nombre', 'is_staff')
    list_display_links = ('email',)
    
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'corredora')
    
    search_fields = ('email', 'rut', 'first_name', 'last_name')
    

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'rut', 'corredora')}), 
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined', 'created')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'rut', 'corredora', 'is_active', 'is_staff', 'is_superuser', 'password', 'password2'),
        }),
    )
    
    ordering = ('email',)
    readonly_fields = ('created',)
    
    @admin.display(description='Corredora')
    def corredora_nombre(self, obj):
        return obj.corredora.nombre if obj.corredora else "N/A"