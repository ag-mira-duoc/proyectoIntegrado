from celery import shared_task
from django.conf import settings
from .models import Documento
import requests
import tempfile
import os

@shared_task(bind=True)
def procesar_documento_ocr(self, documento_id):
    # Obtenemos el objeto documento
    documento = Documento.objects.get(id=documento_id)
    
    # Marcamos inicio del proceso
    documento.marcar_como_procesando(self.request.id)

    try:
        # ---------------------------------------------------------
        # 1. Obtener el archivo (Simulación de descarga de Firebase)
        # ---------------------------------------------------------
        # NOTA: Asumimos que documento.url_firebase es accesible públicamente
        # o es una URL firmada. Si es privada, necesitarías usar firebase-admin aquí.
        
        print(f"Descargando archivo desde: {documento.url_firebase}")
        response_pdf = requests.get(documento.url_firebase)
        response_pdf.raise_for_status() # Lanza error si falla la descarga

        # Creamos un archivo temporal para enviarlo a la API
        # Es necesario porque 'requests' necesita un archivo físico o un stream con nombre
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(response_pdf.content)
            tmp_path = tmp_file.name

        # ---------------------------------------------------------
        # 2. Enviar a tu API de Docling (vía Ngrok)
        # ---------------------------------------------------------
        print(f"Enviando a Docling API: {settings.DOCLING_API_URL}")
        
        with open(tmp_path, 'rb') as f:
            # 'file' debe coincidir con el parámetro en tu main.py de FastAPI
            files = {'file': (documento.nombre_archivo, f, 'application/pdf')}
            response_api = requests.post(settings.DOCLING_API_URL, files=files, timeout=300)
        
        # Limpieza del temporal local
        os.unlink(tmp_path)

        # ---------------------------------------------------------
        # 3. Procesar Respuesta
        # ---------------------------------------------------------
        if response_api.status_code == 200:
            result = response_api.json()
            
            # Extraemos el markdown de la respuesta de tu API
            texto_procesado = result.get("content", "")
            
            # Como Docling devuelve estructura completa, podríamos guardar
            # el JSON completo en datos_extraidos si tu API lo devolviera.
            datos_raw = result 
            
            # Asignamos confianza arbitraria (Docling es IA, no suele dar % global simple como Tesseract)
            # Podrías modificar tu API para calcularla o dejarla fija en 100 por ahora.
            confianza = 95.0 

            # Guardamos en la BD usando tu método del modelo
            documento.marcar_como_completado(
                texto_extraido=texto_procesado,
                datos_extraidos=datos_raw,
                confianza=confianza
            )
            print(f"Documento {documento_id} procesado exitosamente.")
            
        else:
            raise Exception(f"Error API Docling ({response_api.status_code}): {response_api.text}")

    except Exception as e:
        print(f"Error procesando documento: {str(e)}")
        # Registramos el error en el modelo
        documento.marcar_como_error(str(e))