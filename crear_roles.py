"""
Script para crear los grupos RBAC del sistema NUAM.

Ejecutar con:
    python manage.py shell < crear_roles.py

O copiar y pegar en:
    python manage.py shell
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

print("=" * 60)
print("CREANDO GRUPOS RBAC PARA NUAM")
print("=" * 60)

# Crear los 3 grupos principales
grupos = [
    ('Administradores', 'Acceso completo al sistema'),
    ('Analistas', 'Gestión de calificaciones y clientes'),
    ('Auditores', 'Solo lectura de calificaciones y logs'),
]

for nombre, descripcion in grupos:
    grupo, created = Group.objects.get_or_create(name=nombre)
    if created:
        print(f"✅ Grupo '{nombre}' creado - {descripcion}")
    else:
        print(f"ℹ️  Grupo '{nombre}' ya existe")

print("\n" + "=" * 60)
print("GRUPOS CREADOS EXITOSAMENTE")
print("=" * 60)

# Mostrar grupos existentes
print("\nGrupos disponibles:")
for grupo in Group.objects.all().order_by('name'):
    usuarios_count = grupo.user_set.count()
    print(f"  - {grupo.name} ({usuarios_count} usuarios)")

print("\n" + "=" * 60)
print("PERMISOS RECOMENDADOS (configurar en Django Admin)")
print("=" * 60)
print("""
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

print("\n✅ Script completado exitosamente\n")
