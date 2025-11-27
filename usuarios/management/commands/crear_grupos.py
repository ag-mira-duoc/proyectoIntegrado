"""
Management command para crear los grupos RBAC del sistema NUAM.

Uso:
    python manage.py crear_grupos
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Crea los grupos RBAC para el sistema NUAM'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("CREANDO GRUPOS RBAC PARA NUAM"))
        self.stdout.write("=" * 60)

        # Definir grupos
        grupos = [
            ('Administradores', 'Acceso completo al sistema'),
            ('Analistas', 'Gestión de calificaciones y clientes'),
            ('Auditores', 'Solo lectura de calificaciones y logs'),
        ]

        # Crear grupos
        for nombre, descripcion in grupos:
            grupo, created = Group.objects.get_or_create(name=nombre)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Grupo '{nombre}' creado - {descripcion}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"ℹ️  Grupo '{nombre}' ya existe")
                )

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("GRUPOS CREADOS EXITOSAMENTE"))
        self.stdout.write("=" * 60)

        # Mostrar resumen
        self.stdout.write("\n📊 Grupos disponibles:")
        for grupo in Group.objects.all().order_by('name'):
            usuarios_count = grupo.user_set.count()
            self.stdout.write(f"  - {grupo.name} ({usuarios_count} usuarios)")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("PERMISOS RECOMENDADOS (configurar en Django Admin)")
        self.stdout.write("=" * 60)
        self.stdout.write("""
ADMINISTRADORES:
  - Todos los permisos

ANALISTAS:
  - calificaciones: add, change, view
  - clientes: add, change, view  
  - personanatural: add, change, view
  - personajuridica: add, change, view

AUDITORES:
  - calificaciones: view
  - clientes: view
  - logs de auditoría: view
        """)

        self.stdout.write("\n" + self.style.SUCCESS("✅ Listo para usar!\n"))
