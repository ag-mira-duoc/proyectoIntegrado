import os
import json
import time
import re
import google.generativeai as genai
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from decouple import config

# Configura la API
api_key = getattr(settings, 'GOOGLE_API_KEY', None) or config('GOOGLE_API_KEY', default=os.getenv('GOOGLE_API_KEY'))
genai.configure(api_key=api_key)

def limpiar_moneda_ai(valor):
    """Convierte respuestas numéricas de la IA a Decimal."""
    if not valor: return Decimal(0)
    if isinstance(valor, (int, float)): return Decimal(str(valor))
    
    val_str = str(valor).strip().replace('$', '').replace(' ', '')
    
    # Manejo de formatos numéricos (1.000,00 vs 1000.00)
    if ',' in val_str and '.' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
        
    try:
        return Decimal(val_str)
    except:
        return Decimal(0)

def normalizar_a_decimal(valor):
    """
    CORRECCIÓN DE DESBORDAMIENTO:
    Si el valor es > 99 (limite de la BD numeric(10,8)), lo divide
    para convertirlo en un coeficiente decimal (0.XXXX).
    Ej: 52960217.0 -> 0.52960217
    """
    try:
        if not valor: 
            return Decimal(0)
            
        # Aseguramos que trabajamos con Decimal
        valor_dec = Decimal(str(valor))
        
        # Si el valor ya es aceptable (menor a 100), lo devolvemos tal cual
        # Usamos 90 por seguridad, aunque el límite teórico es 99.
        if abs(valor_dec) < 90:
            return valor_dec

        # Convertimos a string la parte entera para contar cuántos dígitos tiene
        parte_entera = int(abs(valor_dec))
        digitos = len(str(parte_entera))
        
        # Dividimos por 10 elevado a la cantidad de dígitos
        divisor = Decimal('10') ** digitos
        valor_corregido = valor_dec / divisor
        
        return valor_corregido
        
    except (ValueError, TypeError, Exception):
        return Decimal(0)

def procesar_archivo_pdf(archivo_memoria):
    """
    Procesa el PDF usando el modelo 'gemini-1.5-flash' con instrucciones 
    estrictas de mapeo de columnas para evitar duplicidad F8/F9 y confusión F27.
    """
    print(f"--- INICIANDO PROCESAMIENTO CON GEMINI FLASH (MODO TOTALES ESTRICTO) ---")
    
    try:
        # Usamos flash por velocidad y costo, suficiente para extracción de tablas
        model = genai.GenerativeModel(
            model_name="gemini-flash-latest", 
            generation_config={"response_mime_type": "application/json"}
        )

        # Preparar archivo
        if hasattr(archivo_memoria, 'read'):
            if hasattr(archivo_memoria, 'seek'):
                archivo_memoria.seek(0)
            pdf_bytes = archivo_memoria.read()
        else:
            pdf_bytes = archivo_memoria

        # --- PROMPT CORREGIDO Y ESTRICTO ---
        prompt = """
        Actúa como un contador auditor experto. Analiza el Certificado Tributario N° 70 adjunto.
        Tu misión es extraer SOLO la fila final de "Totales" (suma anual) y mapear las columnas EXACTAS a los factores tributarios definidos abajo.

        ### INSTRUCCIONES DE EXTRACCIÓN:

        1. **METADATA:**
           - Año Comercial: Busca "por el año comercial YYYY".
           - RUT Cliente: Busca el RUT del titular del certificado.

        2. **MAPEO DE COLUMNAS (CRÍTICO):**
           Debes buscar la fila inferior que dice "Totales" (o "Tos" por error de OCR) en cada página y extraer los valores según estos encabezados exactos:

           **PÁGINA 1 (Base Imponible):**
           - **factor8**: Extrae el valor de la columna titulada "Monto Con crédito por IDPC..." (o similar que indique crédito acumulado desde 2017).
           - **factor9**: Extrae el valor de la columna "Sin derecho a crédito" (generalmente a la derecha del factor 8). **SI LA CELDA ESTÁ VACÍA O ES CERO, DEVUELVE 0. NO DUPLIQUES EL VALOR DEL FACTOR 8 AQUI.**
           
           **PÁGINA 2 (Créditos):**
           - **factor25**: Busca la columna bajo "No sujetos a restitución" -> subtitulo "Con derecho a devolución".
           - **factor26**: Busca la columna bajo "Sujetos a restitución" -> subtitulo "Sin derecho a devolución".
           - **factor27**: Busca la columna bajo "Sujetos a restitución" -> subtitulo "Con derecho a devolución". (En el ejemplo visual, aquí suele haber un monto grande como 19.588.026).
           
           **NOTA:** Si una columna no tiene valor en la fila de totales, su valor es 0.

        3. **SALIDA JSON:**
           Retorna un ÚNICO objeto JSON. Estructura obligatoria:

        {
            "metadata": { "rut_emisor": "XX.XXX.XXX-X", "anno_comercial": 2023 },
            "cliente": { "rut": "XX.XXX.XXX-X", "nombre": "NOMBRE", "tipo_persona": "juridica" },
            "filas": [
                {
                    "fecha_pago": "31/12/2023",
                    "instrumento": "RESUMEN TOTALES ANUAL",
                    "numero_dividendo": 0,
                    "factor8": 0.0,
                    "factor9": 0.0,   // OJO: No copiar F8 aqui
                    "factor25": 0.0,  // No sujetos a restitución - Con derecho
                    "factor26": 0.0,  // Sujetos a restitución - Sin derecho
                    "factor27": 0.0   // Sujetos a restitución - Con derecho
                }
            ]
        }
        """

        # Lógica de Reintentos
        max_intentos = 3
        for intento in range(max_intentos):
            try:
                response = model.generate_content([
                    {"mime_type": "application/pdf", "data": pdf_bytes},
                    prompt
                ])
                
                print(f"Respuesta IA exitosa (intento {intento+1})")
                data = json.loads(response.text)
                break 

            except Exception as e:
                error_msg = str(e).lower()
                if ("429" in error_msg or "quota" in error_msg or "503" in error_msg) and intento < max_intentos - 1:
                    time.sleep(2 * (intento + 1))
                    continue
                else:
                    raise e

        # --- PROCESAMIENTO DE RESPUESTA ---
        meta = data.get('metadata', {})
        anno_detectado = meta.get('anno_comercial')
        if not anno_detectado: anno_detectado = datetime.now().year - 1

        datos_retorno = {
            'tipo': 'C70',
            'metadata': {'rut_emisor': meta.get('rut_emisor'), 'anno': int(anno_detectado)},
            'cliente_detectado': data.get('cliente', {}),
            'filas': [],
            'error': None
        }

        # Procesar filas y limpiar números
        for f in data.get('filas', []):
            fecha_final = f.get('fecha_pago')
            if not fecha_final or str(anno_detectado) not in str(fecha_final):
                fecha_final = f"31/12/{anno_detectado}"

            fila_clean = {
                'ingreso_montos': False,
                'fecha_pago': fecha_final,
                'instrumento': 'RESUMEN TOTALES ANUAL',
                'numero_dividendo': 0,
                'descripcion': 'Carga Masiva IA',
                'isfut': False 
            }
            
            # Mapeo dinámico de factores (F8 a F37)
            # Inicializamos todos en 0 primero
            for i in range(8, 38):
                fila_clean[f'factor{i}'] = Decimal(0)

            # Sobrescribimos con lo que trajo la IA
            for k, v in f.items():
                if k.startswith('factor'):
                    # Extraer el numero del key (ej: "factor8" -> 8)
                    try:
                        num_factor = int(re.search(r'\d+', k).group())
                        if 8 <= num_factor <= 37:
                            # 1. Limpiamos símbolos y comas
                            val_limpio = limpiar_moneda_ai(v)
                            # 2. APLICAMOS CORRECCIÓN DE DESBORDAMIENTO (NORMALIZAR)
                            val_final = normalizar_a_decimal(val_limpio)
                            
                            fila_clean[f'factor{num_factor}'] = val_final
                    except:
                        pass
            
            # Corrección manual de seguridad por si la IA falló en la instrucción negativa
            # Si F9 es exactamente igual a F8 y F8 no es 0, asumimos error de duplicación y limpiamos F9
            if fila_clean['factor9'] == fila_clean['factor8'] and fila_clean['factor8'] > 0:
                 fila_clean['factor9'] = Decimal(0)

            datos_retorno['filas'].append(fila_clean)
            
        return datos_retorno

    except Exception as e:
        print(f"ERROR CRÍTICO: {e}")
        return {'error': str(e), 'filas': [], 'cliente_detectado': {}}