from rest_framework import serializers
from rest_framework.validators import ValidationError
from rest_framework.authtoken.models import Token
from acciones.models import Corredora
from .models import User

class SignupSerializer(serializers.ModelSerializer):
    email = serializers.CharField(max_length=80)
    rut = serializers.CharField(max_length=11)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(min_length=8, write_only=True)
    password2 = serializers.CharField(min_length=8, write_only=True)

    corredora = serializers.PrimaryKeyRelatedField(
        queryset=Corredora.objects.all(), 
        required=True,
        allow_null=False
    )

    class Meta:
        model = User
        fields = ['email', 'rut', 'first_name', 'last_name','corredora', 'password', 'password2']
    
    def validate(self, attrs):
        email_exists = User.objects.filter(email=attrs['email']).exists()
        if email_exists:
            raise ValidationError("Correo en uso.")
        
        rut_exists = User.objects.filter(rut=attrs['rut']).exists()
        if rut_exists:
            raise ValidationError("RUT en uso.")
        
        if attrs['password'] != attrs['password2']:
            raise ValidationError("Las contraseñas no coinciden.")

        return super().validate(attrs)
    
    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop("password")
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=password,
            rut=validated_data['rut'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            corredora=validated_data.get('corredora')
        )
    
        return user

class CurrentUserCalificacionesSerializer(serializers.ModelSerializer):
    calificaciones = serializers.HyperlinkedRelatedField(
        many=True, 
        view_name="calificacion_detail", 
        queryset=User.objects.all()
    )

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'calificaciones']

class CorredoraApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Corredora
        fields = ['nombre', 'telefono', 'direccion']

class UserApprovalSerializer(serializers.ModelSerializer):
    nueva_corredora = CorredoraApprovalSerializer(write_only=True, required=False)
    approve = serializers.BooleanField(write_only=True, required=False)
    reject = serializers.BooleanField(write_only=True, required=False)
    
    corredora_nombre = serializers.CharField(source='corredora.nombre', read_only=True)
    date_joined_formatted = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'rut', 'first_name', 'last_name', 
            'corredora', 'corredora_nombre', 'is_active', 'is_staff',
            'date_joined', 'date_joined_formatted',
            'nueva_corredora', 'approve', 'reject'
        ]
        read_only_fields = ('email', 'rut', 'first_name', 'last_name', 'is_staff', 'date_joined')

    def get_date_joined_formatted(self, obj):
        return obj.date_joined.strftime('%d-%m-%Y %H:%M') if obj.date_joined else ''

    def update(self, instance, validated_data):
        nueva_corredora_data = validated_data.pop('nueva_corredora', None)
        approve_status = validated_data.pop('approve', None)
        reject_status = validated_data.pop('reject', None)

        if nueva_corredora_data:
            corredora = Corredora.objects.create(**nueva_corredora_data)
            instance.corredora = corredora

        if approve_status is True:
            #instance.is_active = True
            #instance.save()
            pass
        
        if reject_status is True:
            instance.delete()
            return instance
        
        return super().update(instance, validated_data)
