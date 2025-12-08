# 1. Usar una imagen base oficial de Python
FROM python:3.11-slim

# 2. Configurar variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Instalar dependencias del sistema (Tesseract, Poppler, etc.)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 4. Establecer el directorio de trabajo
WORKDIR /app

# 5. Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# 6. Copiar el resto del código
COPY . .

# 7. Recolectar estáticos
RUN python manage.py collectstatic --noinput

# 8. COMANDO DE INICIO (ACTUALIZADO)
# Orden de ejecución: 
# 1. Migraciones -> 2. Crear Superusuario -> 3. Iniciar Gunicorn
CMD sh -c "python manage.py migrate && python crear_admin.py && gunicorn nuam_config.wsgi:application --bind 0.0.0.0:$PORT"