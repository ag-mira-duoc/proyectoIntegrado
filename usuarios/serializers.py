from rest_framework import serializers
from rest_framework.validators import ValidationError
from rest_framework.authtoken.models import Token
from .models import User

class SignupSerializer(serializers.ModelSerializer):
    email = serializers.CharField(max_length=80)
    rut = serializers.CharField(max_length=11)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(min_length=8, write_only=True)

    class Meta:
        model = User
        fields = ['email', 'rut', 'first_name', 'last_name', 'password']
    
    def validate(self, attrs):
        email_exists = User.objects.filter(email=attrs['email']).exists()
        if email_exists:
            raise ValidationError("Correo en uso.")
        
        rut_exists = User.objects.filter(rut=attrs['rut']).exists()
        if rut_exists:
            raise ValidationError("RUT en uso.")

        return super().validate(attrs)
    
    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data['username'] = validated_data['email']
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        Token.objects.create(user=user)
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