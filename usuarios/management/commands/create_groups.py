# usuarios/management/commands/create_groups.py
# Crear carpeta: usuarios/management/commands/

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from calificaciones.models import Calificacion

class Command(BaseCommand):
    help = 'Crea grupos de usuarios y asigna permisos'

    def handle(self, *args, **kwargs):
        # Obtener el ContentType de Calificacion
        calificacion_ct = ContentType.objects.get_for_model(Calificacion)
        
        # Permisos disponibles
        permisos_calificacion = Permission.objects.filter(content_type=calificacion_ct)
        
        # ===== GRUPO: Administradores =====
        admin_group, created = Group.objects.get_or_create(name='Administradores')
        if created:
            # Asignar TODOS los permisos
            admin_group.permissions.set(Permission.objects.all())
            self.stdout.write(
                self.style.SUCCESS('✓ Grupo "Administradores" creado con todos los permisos')
            )
        
        # ===== GRUPO: Analistas =====
        analista_group, created = Group.objects.get_or_create(name='Analistas')
        if created:
            # Pueden crear, ver y modificar sus propias calificaciones
            permisos_analista = Permission.objects.filter(
                content_type=calificacion_ct,
                codename__in=['add_calificacion', 'view_calificacion', 'change_calificacion']
            )
            analista_group.permissions.set(permisos_analista)
            self.stdout.write(
                self.style.SUCCESS('✓ Grupo "Analistas" creado')
            )
        
        # ===== GRUPO: Lectores =====
        auditor_group, created = Group.objects.get_or_create(name='Auditores')
        if created:
            # Solo pueden ver calificaciones
            permisos_auditor = Permission.objects.filter(
                content_type=calificacion_ct,
                codename='view_calificacion'
            )
            auditor_group.permissions.set(permisos_auditor)
            self.stdout.write(
                self.style.SUCCESS('✓ Grupo "Auditores creado')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\n¡Grupos creados exitosamente!')
        )
        self.stdout.write('Grupos disponibles:')
        for group in Group.objects.all():
            self.stdout.write(f'  - {group.name} ({group.permissions.count()} permisos)')