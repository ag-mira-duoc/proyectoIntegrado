"""
Formularios para la app usuarios (autenticación y perfil)
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from .models import User, Corredora


class LoginForm(AuthenticationForm):
    """
    Formulario personalizado de login.
    
    Usa email en lugar de username.
    """
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'tu@email.com',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        })
    )


class RegistroForm(UserCreationForm):
    """
    Formulario de registro de nuevos usuarios.
    
    Campos requeridos:
    - email
    - rut (con validación chilena)
    - nombre
    - apellido
    - corredora (opcional)
    - password1, password2
    """
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'tu@email.com'
        })
    )
    
    rut = forms.CharField(
        label='RUT',
        max_length=12,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12345678-9'
        }),
        help_text='Formato: 12345678-9'
    )
    
    nombre = forms.CharField(
        label='Nombre',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Juan'
        })
    )
    
    apellido = forms.CharField(
        label='Apellido',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Pérez'
        })
    )
    
    corredora = forms.ModelChoiceField(
        queryset=Corredora.objects.filter(activa=True),
        required=False,
        label='Corredora',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        help_text='Opcional: selecciona tu corredora'
    )
    
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        }),
        help_text='Mínimo 8 caracteres'
    )
    
    password2 = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña'
        })
    )
    
    class Meta:
        model = User
        fields = ('email', 'rut', 'nombre', 'apellido', 'corredora', 'password1', 'password2')
    
    def clean_email(self):
        """Valida que el email no esté registrado."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Este email ya está registrado.')
        return email
    
    def clean_rut(self):
        """Valida que el RUT no esté registrado."""
        rut = self.cleaned_data.get('rut')
        if User.objects.filter(rut=rut).exists():
            raise ValidationError('Este RUT ya está registrado.')
        return rut

    def save(self, commit=True):
        """Guarda el usuario y le asigna el rol 'Analistas' por defecto."""
        from django.contrib.auth.models import Group
        user = super().save(commit=False)
        if commit:
            user.save()
            # Asignar rol "Analistas" por defecto
            try:
                analistas_group = Group.objects.get(name='Analistas')
                user.groups.add(analistas_group)
            except Group.DoesNotExist:
                pass  # Si no existe el grupo, no hacer nada
        return user


class PerfilForm(forms.ModelForm):
    """
    Formulario para editar el perfil del usuario.
    
    Campos editables:
    - nombre
    - apellido
    - email (solo si no está en uso)
    """
    class Meta:
        model = User
        fields = ('nombre', 'apellido', 'email')
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # RUT no es editable
        self.fields['email'].help_text = 'Asegúrate de que sea un email válido'
    
    def clean_email(self):
        """Valida que el email no esté en uso por otro usuario."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('Este email ya está en uso.')
        return email


class CambiarPasswordForm(PasswordChangeForm):
    """
    Formulario personalizado para cambiar contraseña.
    """
    old_password = forms.CharField(
        label='Contraseña Actual',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña actual'
        })
    )
    
    new_password1 = forms.CharField(
        label='Nueva Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nueva contraseña'
        }),
        help_text='Mínimo 8 caracteres'
    )
    
    new_password2 = forms.CharField(
        label='Confirmar Nueva Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar nueva contraseña'
        })
    )


class EditarUsuarioForm(forms.ModelForm):
    """Formulario para que admin edite usuarios y sus roles."""
    grupos = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Roles'
    )

    class Meta:
        model = User
        fields = ('nombre', 'apellido', 'email', 'corredora', 'is_active', 'is_staff')
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'corredora': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        from django.contrib.auth.models import Group
        super().__init__(*args, **kwargs)
        self.fields['grupos'].queryset = Group.objects.all()
        if self.instance.pk:
            self.fields['grupos'].initial = self.instance.groups.all()

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Actualizar grupos
            user.groups.set(self.cleaned_data['grupos'])
        return user
