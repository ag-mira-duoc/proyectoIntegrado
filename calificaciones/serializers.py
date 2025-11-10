from rest_framework import serializers
from .models import Calificacion

class CalificacionSerializer(serializers.ModelSerializer):
    anno = serializers.IntegerField()
    mercado = serializers.CharField(max_length=3)
    instrumento = serializers.CharField(max_length=50)
    fecha_pago = serializers.DateField()
    secuencia_evento = serializers.IntegerField()
    dividendo = serializers.IntegerField()
    descripcion = serializers.CharField(max_length=50)
    factor_actualizacion = serializers.DateField()
    isfut = serializers.IntegerField()
    valor_historico = serializers.DecimalField(max_digits=10, decimal_places=0)
    
    class Meta:
        model = Calificacion
        fields = [
            'id', 'anno', 'mercado', 'instrumento', 'fecha_pago', 
            'secuencia_evento', 'dividendo', 'descripcion', 
            'factor_actualizacion', 'isfut', 'valor_historico', 
            'ingreso_montos', 'created'
        ]