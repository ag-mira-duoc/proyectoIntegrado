from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

class Corredora(models.Model):
    nombre = models.CharField(max_length=255)
    telefono = models.CharField(max_length=255, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'corredora'
        verbose_name = 'Corredora'
        verbose_name_plural = 'Corredoras'
    
    def __str__(self):
        return self.nombre

class TipoUsuario(models.Model):
    descripcion = models.CharField(max_length=255)
    
    class Meta:
        db_table = 'tipo_usuario'
        verbose_name = 'Tipo de Usuario'
        verbose_name_plural = 'Tipos de Usuario'
    
    def __str__(self):
        return self.descripcion

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    corredora = models.ForeignKey(Corredora, on_delete=models.PROTECT, related_name='usuarios')
    tipo_usuario = models.ForeignKey(TipoUsuario, on_delete=models.PROTECT, null=True, blank=True)
    email = models.EmailField(unique=True)
    rut = models.CharField(max_length=255, unique=True)
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    logged_in = models.BooleanField(default=False)
    user_token = models.CharField(max_length=255, blank=True, null=True)
    token_expiration = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['rut', 'nombre', 'apellido']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.email})"
