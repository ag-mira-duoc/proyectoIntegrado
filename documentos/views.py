from django.shortcuts import render, redirect
from django.contrib import messages
from .services import gestionar_carga_documento

def subir_documento_view(request):
    if request.method == 'POST':
        # Verificamos si viene el archivo
        if 'file' in request.FILES:
            archivo = request.FILES['file']
            try:
                # Llamamos a tu servicio que sube a Azure y procesa OCR
                gestionar_carga_documento(
                    archivo_memoria=archivo,
                    usuario=request.user,
                    tipo_doc='CERT_70' # O lo que venga del request.POST.get('tipo')
                )
                messages.success(request, f"Documento {archivo.name} cargado y procesando.")
                return redirect('nombre_de_tu_url_de_lista') # Cambia esto por tu URL de destino
            except Exception as e:
                messages.error(request, f"Error al subir: {str(e)}")
        else:
            messages.error(request, "No se seleccionó ningún archivo.")

    return render(request, 'documentos/tu_template_de_carga.html')