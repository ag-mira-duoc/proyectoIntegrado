from django.db import models

# Create your models here.
from django.db import models
from usuarios.models import User, Corredora

class Cliente(models.Model):
    rut = models.CharField(max_length=255, unique=True)
    telefono = models.CharField(max_length=255, blank=True, null=True)
    correo = models.EmailField(blank=True, null=True)
    
    class Meta:
        db_table = 'cliente'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
    
    def __str__(self):
        return self.rut

class PersonaNatural(models.Model):
    cliente = models.OneToOneField(Cliente, on_delete=models.CASCADE, related_name='persona_natural')
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    
    class Meta:
        db_table = 'persona_natural'
        verbose_name = 'Persona Natural'
        verbose_name_plural = 'Personas Naturales'
    
    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class PersonaJuridica(models.Model):
    cliente = models.OneToOneField(Cliente, on_delete=models.CASCADE, related_name='persona_juridica')
    razon_social = models.CharField(max_length=255)
    domicilio_tributario = models.CharField(max_length=255)
    
    class Meta:
        db_table = 'persona_juridica'
        verbose_name = 'Persona Jurídica'
        verbose_name_plural = 'Personas Jurídicas'
    
    def __str__(self):
        return self.razon_social

class Accion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='acciones')
    corredora = models.ForeignKey(Corredora, on_delete=models.CASCADE)
    empresa = models.CharField(max_length=255)
    mercado = models.CharField(max_length=255)
    
    class Meta:
        db_table = 'accion'
        verbose_name = 'Acción'
        verbose_name_plural = 'Acciones'
    
    def __str__(self):
        return f"{self.empresa} - {self.mercado}"

class ClienteAccion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    accion = models.ForeignKey(Accion, on_delete=models.CASCADE)
    fecha_compra = models.DateField()
    cantidad = models.IntegerField()
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'cliente_accion'
        unique_together = ('cliente', 'accion')
        verbose_name = 'Cliente-Acción'
        verbose_name_plural = 'Clientes-Acciones'
    
    def __str__(self):
        return f"{self.cliente.rut} - {self.accion.empresa}"
    
    def get_total_cost(self):
        return self.cantidad * self.precio_compra

class Calificacion(models.Model):
    corredora = models.ForeignKey(Corredora, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='calificaciones')
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    anno = models.IntegerField(null=True, blank=True)
    mercado = models.CharField(max_length=3, blank=True, null=True)
    instrumento = models.CharField(max_length=50, blank=True, null=True)
    fecha_pago = models.DateField(null=True, blank=True)
    secuencia_evento = models.IntegerField(null=True, blank=True)
    dividendo = models.IntegerField(null=True, blank=True)
    descripcion = models.CharField(max_length=50, blank=True, null=True)
    factor_actualizacion = models.DateField(null=True, blank=True)
    isfut = models.BooleanField(default=False)
    valor_historico = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ingreso_montos = models.BooleanField(default=False)
    
    # Factores tributarios (29 factores: factor8 a factor37)
    factor8 = models.IntegerField(null=True, blank=True)
    factor9 = models.IntegerField(null=True, blank=True)
    factor10 = models.IntegerField(null=True, blank=True)
    factor11 = models.IntegerField(null=True, blank=True)
    factor12 = models.IntegerField(null=True, blank=True)
    factor13 = models.IntegerField(null=True, blank=True)
    factor14 = models.IntegerField(null=True, blank=True)
    factor15 = models.IntegerField(null=True, blank=True)
    factor16 = models.IntegerField(null=True, blank=True)
    factor17 = models.IntegerField(null=True, blank=True)
    factor18 = models.IntegerField(null=True, blank=True)
    factor19 = models.IntegerField(null=True, blank=True)
    factor20 = models.IntegerField(null=True, blank=True)
    factor21 = models.IntegerField(null=True, blank=True)
    factor22 = models.IntegerField(null=True, blank=True)
    factor23 = models.IntegerField(null=True, blank=True)
    factor24 = models.IntegerField(null=True, blank=True)
    factor25 = models.IntegerField(null=True, blank=True)
    factor26 = models.IntegerField(null=True, blank=True)
    factor27 = models.IntegerField(null=True, blank=True)
    factor28 = models.IntegerField(null=True, blank=True)
    factor29 = models.IntegerField(null=True, blank=True)
    factor30 = models.IntegerField(null=True, blank=True)
    factor31 = models.IntegerField(null=True, blank=True)
    factor32 = models.IntegerField(null=True, blank=True)
    factor33 = models.IntegerField(null=True, blank=True)
    factor34 = models.IntegerField(null=True, blank=True)
    factor35 = models.IntegerField(null=True, blank=True)
    factor36 = models.IntegerField(null=True, blank=True)
    factor37 = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'calificacion'
        ordering = ['-created_at']
        verbose_name = 'Calificación'
        verbose_name_plural = 'Calificaciones'
    
    def __str__(self):
        return f"Calificación {self.id} - {self.cliente.rut} - {self.anno}"
