"""
Modelos optimizados para PostgreSQL - App: calificaciones
Incluye: índices, constraints, validaciones y campos específicos PostgreSQL

CAMBIOS PRINCIPALES:
- Índices compuestos para consultas frecuentes
- Constraints de negocio para validaciones
- Campo JSONB para metadatos adicionales
- Validaciones de RUT, rangos de factores
- Soft delete en Cliente
- Optimización de relaciones ManyToMany
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from usuarios.models import User, Corredora, validar_rut_chileno
from django.db.models import Q
from decimal import Decimal


class Cliente(models.Model):
    """
    Representa un cliente de la corredora (persona natural o jurídica).

    Un cliente puede ser:
    - Persona Natural (con extensión en PersonaNatural)
    - Persona Jurídica (con extensión en PersonaJuridica)

    Características: 
    - Soft delete (no se eliminan físicamente)
    - Cifrado de datos sensibles (rut, telefono, correo)
    - Validación de RUT chileno
    """

    # NOTA: Para producción, cifrar con django-cryptography
    rut = models.CharField(
        max_length=12,
        unique=True,
        validators=[validar_rut_chileno],
        help_text="RUT del cliente (formato: 12345678-9)",
        db_index=True
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Teléfono de contacto"
    )
    correo = models.EmailField(
        blank=True,
        null=True,
        help_text="Email de contacto"
    )

    # Soft delete
    activo = models.BooleanField(
        default=True,
        help_text="Si el cliente está activo (soft delete)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Fecha de eliminación lógica"
    )

    class Meta:
        db_table = 'cliente'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['rut']
        indexes = [
            models.Index(fields=['rut'], name='idx_cliente_rut'),
            models.Index(fields=['activo'], name='idx_cliente_activo'),
            models.Index(fields=['created_at'], name='idx_cliente_created'),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(rut__isnull=False) & ~Q(rut=''),
                name='chk_cliente_rut_no_vacio'
            )
        ]

    def __str__(self):
        return self.rut

    def get_nombre_completo(self) -> str:
        """
        Retorna el nombre completo del cliente.

        Returns:
            Nombre y apellido (persona natural) o razón social (persona jurídica)
        """
        if hasattr(self, 'persona_natural'):
            return f"{self.persona_natural.nombre} {self.persona_natural.apellido}"
        elif hasattr(self, 'persona_juridica'):
            return self.persona_juridica.razon_social
        else:
            return self.rut

    def es_persona_natural(self) -> bool:
        """Verifica si el cliente es persona natural."""
        return hasattr(self, 'persona_natural')

    def es_persona_juridica(self) -> bool:
        """Verifica si el cliente es persona jurídica."""
        return hasattr(self, 'persona_juridica')

    def soft_delete(self):
        """Realiza eliminación lógica del cliente."""
        from django.utils import timezone
        self.activo = False
        self.deleted_at = timezone.now()
        self.save()


class PersonaNatural(models.Model):
    """
    Extensión de Cliente para personas naturales.

    Relación OneToOne con Cliente.
    """

    cliente = models.OneToOneField(
        Cliente,
        on_delete=models.CASCADE,
        related_name='persona_natural',
        primary_key=True
    )
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre(s) de la persona"
    )
    apellido = models.CharField(
        max_length=100,
        help_text="Apellido(s) de la persona"
    )

    class Meta:
        db_table = 'persona_natural'
        verbose_name = 'Persona Natural'
        verbose_name_plural = 'Personas Naturales'
        indexes = [
            models.Index(fields=['nombre', 'apellido'], name='idx_pn_nombre_apellido'),
        ]

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class PersonaJuridica(models.Model):
    """
    Extensión de Cliente para personas jurídicas (empresas).

    Relación OneToOne con Cliente.
    """

    cliente = models.OneToOneField(
        Cliente,
        on_delete=models.CASCADE,
        related_name='persona_juridica',
        primary_key=True
    )
    razon_social = models.CharField(
        max_length=255,
        help_text="Razón social de la empresa"
    )
    domicilio_tributario = models.CharField(
        max_length=500,
        help_text="Dirección del domicilio tributario"
    )
    giro = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Giro o actividad económica"
    )

    class Meta:
        db_table = 'persona_juridica'
        verbose_name = 'Persona Jurídica'
        verbose_name_plural = 'Personas Jurídicas'
        indexes = [
            models.Index(fields=['razon_social'], name='idx_pj_razon_social'),
        ]

    def __str__(self):
        return self.razon_social


class Accion(models.Model):
    """
    Representa una acción bursátil negociada.

    CAMBIO: Ya no tiene FK directa a Cliente.
    La relación Cliente-Accion se maneja via ClienteAccion (ManyToMany explícita).
    """

    MERCADOS = [
        ('LOC', 'Mercado Local'),
        ('INT', 'Mercado Internacional'),
        ('EME', 'Mercado Emergente'),
    ]

    corredora = models.ForeignKey(
        Corredora,
        on_delete=models.CASCADE,
        related_name='acciones',
        help_text="Corredora que gestiona la acción"
    )
    nemotecnico = models.CharField(
        max_length=10,
        unique=True,
        help_text="Código nemotécnico de la acción (ej: SQM-B)"
    )
    empresa = models.CharField(
        max_length=255,
        help_text="Nombre de la empresa emisora"
    )
    mercado = models.CharField(
        max_length=3,
        choices=MERCADOS,
        help_text="Tipo de mercado donde se transa"
    )
    activa = models.BooleanField(
        default=True,
        help_text="Si la acción está disponible para transacciones"
    )

    class Meta:
        db_table = 'accion'
        verbose_name = 'Acción'
        verbose_name_plural = 'Acciones'
        ordering = ['nemotecnico']
        indexes = [
            models.Index(fields=['nemotecnico'], name='idx_accion_nemotecnico'),
            models.Index(fields=['corredora', 'activa'], name='idx_accion_corr_activa'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['corredora', 'nemotecnico'],
                name='unique_accion_por_corredora'
            )
        ]

    def __str__(self):
        return f"{self.empresa} ({self.nemotecnico}) - {self.get_mercado_display()}"


class ClienteAccion(models.Model):
    """
    Relación ManyToMany explícita entre Cliente y Accion.

    Almacena información de la compra de acciones por parte del cliente.
    """

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='cliente_acciones'
    )
    accion = models.ForeignKey(
        Accion,
        on_delete=models.CASCADE,
        related_name='cliente_acciones'
    )
    fecha_compra = models.DateField(
        help_text="Fecha de adquisición de las acciones"
    )
    cantidad = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Número de acciones adquiridas"
    )
    precio_compra = models.DecimalField(
        max_digits=15,  # Aumentado de 10 a 15 para valores más grandes
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Precio unitario de compra"
    )

    class Meta:
        db_table = 'cliente_accion'
        unique_together = [('cliente', 'accion', 'fecha_compra')]
        verbose_name = 'Cliente-Acción'
        verbose_name_plural = 'Clientes-Acciones'
        ordering = ['-fecha_compra']
        indexes = [
            models.Index(fields=['cliente', 'fecha_compra'], name='idx_ca_cliente_fecha'),
            models.Index(fields=['accion', 'fecha_compra'], name='idx_ca_accion_fecha'),
        ]

    def __str__(self):
        return f"{self.cliente.rut} - {self.accion.nemotecnico} ({self.cantidad} acciones)"

    def get_total_cost(self) -> Decimal:
        """
        Calcula el costo total de la compra.

        Returns:
            Decimal con el costo total (cantidad * precio_compra)
        """
        return self.cantidad * self.precio_compra


class Calificacion(models.Model):
    # Opciones
    MERCADO_CHOICES = [
        ('AC', 'Acciones'),
        ('CFI', 'CFI'),
    ]
    
    TIPO_SOCIEDAD_CHOICES = [
        ('A', 'Abierta (A)'),
        ('C', 'Cerrada (C)'),
    ]

    ESTADOS = [
        ('BORRADOR', 'Borrador'),
        ('REVISION', 'En Revisión'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
        ('ENVIADA_SII', 'Enviada al SII'),
    ]

    # Relaciones
    corredora = models.ForeignKey(
        Corredora,
        on_delete=models.CASCADE,
        related_name='calificaciones',
        help_text="Corredora responsable de la calificación",
        null=True, blank=True
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='calificaciones',
        help_text="Cliente al que pertenece la calificación"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='calificaciones_creadas',
        help_text="Usuario que creó/modificó la calificación"
    )

    # ==========================================
    # CAMPOS SEGÚN ARCHIVO DE CARGA (CSV 3.1)
    # ==========================================
    
    # 1. Ejercicio (Numero, 4)
    anno = models.IntegerField(
        verbose_name="Ejercicio",
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
        help_text="Año comercial (ej: 2025)"
    )

    # 2. Mercado (Texto, 3)
    mercado = models.CharField(
        max_length=3,
        choices=MERCADO_CHOICES,
        blank=True, null=True
    )

    # 3. Instrumento (Texto, 50)
    instrumento = models.CharField(
        max_length=50,
        blank=True, null=True
    )

    # 4. Fecha (Fecha, 10)
    fecha_pago = models.DateField(
        verbose_name="Fecha Pago",
        help_text="DD-MM-AAAA",
        null=True, blank=True
    )

    # 5. Secuencia (Numero, 10) - BigInteger para evitar desbordamiento
    secuencia_evento = models.BigIntegerField(
        verbose_name="Secuencia",
        null=True, blank=True,
        validators=[MinValueValidator(1)]
    )

    # 6. Numero de dividendo (Numero, 10) - NUEVO
    numero_dividendo = models.BigIntegerField(
        verbose_name="Número de dividendo",
        null=True, blank=True
    )

    # 7. Tipo sociedad (Texto, 1) - NUEVO
    tipo_sociedad = models.CharField(
        max_length=1,
        choices=TIPO_SOCIEDAD_CHOICES,
        null=True, blank=True
    )

    # 8. Valor Historico (Numero, 10) - Usamos 8 decimales por consistencia
    valor_historico = models.DecimalField(
        max_digits=15, 
        decimal_places=8, 
        default=0,
        null=True, blank=True
    )

    # ==========================================
    # CAMPOS DE LÓGICA DE NEGOCIO ADICIONALES
    # ==========================================

    # Factor de Actualización (Factor de Crédito)
    # Ejemplos: 0,142857 (Pyme), 0,369863 (Semiintegrado)
    factor_actualizacion = models.DecimalField(
        max_digits=10,
        decimal_places=6, # Suficiente para los ejemplos dados
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.000000'))],
        help_text="Factor de crédito (Ej: 0.142857 para Pyme)"
    )

    dividendo = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Monto monetario del dividendo"
    )
    
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    isfut = models.BooleanField(default=False, verbose_name="Aplica ISFUT")
    ingreso_montos = models.BooleanField(default=False)
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='BORRADOR'
    )

    # ==========================================
    # FACTORES TRIBUTARIOS (Factor 8 a 37)
    # Requerimiento 3.1: "1 entero, 8 decimales"
    # Max Digits: 10 (para permitir 1.00000000)
    # ==========================================
    factor8 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor9 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor10 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor11 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor12 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor13 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor14 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor15 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor16 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor17 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor18 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor19 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor20 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor21 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor22 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor23 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor24 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor25 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor26 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor27 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor28 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor29 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor30 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor31 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor32 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor33 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor34 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor35 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor36 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    factor37 = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'calificacion'
        ordering = ['-anno', '-created_at']
        indexes = [
            models.Index(fields=['corredora', 'anno']),
            models.Index(fields=['cliente', 'anno']),
            models.Index(fields=['estado']),
        ]

    def __str__(self):
        return f"{self.instrumento} ({self.anno})"
        
    def get_suma_factores(self) -> Decimal:
        """Suma de todos los factores 8-37 para validaciones."""
        factores = [
            self.factor8, self.factor9, self.factor10, self.factor11, self.factor12,
            self.factor13, self.factor14, self.factor15, self.factor16, self.factor17,
            self.factor18, self.factor19, self.factor20, self.factor21, self.factor22,
            self.factor23, self.factor24, self.factor25, self.factor26, self.factor27,
            self.factor28, self.factor29, self.factor30, self.factor31, self.factor32,
            self.factor33, self.factor34, self.factor35, self.factor36, self.factor37,
        ]
        return sum(f for f in factores if f is not None)