from django.db import models

class Documento(models.Model):
    calificacion = models.ForeignKey('calificaciones.Calificacion', models.DO_NOTHING)
    cliente = models.ForeignKey('clientes.Cliente', models.DO_NOTHING)
    user = models.ForeignKey('usuarios.User', models.DO_NOTHING)
    tipo = models.CharField(max_length=255)
    archivo = models.CharField(max_length=255)
    fecha_emision = models.DateField()
    fecha_ingreso = models.DateField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'documento'
