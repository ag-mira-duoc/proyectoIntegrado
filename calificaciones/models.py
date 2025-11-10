from django.db import models

class Calificacion(models.Model):
    corredora = models.ForeignKey('acciones.Corredora', models.DO_NOTHING)
    cliente = models.ForeignKey('clientes.Cliente', models.DO_NOTHING)
    user = models.ForeignKey('usuarios.User', models.DO_NOTHING, related_name="calificaciones")
    anno = models.IntegerField(blank=True, null=True)
    mercado = models.CharField(max_length=3, blank=True, null=True)
    instrumento = models.CharField(max_length=50, blank=True, null=True)
    fecha_pago = models.DateField(blank=True, null=True)
    secuencia_evento = models.IntegerField(blank=True, null=True)
    dividendo = models.IntegerField(blank=True, null=True)
    descripcion = models.CharField(max_length=50, blank=True, null=True)
    factor_actualizacion = models.DateTimeField(auto_now=True)
    isfut = models.IntegerField(blank=True, null=True)
    valor_historico = models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True)
    ingreso_montos = models.IntegerField(blank=True, null=True)

    # Factores tributarios
    factor8 = models.IntegerField(blank=True, null=True)
    factor9 = models.IntegerField(blank=True, null=True)
    factor10 = models.IntegerField(blank=True, null=True)
    factor11 = models.IntegerField(blank=True, null=True)
    factor12 = models.IntegerField(blank=True, null=True)
    factor13 = models.IntegerField(blank=True, null=True)
    factor14 = models.IntegerField(blank=True, null=True)
    factor15 = models.IntegerField(blank=True, null=True)
    factor16 = models.IntegerField(blank=True, null=True)
    factor17 = models.IntegerField(blank=True, null=True)
    factor18 = models.IntegerField(blank=True, null=True)
    factor19 = models.IntegerField(blank=True, null=True)
    factor20 = models.IntegerField(blank=True, null=True)
    factor21 = models.IntegerField(blank=True, null=True)
    factor22 = models.IntegerField(blank=True, null=True)
    factor23 = models.IntegerField(blank=True, null=True)
    factor24 = models.IntegerField(blank=True, null=True)
    factor25 = models.IntegerField(blank=True, null=True)
    factor26 = models.IntegerField(blank=True, null=True)
    factor27 = models.IntegerField(blank=True, null=True)
    factor28 = models.IntegerField(blank=True, null=True)
    factor29 = models.IntegerField(blank=True, null=True)
    factor30 = models.IntegerField(blank=True, null=True)
    factor31 = models.IntegerField(blank=True, null=True)
    factor32 = models.IntegerField(blank=True, null=True)
    factor33 = models.IntegerField(blank=True, null=True)
    factor34 = models.IntegerField(blank=True, null=True)
    factor35 = models.IntegerField(blank=True, null=True)
    factor36 = models.IntegerField(blank=True, null=True)
    factor37 = models.IntegerField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'calificacion'
        ordering = ['-created']
        verbose_name = 'Calificación'
        verbose_name_plural = 'Calificaciones'
    
    def __str__(self):
        return f"Calificación {self.id} - {self.cliente.rut} - {self.anno}"
