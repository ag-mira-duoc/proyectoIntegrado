from celery import shared_task
from .models import Documento
import pytesseract
from pdf2image import convert_from_path

@shared_task(bind=True)
def procesar_documento_ocr(self, documento_id):
    documento = Documento.objects.get(id=documento_id)
    documento.marcar_como_procesando(self.request.id)

    try:
        # 1. Descargar PDF de Firebase
        # 2. Convertir a imágenes
        # 3. Aplicar OCR
        # 4. Extraer datos
        # 5. Guardar resultados

        documento.marcar_como_completado(texto, datos, confianza)
    except Exception as e:
        documento.marcar_como_error(str(e))