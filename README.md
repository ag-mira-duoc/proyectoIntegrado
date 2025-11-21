# NUAM - Sistema de Gestión de Calificaciones Tributarias

![Django](https://img.shields.io/badge/Django-5.2.7-green.svg)
![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

Sistema de gestión de calificaciones tributarias para corredoras de bolsa chilenas, basado en el modelo 1851 del SII (Servicio de Impuestos Internos).

## 📋 Índice

- [Descripción](#descripción)
- [Características Principales](#características-principales)
- [Tecnologías Utilizadas](#tecnologías-utilizadas)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Requisitos Previos](#requisitos-previos)
- [Instalación Local](#instalación-local)
- [Configuración](#configuración)
- [Deployment en Render](#deployment-en-render)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Modelos de Datos](#modelos-de-datos)
- [Sistema RBAC](#sistema-rbac)
- [API REST](#api-rest)
- [Testing](#testing)
- [Seguridad](#seguridad)
- [Contribución](#contribución)
- [Equipo](#equipo)
- [Licencia](#licencia)

---

## 📝 Descripción

**NUAM** es un sistema web desarrollado con Django para la gestión integral de calificaciones tributarias de clientes de corredoras de bolsa. Permite el registro, procesamiento, validación y auditoría de documentos tributarios según la normativa chilena (Formulario 1851 SII).

### Contexto Académico

Este proyecto es desarrollado como trabajo final del programa de **Analista Programador** por un equipo de 3 estudiantes, utilizando metodología **Kanban** y cumpliendo con los siguientes criterios de evaluación:

- ✅ Interfaces coherentes con el negocio
- ✅ Cumplimiento de lineamientos estéticos y funcionales
- ✅ Estructura de base de datos óptima (PostgreSQL)
- ✅ Normalización hasta 3FN
- ✅ Implementación de patrones de seguridad (OWASP Top 10)
- ✅ Control de acceso basado en roles (RBAC)
- ✅ Auditoría inmutable
- ✅ Plan de pruebas completo

---

## 🚀 Características Principales

### Funcionalidades Core

- **Gestión de Calificaciones Tributarias**: CRUD completo de calificaciones según formulario 1851 SII (30 factores)
- **Carga Masiva de Documentos**: Upload y procesamiento automático de múltiples PDFs
- **OCR con Tesseract**: Extracción automática de datos de documentos PDF
- **Arquitectura Híbrida**: PostgreSQL (datos) + Firebase Storage (PDFs)
- **Sistema de Auditoría Inmutable**: Trazabilidad completa de todas las operaciones
- **Control de Acceso Basado en Roles (RBAC)**: 3 roles (Administradores, Analistas, Auditores)
- **API REST con autenticación JWT**: Integración con otros sistemas
- **Dashboard Interactivo**: Visualización de estadísticas y reportes

### Características Técnicas

- **Multitenancy**: Aislamiento de datos por corredora
- **Procesamiento Asíncrono**: Celery + Redis para tareas pesadas (OCR, reportes)
- **Full-Text Search**: Búsqueda en documentos procesados (PostgreSQL)
- **Validación de RUT Chileno**: Validación automática con dígito verificador
- **Exportación de Datos**: CSV, Excel, PDF
- **Notificaciones por Email**: Sistema de alertas y recuperación de contraseña
- **Responsive Design**: Bootstrap 5 para móviles y tablets

---

## 🛠️ Tecnologías Utilizadas

### Backend

- **Django 5.2.7**: Framework web principal
- **Django REST Framework**: API RESTful
- **PostgreSQL 15+**: Base de datos principal
- **Redis**: Caché y broker de Celery
- **Celery**: Procesamiento asíncrono
- **Gunicorn**: Servidor WSGI para producción

### Frontend

- **Bootstrap 5**: Framework CSS
- **Django Template System**: Renderizado server-side
- **Django Crispy Forms**: Formularios estilizados
- **DataTables**: Tablas interactivas
- **Chart.js**: Gráficos y estadísticas

### Storage & Files

- **Firebase Storage**: Almacenamiento de PDFs
- **WhiteNoise**: Archivos estáticos en producción

### OCR & Processing

- **Tesseract OCR**: Extracción de texto de PDFs
- **pdf2image**: Conversión PDF a imágenes
- **Pillow**: Procesamiento de imágenes

### Seguridad

- **Django Axes**: Límite de intentos de login
- **django-cryptography**: Cifrado de campos sensibles
- **django-cors-headers**: Configuración CORS

### Testing

- **pytest**: Framework de testing
- **pytest-django**: Integración con Django
- **factory-boy**: Factories para testing
- **OWASP ZAP**: Testing de seguridad

### Deployment

- **Render**: Plataforma de hosting
- **Docker**: Containerización (opcional)
- **GitHub Actions**: CI/CD (opcional)

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│  Bootstrap 5 + Django Templates + JavaScript                │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                      DJANGO APP                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   usuarios   │  │calificaciones│  │  auditoria   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │ documentos   │  │      API     │                       │
│  │ (OCR + PDF)  │  │  (REST DRF)  │                       │
│  └──────────────┘  └──────────────┘                       │
└──────────┬─────────────────────┬────────────────────┬──────┘
           │                     │                    │
┌──────────▼──────┐   ┌──────────▼──────┐   ┌────────▼──────┐
│   PostgreSQL    │   │  Firebase       │   │    Redis      │
│   (Metadatos)   │   │  Storage (PDFs) │   │ (Cache+Celery)│
└─────────────────┘   └─────────────────┘   └───────────────┘
           │                     │                    │
┌──────────▼─────────────────────▼────────────────────▼──────┐
│                      CELERY WORKERS                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ OCR Worker   │  │Report Worker │  │ Email Worker │     │
│  │ (Tesseract)  │  │ (Exportación)│  │ (SendGrid)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Procesamiento OCR

```
1. Usuario carga PDF → Django guarda en Firebase Storage
2. Se crea registro en PostgreSQL con url_firebase
3. Trigger PostgreSQL notifica cambio via NOTIFY
4. Celery task inicia procesamiento:
   a. Descarga PDF de Firebase
   b. Convierte PDF a imágenes (pdf2image)
   c. Aplica Tesseract OCR a cada página
   d. Extrae datos estructurados (regex para campos)
   e. Valida contra esquema esperado
   f. Crea/actualiza Calificacion en PostgreSQL
   g. Registra en auditoría
5. Si confianza < 80%, marca para revisión manual
```

---

## 📦 Requisitos Previos

### Software Requerido

- **Python 3.11+**
- **PostgreSQL 15+**
- **Redis 7+** (para Celery y caché)
- **Tesseract OCR** (para procesamiento de documentos)
- **Poppler** (para pdf2image)
- **Git**

### Instalación de Dependencias del Sistema

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    postgresql \
    postgresql-contrib \
    libpq-dev \
    redis-server \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    git
```

#### macOS (Homebrew)

```bash
brew install python@3.11 postgresql@15 redis tesseract tesseract-lang poppler git
brew services start postgresql@15
brew services start redis
```

#### Windows

1. **Python**: Descargar desde [python.org](https://www.python.org/downloads/)
2. **PostgreSQL**: Descargar desde [postgresql.org](https://www.postgresql.org/download/windows/)
3. **Redis**: Descargar desde [GitHub](https://github.com/microsoftarchive/redis/releases)
4. **Tesseract**: Descargar desde [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
5. **Poppler**: Descargar desde [GitHub](https://github.com/oschwartz10612/poppler-windows/releases/)

---

## 💻 Instalación Local

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/proyectoIntegrado.git
cd proyectoIntegrado
```

### 2. Crear Entorno Virtual

```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# o
venv\Scripts\activate  # Windows
```

### 3. Instalar Dependencias de Python

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurar Base de Datos PostgreSQL

```bash
# Acceder a PostgreSQL
sudo -u postgres psql

# Crear base de datos y usuario
CREATE DATABASE nuam_db;
CREATE USER nuam_user WITH PASSWORD 'nuam_password_2025';
ALTER ROLE nuam_user SET client_encoding TO 'utf8';
ALTER ROLE nuam_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE nuam_user SET timezone TO 'America/Santiago';
GRANT ALL PRIVILEGES ON DATABASE nuam_db TO nuam_user;
\q
```

### 5. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus credenciales
nano .env  # o tu editor favorito
```

Variables mínimas requeridas:

```env
SECRET_KEY=tu_clave_secreta_generada
DEBUG=True
DATABASE_URL=postgresql://nuam_user:nuam_password_2025@localhost:5432/nuam_db
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 6. Aplicar Migraciones

```bash
python manage.py migrate
```

### 7. Crear Superusuario

```bash
python manage.py createsuperuser
```

### 8. Crear Grupos de RBAC

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import Group

# Crear grupos
Group.objects.get_or_create(name='Administradores')
Group.objects.get_or_create(name='Analistas')
Group.objects.get_or_create(name='Auditores')
exit()
```

### 9. Recolectar Archivos Estáticos

```bash
python manage.py collectstatic --noinput
```

### 10. Iniciar Servidor de Desarrollo

```bash
python manage.py runserver
```

Acceder a: http://127.0.0.1:8000/

### 11. Iniciar Celery (en otra terminal)

```bash
# Activar entorno virtual
source venv/bin/activate

# Iniciar worker
celery -A nuam_config worker --loglevel=info

# En otra terminal, iniciar beat (tareas programadas)
celery -A nuam_config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

## ⚙️ Configuración

### Configuración de Firebase Storage

1. **Crear proyecto en Firebase Console**: https://console.firebase.google.com/
2. **Habilitar Firebase Storage**
3. **Descargar credenciales** (JSON file):
   - Settings → Service Accounts → Generate New Private Key
4. **Guardar archivo** como `firebase-credentials.json` en la raíz del proyecto
5. **Configurar en `.env`**:

```env
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
FIREBASE_STORAGE_BUCKET=tu-proyecto.appspot.com
```

### Configuración de Email

Para notificaciones y recuperación de contraseña:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_email@gmail.com
EMAIL_HOST_PASSWORD=tu_app_password
DEFAULT_FROM_EMAIL=NUAM Sistema <noreply@nuam.cl>
```

**Nota**: Para Gmail, usar **App Passwords**, no contraseña normal.

### Configuración de Tesseract

Verificar ruta de Tesseract:

```bash
which tesseract  # Linux/macOS
where tesseract  # Windows
```

Configurar en `.env`:

```env
TESSERACT_CMD=/usr/bin/tesseract  # Tu ruta
```

---

## 🚀 Deployment en Render

### Preparación

1. **Commitear cambios**:

```bash
git add .
git commit -m "Preparar para deployment en Render"
git push origin main
```

2. **Crear cuenta en Render**: https://render.com/

### Deployment Automático (Recomendado)

Render detectará automáticamente el archivo `render.yaml`:

1. **Dashboard → New → Blueprint**
2. **Conectar repositorio GitHub**
3. **Seleccionar rama** (main)
4. **Render creará automáticamente**:
   - Web Service (Django)
   - PostgreSQL Database
   - Celery Workers

### Configuración Manual de Variables

En Render Dashboard → tu servicio → Environment:

```
SECRET_KEY=<generada automáticamente>
DEBUG=false
ALLOWED_HOSTS=tu-app.onrender.com
FIREBASE_CREDENTIALS_JSON=<JSON completo>
EMAIL_HOST_USER=<tu email>
EMAIL_HOST_PASSWORD=<tu contraseña>
```

### Crear Redis

1. **Dashboard → New → Redis**
2. **Nombre**: nuam-redis
3. **Plan**: Starter (gratuito)
4. **Vincular** a web service y workers

### Post-Deployment

```bash
# Acceder a Shell en Render
python manage.py createsuperuser
python manage.py shell

# Crear grupos RBAC
from django.contrib.auth.models import Group
Group.objects.get_or_create(name='Administradores')
Group.objects.get_or_create(name='Analistas')
Group.objects.get_or_create(name='Auditores')
```

---

## 📁 Estructura del Proyecto

```
proyectoIntegrado/
├── nuam_config/              # Configuración principal de Django
│   ├── __init__.py
│   ├── settings.py           # Configuración (usar settings_postgres.py)
│   ├── settings_postgres.py  # ✅ Configuración optimizada para PostgreSQL
│   ├── urls.py               # URLs principales
│   ├── wsgi.py
│   ├── asgi.py
│   └── context_processors.py # Context processors personalizados
│
├── usuarios/                 # App de usuarios y autenticación
│   ├── models.py             # Modelos: User, Corredora
│   ├── models_optimized.py   # ✅ Modelos optimizados para PostgreSQL
│   ├── views.py
│   ├── admin.py
│   ├── urls.py
│   └── migrations/
│
├── calificaciones/           # App principal (CRUD calificaciones)
│   ├── models.py             # Modelos: Cliente, Calificacion, Accion
│   ├── models_optimized.py   # ✅ Modelos optimizados con índices
│   ├── views.py
│   ├── serializers.py        # Serializers para API REST
│   ├── admin.py
│   ├── urls.py
│   └── migrations/
│
├── auditoria/                # App de auditoría inmutable
│   ├── models.py             # Modelo: LogAuditoria
│   ├── models_optimized.py   # ✅ Modelo con inmutabilidad y JSONB
│   ├── views.py
│   ├── admin.py
│   └── migrations/
│
├── documentos/               # App de documentos y OCR
│   ├── models.py             # ✅ Modelos: Documento, CargaMasiva
│   ├── views.py
│   ├── tasks.py              # Tareas Celery para OCR
│   ├── admin.py
│   └── migrations/
│
├── templates/                # Templates HTML globales
│   ├── base.html             # Template base con Bootstrap 5
│   ├── navbar.html
│   ├── sidebar.html
│   └── ...
│
├── static/                   # Archivos estáticos (CSS, JS, imágenes)
│   ├── css/
│   ├── js/
│   └── img/
│
├── media/                    # Uploads de usuarios (generado)
├── logs/                     # Logs de Django (generado)
├── staticfiles/              # Archivos estáticos recolectados (generado)
│
├── .env.example              # ✅ Ejemplo de variables de entorno
├── .gitignore                # ✅ Archivos ignorados por git
├── requirements.txt          # ❌ Dependencias (UTF-16, deprecado)
├── requirements_new.txt      # ✅ Dependencias actualizadas
├── render.yaml               # ✅ Configuración para Render
├── README.md                 # ✅ Este archivo
├── manage.py                 # CLI de Django
└── pytest.ini                # Configuración de pytest
```

---

## 📊 Modelos de Datos

### Diagrama ER Simplificado

```
Corredora (1) ──────── (N) User
   │                         │
   │                         │
   (N)                      (N)
   │                         │
Calificacion ─────────── LogAuditoria
   │
   │ (N)
   │
Cliente (1:1) PersonaNatural
        (1:1) PersonaJuridica
   │
   │ (N:M via ClienteAccion)
   │
Accion
```

### Modelos Principales

#### User (usuarios.models)

```python
- corredora: FK → Corredora
- email: EmailField (unique, login)
- rut: CharField (unique, validado)
- nombre, apellido: CharField
- groups: ManyToMany → Group (RBAC)
```

#### Calificacion (calificaciones.models)

```python
- corredora: FK → Corredora
- cliente: FK → Cliente
- user: FK → User
- anno: IntegerField
- factor8 a factor37: DecimalField (30 factores)
- estado: CharField (BORRADOR, APROBADA, etc.)
- created_at, updated_at: DateTimeField
```

#### LogAuditoria (auditoria.models)

```python
- calificacion: FK → Calificacion
- user: FK → User
- accion: CharField (CREATE, UPDATE, DELETE, VIEW)
- valores_anteriores: JSONField
- valores_nuevos: JSONField
- ip_address: GenericIPAddressField
- fecha: DateTimeField
```

#### Documento (documentos.models)

```python
- calificacion: FK → Calificacion
- usuario_carga: FK → User
- url_firebase: URLField
- texto_extraido: TextField (OCR)
- datos_extraidos: JSONField
- estado: CharField (PENDIENTE, PROCESANDO, COMPLETADO)
```

---

## 🔐 Sistema RBAC

### Roles Definidos

| Rol                 | Permisos                                   |
|---------------------|--------------------------------------------|
| **Administradores** | Acceso completo al sistema                 |
| **Analistas**       | CRUD de calificaciones, carga masiva       |
| **Auditores**       | Solo lectura de calificaciones y logs      |

### Implementación

Los roles se implementan usando **Django Groups**:

```python
# Verificar rol en vista
@login_required
@user_passes_test(lambda u: u.groups.filter(name='Analistas').exists())
def crear_calificacion(request):
    ...

# Verificar rol en template
{% if is_analista %}
    <a href="{% url 'calificaciones:crear' %}">Nueva Calificación</a>
{% endif %}
```

---

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Con cobertura
pytest --cov=. --cov-report=html

# Test específico
pytest usuarios/tests/test_models.py

# Tests en paralelo
pytest -n auto
```

### Tipos de Tests

1. **Tests Unitarios** (`test_models.py`, `test_forms.py`)
2. **Tests de Integración** (`test_views.py`, `test_api.py`)
3. **Tests de Seguridad** (OWASP ZAP, bandit)
4. **Tests de Rendimiento** (Locust, JMeter)

### Cobertura Objetivo

- **Mínimo**: 80%
- **Objetivo**: 90%+

---

## 🔒 Seguridad

### Medidas Implementadas

#### OWASP Top 10

| Amenaza           | Mitigación                                    |
|-------------------|-----------------------------------------------|
| SQL Injection     | Django ORM (sin raw queries)                  |
| XSS               | Template auto-escaping                        |
| CSRF              | Django CSRF middleware + tokens               |
| Auth Rota         | django-axes (límite 5 intentos)               |
| Control Acceso    | RBAC con Django Groups                        |
| Config Insegura   | Variables de entorno (.env)                   |
| Datos Sensibles   | django-cryptography (RUT, email, teléfono)    |
| Deserialización   | No usar pickle, solo JSON                     |
| Componentes       | Actualizar dependencias regularmente          |
| Logging           | Logs completos de seguridad                   |

#### Headers de Seguridad (Producción)

```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

#### Auditoría Inmutable

- Todos los cambios en calificaciones se registran en `LogAuditoria`
- No se puede actualizar ni eliminar logs (protegido a nivel de modelo y trigger PostgreSQL)
- Retención: 5 años (Ley 19.628 Chile)

---

## 👥 Equipo

Proyecto desarrollado por estudiantes del programa **Analista Programador**:

- **[Nombre 1]** - Desarrollador Backend
- **[Nombre 2]** - Desarrollador Frontend
- **[Nombre 3]** - Testing & QA

**Institución**: [Nombre de la institución]
**Período**: [Año académico]
**Metodología**: Kanban

---

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

---

## 🙏 Agradecimientos

- Servicio de Impuestos Internos (SII) de Chile por la documentación del formulario 1851
- Comunidad de Django por el excelente framework
- Render por la plataforma de hosting

---

## 📞 Contacto

Para consultas sobre el proyecto:

- **Email**: contacto@nuam.cl
- **GitHub**: https://github.com/tu-usuario/proyectoIntegrado
- **Documentación**: https://docs.nuam.cl

---

## 📚 Recursos Adicionales

- [Documentación de Django](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Celery Docs](https://docs.celeryproject.org/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [Render Docs](https://render.com/docs)

---

**Última actualización**: Noviembre 2025
