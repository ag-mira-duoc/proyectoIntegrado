import os
import django

# Configurar el entorno de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nuam_config.settings")
django.setup()

from django.contrib.auth import get_user_model

def crear_superusuario():
    User = get_user_model()
    
    email = os.getenv('ADMIN_EMAIL', 'correo@correo.cl')
    password = os.getenv('ADMIN_PASSWORD', 'ContrasenaSegura123')
    rut = '19237573-8'
    
    if not User.objects.filter(email=email).exists():
        print(f"Creando superusuario: {email}...")
        try:
            User.objects.create_superuser(
                email=email,
                password=password,
                rut=rut,
                nombre='Administrador',
                apellido='Sistema'
            )
            print("Superusuario creado exitosamente.")
        except Exception as e:
            print(f"Error al crear superusuario: {e}")
    else:
        print("El superusuario ya existe. Omitiendo creación.")

if __name__ == "__main__":
    crear_superusuario()