import os
import uuid
from django.utils import timezone
from .models import Documento
from nuam_config.azure_config import get_container_client

from calificaciones.services import procesar_archivo_pdf 

def gestionar_carga_documento(archivo_memoria, usuario, tipo_doc='CERT_70', calificacion=None):
    
    # 1. Definir ruta única (blob name)
    ext = os.path.splitext(archivo_memoria.name)[1]
    nombre_blob = f"{usuario.id}/{timezone.now().strftime('%Y/%m')}/{uuid.uuid4()}{ext}"
    
    # Asegurar puntero al inicio
    archivo_memoria.seek(0)

    # 2. Subir a Azure Blob Storage
    try:
        container_client = get_container_client()
        from azure.storage.blob import ContentSettings
        
        blob_client = container_client.upload_blob(
            name=nombre_blob,
            data=archivo_memoria,
            content_settings=ContentSettings(content_type=archivo_memoria.content_type),
            overwrite=True
        )
        url_base = blob_client.url 

    except Exception as e:
        print(f"Error subiendo a Azure: {e}")
        raise e

    # 3. Crear registro en BD
    doc = Documento.objects.create(
        usuario_carga=usuario,
        calificacion=calificacion,
        tipo_documento=tipo_doc,
        nombre_archivo=archivo_memoria.name,
        tamaño_bytes=archivo_memoria.size,
        firebase_path=nombre_blob,
        url_firebase=url_base,
        estado='PROCESANDO'
    )

    try:
        # 4. Procesar OCR
        # IMPORTANTE: Rebobinar el archivo porque upload_blob lo leyó hasta el final
        archivo_memoria.seek(0) 
        
        # Llamamos a la función pura que está en calificaciones/services.py
        resultado_extraccion = procesar_archivo_pdf(archivo_memoria)
        
        if 'error' in resultado_extraccion:
            doc.marcar_como_error(resultado_extraccion['error'])
        else:
            confianza = 100.0 if resultado_extraccion.get('factores') else 0.0
            doc.marcar_como_completado(
                texto_extraido=str(resultado_extraccion),
                datos_extraidos=resultado_extraccion,
                confianza=confianza
            )
            
    except Exception as e:
        doc.marcar_como_error(str(e))
        print(f"Error procesando OCR doc {doc.id}: {e}")

    return doc