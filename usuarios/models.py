"""
Modelos optimizados para PostgreSQL - App: usuarios
Incluye: índices, constraints, validaciones y preparación para cifrado

CAMBIOS PRINCIPALES:
- Índices compuestos para consultas frecuentes
- Validador de RUT chileno
- Preparación para cifrado de datos sensibles (rut, email)
- Eliminación de campos redundantes (logged_in, user_token)
- Integración con Django Groups para RBAC
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group
from django.core.validators import RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import re


def validar_rut_chileno(rut: str) -> None:
    """
    Valida formato y dígito verificador de RUT chileno.

    Formato esperado: 12345678-9 o 12.345.678-9

    Args:
        rut: String con RUT a validar

    Raises:
        ValidationError: Si el RUT no es válido
    """
    # Limpiar puntos y guiones
    rut_limpio = rut.replace(".", "").replace("-", "")

    if len(rut_limpio) < 2:
        raise ValidationError("RUT debe tener al menos 2 caracteres")

    # Separar número y dígito verificador
    numero = rut_limpio[:-1]
    dv_ingresado = rut_limpio[-1].upper()

    # Validar que el número sea numérico
    if not numero.isdigit():
        raise ValidationError("El número del RUT debe ser numérico")

    # Calcular dígito verificador
    suma = 0
    multiplo = 2

    for digito in reversed(numero):
        suma += int(digito) * multiplo
        multiplo += 1
        if multiplo > 7:
            multiplo = 2

    resto = suma % 11
    dv_calculado = 11 - resto

    if dv_calculado == 11:
        dv_esperado = '0'
    elif dv_calculado == 10:
        dv_esperado = 'K'
    else:
        dv_esperado = str(dv_calculado)

    if dv_ingresado != dv_esperado:
        raise ValidationError(f"Dígito verificador incorrecto. Se esperaba {dv_esperado}")


class Corredora(models.Model):
    """
    Representa una corredora de bolsa registrada en el sistema.

    Cada corredora puede tener múltiples usuarios y gestionar múltiples clientes.
    Los datos están aislados por corredora (multitenancy).
    """
    nombre = models.CharField(
        max_length=255,
        unique=True,  # Nuevo: nombre único
        help_text="Razón social de la corredora"
    )
    # NOTA: Para producción, cifrar con django-cryptography
    telefono = models.CharField(
        max_length=20,  # Reducido de 255 a 20
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?56?[0-9]{8,9}$',
                message='Formato de teléfono chileno inválido. Ejemplo: +56912345678'
            )
        ],
        help_text="Teléfono de contacto (formato chileno)"
    )
    direccion = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Dirección física de la corredora"
    )
    email_contacto = models.EmailField(
        blank=True,
        null=True,
        help_text="Email de contacto general"
    )
    activa = models.BooleanField(
        default=True,
        help_text="Si la corredora está activa en el sistema"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'corredora'
        verbose_name = 'Corredora'
        verbose_name_plural = 'Corredoras'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre'], name='idx_corr_nombre'),
            models.Index(fields=['activa'], name='idx_corr_activa'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(nombre__isnull=False) & ~models.Q(nombre=''),
                name='chk_corredora_nombre_no_vacio'
            )
        ]

    def __str__(self):
        return self.nombre


class UserManager(BaseUserManager):
    """
    Manager personalizado para el modelo User.

    Maneja la creación de usuarios normales y superusuarios.
    """

    def create_user(self, email: str, password: str = None, **extra_fields) -> 'User':
        """
        Crea y guarda un usuario normal.

        Args:
            email: Email del usuario (usado como username)
            password: Contraseña en texto plano (será hasheada)
            **extra_fields: Campos adicionales (rut, nombre, apellido, etc.)

        Returns:
            Instancia de User creada

        Raises:
            ValueError: Si no se proporciona email
        """
        if not email:
            raise ValueError('El email es obligatorio')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str = None, **extra_fields) -> 'User':
        """
        Crea y guarda un superusuario.

        Args:
            email: Email del superusuario
            password: Contraseña en texto plano
            **extra_fields: Campos adicionales

        Returns:
            Instancia de User con privilegios de superusuario
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuario debe tener is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuario debe tener is_superuser=True')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Modelo de usuario personalizado para el sistema NUAM.

    Características:
    - Autenticación por email (no username)
    - Asociado a una corredora (multitenancy)
    - Roles manejados por Django Groups ('Administradores', 'Analistas', 'Auditores')
    - Campos sensibles preparados para cifrado

    RBAC (Control de Acceso Basado en Roles):
    - Administradores: Gestión completa del sistema
    - Analistas Tributarios: CRUD de calificaciones
    - Auditores: Solo lectura de calificaciones y logs
    """

    # Relación con corredora (multitenancy)
    corredora = models.ForeignKey(
        Corredora,
        on_delete=models.PROTECT,
        related_name='usuarios',
        null=True,
        blank=True,
        help_text="Corredora a la que pertenece el usuario (opcional para superusuarios)"
    )

    # Campos de identificación
    # NOTA: Para producción, cifrar email y rut con django-cryptography
    email = models.EmailField(
        unique=True,
        help_text="Email del usuario (usado para login)"
    )
    rut = models.CharField(
        max_length=12,  # Formato: 12.345.678-9
        unique=True,
        validators=[validar_rut_chileno],
        help_text="RUT chileno con formato: 12345678-9"
    )
    nombre = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(2)],
        help_text="Nombre(s) del usuario"
    )
    apellido = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(2)],
        help_text="Apellido(s) del usuario"
    )

    # Campos de estado
    is_active = models.BooleanField(
        default=True,
        help_text="Si el usuario puede acceder al sistema"
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Si el usuario puede acceder al admin de Django"
    )

    # Timestamps
    date_joined = models.DateTimeField(
        default=timezone.now,
        help_text="Fecha de registro en el sistema"
    )
    last_login = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Último login exitoso"
    )

    # Manager personalizado
    objects = UserManager()

    # Configuración de autenticación
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['rut', 'nombre', 'apellido']

    class Meta:
        db_table = 'users'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['apellido', 'nombre']
        indexes = [
            models.Index(fields=['email'], name='idx_user_email'),
            models.Index(fields=['rut'], name='idx_user_rut'),
            models.Index(fields=['corredora', 'is_active'], name='idx_user_corr_active'),
            models.Index(fields=['last_login'], name='idx_user_last_login'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(email__isnull=False) & ~models.Q(email=''),
                name='chk_user_email_no_vacio'
            ),
            models.CheckConstraint(
                check=models.Q(rut__isnull=False) & ~models.Q(rut=''),
                name='chk_user_rut_no_vacio'
            ),
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.email})"

    def get_full_name(self) -> str:
        """Retorna nombre completo del usuario."""
        return f"{self.nombre} {self.apellido}"

    def get_short_name(self) -> str:
        """Retorna nombre corto del usuario."""
        return self.nombre

    def get_rol(self) -> str:
        """
        Retorna el rol principal del usuario basado en Django Groups.

        Returns:
            String con el rol: 'Administrador', 'Analista', 'Auditor' o 'Sin Rol'
        """
        grupos = self.groups.values_list('name', flat=True)

        if 'Administradores' in grupos:
            return 'Administrador'
        elif 'Analistas' in grupos:
            return 'Analista Tributario'
        elif 'Auditores' in grupos:
            return 'Auditor'
        else:
            return 'Sin Rol'

    def es_administrador(self) -> bool:
        """Verifica si el usuario tiene rol de Administrador."""
        return self.groups.filter(name='Administradores').exists()

    def es_analista(self) -> bool:
        """Verifica si el usuario tiene rol de Analista."""
        return self.groups.filter(name='Analistas').exists()

    def es_auditor(self) -> bool:
        """Verifica si el usuario tiene rol de Auditor."""
        return self.groups.filter(name='Auditores').exists()


# NOTA: El modelo TipoUsuario está DEPRECADO
# Usar Django Groups para RBAC en su lugar
# Grupos a crear:
# - Administradores: Gestión completa
# - Analistas: CRUD de calificaciones
# - Auditores: Solo lectura

"""
Para crear los grupos en una migración de datos:

from django.db import migrations

def crear_grupos_rbac(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    # Crear grupos
    admin_group, _ = Group.objects.get_or_create(name='Administradores')
    analista_group, _ = Group.objects.get_or_create(name='Analistas')
    auditor_group, _ = Group.objects.get_or_create(name='Auditores')

    # Asignar permisos según necesidad
    # (ver documentación de implementación RBAC)

class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_grupos_rbac),
    ]
"""
