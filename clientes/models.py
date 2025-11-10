from django.db import models

class Cliente(models.Model):
    rut = models.CharField(unique=True, max_length=255)
    telefono = models.CharField(max_length=255, blank=True, null=True)
    correo = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'cliente'

class PersonaNatural(models.Model):
    cliente = models.ForeignKey(Cliente, models.DO_NOTHING)
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'persona_natural'

class PersonaJuridica(models.Model):
    cliente = models.ForeignKey(Cliente, models.DO_NOTHING)
    razon_social = models.CharField(max_length=255)
    domicilio_tributario = models.CharField(max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'persona_juridica'
