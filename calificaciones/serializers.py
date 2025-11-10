from rest_framework import serializers
from .models import Calificacion

class CalificacionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    corredora_nombre = serializers.CharField(source='corredora.nombre', read_only=True)
    cliente_rut = serializers.CharField(source='cliente.rut', read_only=True)
    
    class Meta:
        model = Calificacion
        fields = [
            'id',
            'anno',
            'mercado',
            'instrumento',
            'fecha_pago',
            'secuencia_evento',
            'dividendo',
            'descripcion',
            'factor_actualizacion',
            'isfut',
            'valor_historico',
            'ingreso_montos',
            'factor8', 'factor9', 'factor10', 'factor11', 'factor12',
            'factor13', 'factor14', 'factor15', 'factor16', 'factor17',
            'factor18', 'factor19', 'factor20', 'factor21', 'factor22',
            'factor23', 'factor24', 'factor25', 'factor26', 'factor27',
            'factor28', 'factor29', 'factor30', 'factor31', 'factor32',
            'factor33', 'factor34', 'factor35', 'factor36', 'factor37',
            'created',
            'user_email',
            'corredora_nombre',
            'cliente_rut',
        ]
        read_only_fields = ['id', 'created', 'user_email', 'corredora_nombre', 'cliente_rut']
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            pass
        return super().create(validated_data)