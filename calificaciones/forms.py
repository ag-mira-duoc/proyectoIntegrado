"""
Formularios para la app calificaciones
"""
from django import forms
from .models import Calificacion, Cliente, PersonaNatural, PersonaJuridica, Corredora


class CalificacionForm(forms.ModelForm):
    """
    Formulario para crear/editar calificaciones tributarias.
    
    Incluye todos los 30 factores del formulario 1851 SII.
    """
    class Meta:
        model = Calificacion
        fields = [
            'cliente', 'anno', 'mercado', 'instrumento', 'fecha_pago',
            'secuencia_evento', 'dividendo', 'descripcion', 'factor_actualizacion',
            'isfut', 'valor_historico', 'ingreso_montos', 'estado',
            # 30 factores
            'factor8', 'factor9', 'factor10', 'factor11', 'factor12',
            'factor13', 'factor14', 'factor15', 'factor16', 'factor17',
            'factor18', 'factor19', 'factor20', 'factor21', 'factor22',
            'factor23', 'factor24', 'factor25', 'factor26', 'factor27',
            'factor28', 'factor29', 'factor30', 'factor31', 'factor32',
            'factor33', 'factor34', 'factor35', 'factor36', 'factor37',
        ]
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'anno': forms.NumberInput(attrs={'class': 'form-control'}),
            'mercado': forms.Select(attrs={'class': 'form-select'}),
            'instrumento': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_pago': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'secuencia_evento': forms.NumberInput(attrs={'class': 'form-control'}),
            'dividendo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'factor_actualizacion': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'valor_historico': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'isfut': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ingreso_montos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        # Widgets para los 30 factores
        for i in range(8, 38):
            widgets[f'factor{i}'] = forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Si el usuario no es administrador, filtrar clientes por corredora
        if self.user and not (self.user.is_superuser or self.user.es_administrador()):
            if hasattr(self.user, 'corredora') and self.user.corredora:
                self.fields['cliente'].queryset = Cliente.objects.filter(activo=True)
        
        # Help texts personalizados
        self.fields['anno'].help_text = 'Año comercial (ej: 2024)'
        self.fields['cliente'].help_text = 'Seleccione el cliente'
        self.fields['estado'].help_text = 'Estado actual de la calificación'


class ClienteForm(forms.ModelForm):
    """
    Formulario para crear/editar clientes (base).
    """
    class Meta:
        model = Cliente
        fields = ['rut', 'telefono', 'correo']
        widgets = {
            'rut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12345678-9'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56912345678'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'cliente@email.com'}),
        }


class PersonaNaturalForm(forms.ModelForm):
    """
    Formulario para crear/editar personas naturales.
    """
    class Meta:
        model = PersonaNatural
        fields = ['nombre', 'apellido']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Juan'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pérez'}),
        }


class PersonaJuridicaForm(forms.ModelForm):
    """
    Formulario para crear/editar personas jurídicas.
    """
    class Meta:
        model = PersonaJuridica
        fields = ['razon_social', 'domicilio_tributario', 'giro']
        widgets = {
            'razon_social': forms.TextInput(attrs={'class': 'form-control'}),
            'domicilio_tributario': forms.TextInput(attrs={'class': 'form-control'}),
            'giro': forms.TextInput(attrs={'class': 'form-control'}),
        }


class CorrederaForm(forms.ModelForm):
    """
    Formulario para crear/editar corredoras.
    """
    class Meta:
        model = Corredora
        fields = ['nombre', 'telefono', 'direccion', 'email_contacto', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'email_contacto': forms.EmailInput(attrs={'class': 'form-control'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
