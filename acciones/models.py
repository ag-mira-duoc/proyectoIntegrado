from django.db import models

class Corredora(models.Model):
    nombre = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=255, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'corredora'

class Accion(models.Model):
    cliente = models.ForeignKey('clientes.Cliente', models.DO_NOTHING)
    corredora = models.ForeignKey('Corredora', models.DO_NOTHING)
    empresa = models.CharField(max_length=255)
    mercado = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'accion'

class ClienteAccion(models.Model):
    pk = models.CompositePrimaryKey('cliente_id', 'accion_id')
    cliente = models.ForeignKey('clientes.Cliente', models.DO_NOTHING)
    accion = models.ForeignKey(Accion, models.DO_NOTHING)
    fecha_compra = models.DateField()
    cantidad = models.IntegerField()
    precio_compra = models.DecimalField(max_digits=10, decimal_places=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'cliente_accion'