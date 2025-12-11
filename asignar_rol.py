"""
Script para asignar un rol a un usuario.

Ejecutar con:
    python manage.py shell < asignar_rol.py

O copiar y pegar en el shell de Django.
"""

from usuarios.models import User
from django.contrib.auth.models import Group

# CONFIGURACIÓN: Cambia estos valores
EMAIL_USUARIO = 'admin@example.com'  # Email del usuario
ROL = 'Administradores'  # Opciones: Administradores, Analistas, Auditores

print("\n" + "=" * 60)
print("ASIGNAR ROL A USUARIO")
print("=" * 60)

try:
    # Buscar usuario
    usuario = User.objects.get(email=EMAIL_USUARIO)
    print(f"✅ Usuario encontrado: {usuario.get_full_name()} ({usuario.email})")
    
    # Buscar grupo
    grupo = Group.objects.get(name=ROL)
    print(f"✅ Grupo encontrado: {grupo.name}")
    
    # Asignar rol
    usuario.groups.add(grupo)
    print(f"\n✅ Rol '{ROL}' asignado a {usuario.get_full_name()}")
    
    # Mostrar roles actuales del usuario
    print(f"\n📋 Roles de {usuario.get_full_name()}:")
    for g in usuario.groups.all():
        print(f"  - {g.name}")
    
except User.DoesNotExist:
    print(f"❌ ERROR: Usuario con email '{EMAIL_USUARIO}' no encontrado")
    print("\nUsuarios disponibles:")
    for u in User.objects.all()[:10]:
        print(f"  - {u.email} ({u.get_full_name()})")

except Group.DoesNotExist:
    print(f"❌ ERROR: Grupo '{ROL}' no encontrado")
    print("\nGrupos disponibles:")
    for g in Group.objects.all():
        print(f"  - {g.name}")

print("\n" + "=" * 60 + "\n")
