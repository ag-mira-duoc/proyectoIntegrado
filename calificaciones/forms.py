"""
Formularios para la app calificaciones.
"""
from django import forms
from django.core.exceptions import ValidationError
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
            'secuencia_evento', 'numero_dividendo', 'tipo_sociedad',
            'dividendo', 'descripcion', 'factor_actualizacion',
            'isfut', 'valor_historico', 'ingreso_montos', 'estado',
            # 30 factores (8 al 37)
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
            'tipo_sociedad': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'isfut': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        # Agregar clases a todos los campos de factores e inputs numéricos
        labels = {}
        for i in range(8, 38):
            widgets[f'factor{i}'] = forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00000001'})

    def __init__(self, *args, **kwargs):
        # 1. Extraemos 'user' de los argumentos antes de llamar a super()
        # Esto soluciona el TypeError: unexpected keyword argument 'user'
        self.user = kwargs.pop('user', None)
        
        # 2. Llamamos al init original sin el argumento 'user'
        super().__init__(*args, **kwargs)
        
        # 3. Lógica personalizada
        # Si el usuario no es administrador, filtrar clientes por su corredora
        if self.user and not (self.user.is_superuser or getattr(self.user, 'es_administrador', lambda: False)()):
            if hasattr(self.user, 'corredora') and self.user.corredora:
                self.fields['cliente'].queryset = Cliente.objects.filter(activo=True) # Podrías filtrar por corredora si el modelo Cliente lo permite
        
        # Help texts y configuraciones visuales
        self.fields['anno'].widget.attrs['placeholder'] = 'YYYY'
        self.fields['secuencia_evento'].required = False
        self.fields['numero_dividendo'].required = False


class ClienteForm(forms.ModelForm):
    """Formulario base para Cliente"""
    class Meta:
        model = Cliente
        fields = ['rut', 'telefono', 'correo', 'activo']
        widgets = {
            'rut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12345678-9'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class PersonaNaturalForm(forms.ModelForm):
    """Formulario para datos de Persona Natural"""
    class Meta:
        model = PersonaNatural
        fields = ['nombre', 'apellido']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PersonaJuridicaForm(forms.ModelForm):
    """Formulario para datos de Persona Jurídica"""
    class Meta:
        model = PersonaJuridica
        fields = ['razon_social', 'domicilio_tributario']
        widgets = {
            'razon_social': forms.TextInput(attrs={'class': 'form-control'}),
            'domicilio_tributario': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CorrederaForm(forms.ModelForm):
    """Formulario para crear/editar corredoras"""
    class Meta:
        model = Corredora
        fields = ['nombre', 'telefono', 'direccion', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class IngresoMontoForm(forms.Form):
    """
    Formulario para ingresar Montos Base y calcular Factores.
    Basado en la lógica de negocio: Factor = Monto Parcial / Monto Total Reparto
    """
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(activo=True), 
        label="Cliente",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    anno = forms.IntegerField(
        label="Ejercicio (Año)", 
        initial=2025,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    # Denominador común (Suma columnas 8 a 19 según Excel de homologación)
    monto_total_reparto = forms.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        label="Monto Total Reparto (Denominador)",
        help_text="Corresponde a la suma de las columnas 8 a 19.",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    # Numeradores (Montos parciales para cada factor)
    monto_f8_credito_idpc = forms.DecimalField(
        max_digits=15, decimal_places=2, initial=0, required=False,
        label="F8: Con crédito IDPC (desde 2017)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    monto_f12_exento = forms.DecimalField(
        max_digits=15, decimal_places=2, initial=0, required=False,
        label="F12: Rentas Exentas (Art 11)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        monto_total = cleaned_data.get('monto_total_reparto') or 0
        f8 = cleaned_data.get('monto_f8_credito_idpc') or 0
        f12 = cleaned_data.get('monto_f12_exento') or 0
        
        if (f8 + f12) > monto_total:
            raise ValidationError("La suma de los montos parciales ingresados supera el Monto Total de Reparto.")
        return cleaned_data

class CargaMasivaFactoresForm(forms.Form):
    """
    Formulario para subir PDF de carga masiva (Certificados 70/44).
    """
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(activo=True),
        label="Cliente Asociado",
        help_text="Cliente al que corresponde este certificado.",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    archivo_pdf = forms.FileField(
        label="Archivo PDF",
        help_text="Formatos soportados: Certificado N° 70, Certificado N° 44 (Digital o Escaneado).",
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'})
    )
    
    def clean_archivo_pdf(self):
        archivo = self.cleaned_data.get('archivo_pdf')
        if archivo:
            if not archivo.name.lower().endswith('.pdf'):
                raise ValidationError("El archivo debe tener extensión .pdf")
        return archivo