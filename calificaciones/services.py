import os
import re
import csv
import io
import requests
from decimal import Decimal
from datetime import datetime
from django.conf import settings

# Configuración URL Docling
DOCLING_API_URL = getattr(settings, 'DOCLING_API_URL', 'http://localhost:8000/convert')

FACTOR_DIVISOR = Decimal('100000000')

def normalizar_a_decimal(valor):
    if valor is None: return Decimal(0)
    val_str = str(valor).strip().replace('"', '').replace("'", "").replace('\n', '').replace('\r', '')
    
    # Remover separadores de miles pero preservar decimales
    val_str = val_str.replace('$ ', '').replace('$', '').replace('_', '')
    
    if not val_str or val_str == '|': return Decimal(0)

    # Detectar formato: usar último separador como decimal
    if '.' in val_str and ',' in val_str:
        if val_str.rfind('.') > val_str.rfind(','):
            clean_val = val_str.replace('.', '').replace(',', '.')
        else:
            clean_val = val_str.replace(',', '')
    elif ',' in val_str:
        partes = val_str.split(',')
        if len(partes[-1]) <= 2:
            clean_val = val_str.replace(',', '.')
        else:
            clean_val = val_str.replace(',', '')
    elif '.' in val_str:
        if val_str.count('.') > 1:
            clean_val = val_str.replace('.', '')
        else:
            partes = val_str.split('.')
            if len(partes[-1]) <= 2 and len(partes[0]) > 3:
                clean_val = val_str.replace('.', '')
            else:
                clean_val = val_str
    else:
        clean_val = val_str

    try:
        clean_val = "".join(c for c in clean_val if c.isdigit() or c == '.' or c == '-')
        return Decimal(clean_val) if clean_val else Decimal(0)
    except:
        return Decimal(0)

def formatear_decimal_frontend(decimal_val):
    try: return "{:,.0f}".format(decimal_val).replace(',', '.')
    except: return "0"

def extraer_metadata_de_texto(texto_completo):
    print("\n[METADATA] Extrayendo cabecera...")
    meta = {
        'rut_emisor': '', 'nombre_emisor': 'No Detectado',
        'fecha_certificado': '', 'anno_comercial': datetime.now().year - 1,
        'secuencia': ''
    }
    if not texto_completo: return meta

    match_emisor = re.search(r'(?:Nombre o Razón Social|Señor\(es\))\s*[:\.]?\s*(.*?)\s*[:\.]?\s*RUT', texto_completo, re.IGNORECASE)
    if match_emisor: meta['nombre_emisor'] = match_emisor.group(1).split(':')[0].strip()

    rut_match = re.search(r'(\d{1,2}\.\d{3}\.\d{3}-[\dkK])', texto_completo)
    if rut_match:
        rut = rut_match.group(1)
        if "95.319.000-1" not in rut: meta['rut_emisor'] = rut

    match_anno = re.search(r'año comercial\s*[:\.]?\s*(20\d{2})', texto_completo, re.IGNORECASE)
    if match_anno: meta['anno_comercial'] = int(match_anno.group(1))
    
    match_sec = re.search(r'Certificado\s*N[°o]\s*(\d+)', texto_completo, re.IGNORECASE)
    if match_sec: meta['secuencia'] = match_sec.group(1)
        
    meses = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
             'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}
    
    patron_fecha_texto = r'(?:[a-zA-Z\s\.]+,)?\s*(\d{1,2})\s+(?:de\s+)?([a-zA-Z]+)\s+de\s+(\d{4})'
    match_fecha_txt = re.search(patron_fecha_texto, texto_completo, re.IGNORECASE)
    
    if match_fecha_txt:
        dia, mes_str, anio = int(match_fecha_txt.group(1)), match_fecha_txt.group(2).lower(), match_fecha_txt.group(3)
        mes_num = meses.get(mes_str)
        if mes_num:
            meta['fecha_certificado'] = f"{dia:02d}/{mes_num:02d}/{anio}"

    if not meta['fecha_certificado']:
        fechas = re.findall(r'(\d{2}[/-]\d{2}[/-]\d{4})', texto_completo[:1500])
        if fechas: meta['fecha_certificado'] = fechas[-1]

    return meta

def parsear_fila_markdown_pipes(fila_texto):
    """
    Parsea una fila Markdown con pipes, manejando saltos de línea dentro de celdas.
    Ejemplo: "| val1 | val2\ncon salto | val3 |" -> ["val1", "val2 con salto", "val3"]
    """
    # Remover pipes del inicio/fin
    fila_limpia = fila_texto.strip()
    if fila_limpia.startswith('|'):
        fila_limpia = fila_limpia[1:]
    if fila_limpia.endswith('|'):
        fila_limpia = fila_limpia[:-1]
    
    # Split por pipe, pero mantener contenido
    celdas_raw = fila_limpia.split('|')
    
    # Limpiar cada celda
    celdas = []
    for celda in celdas_raw:
        # Reemplazar saltos de línea por espacios
        celda_limpia = celda.replace('\n', ' ').replace('\r', ' ')
        # Normalizar espacios múltiples
        celda_limpia = re.sub(r'\s+', ' ', celda_limpia).strip()
        celdas.append(celda_limpia)
    
    return celdas

def extraer_valores_numericos_de_celdas(celdas):
    """
    Extrae valores numéricos de una lista de celdas.
    Retorna lista de Decimals en el orden de las celdas.
    """
    valores = []
    
    for celda in celdas:
        val = normalizar_a_decimal(celda)
        valores.append(val)
    
    return valores

def obtener_filas_normalizadas(texto_completo):
    """
    Parsea contenido Markdown con tablas (pipes) o CSV
    """
    filas_resultado = []
    
    # Detectar si es Markdown con pipes
    tiene_pipes = texto_completo.count('|') > 10
    
    if tiene_pipes:
        print("[DEBUG] Formato Markdown con pipes detectado")
        lineas = texto_completo.split('\n')
        
        for linea in lineas:
            linea = linea.strip()
            if not linea or not '|' in linea:
                continue
            
            # Ignorar líneas separadoras (----)
            if re.match(r'^\|[\s\-:]+\|$', linea):
                continue
            
            # Parsear la fila
            celdas = parsear_fila_markdown_pipes(linea)
            if celdas:
                filas_resultado.append(celdas)
        
        return filas_resultado
    
    # Fallback: CSV Parser
    try:
        f = io.StringIO(texto_completo)
        reader = csv.reader(f, delimiter=',', quotechar='"')
        filas_csv = list(reader)
        
        if len(filas_csv) > 10:
            print(f"[DEBUG] CSV detectado: {len(filas_csv)} filas")
            
            for row in filas_csv:
                max_subfilas = 1
                for cell in row:
                    if cell.strip():
                        max_subfilas = max(max_subfilas, cell.count('\n') + 1)
                
                if max_subfilas > 1:
                    sub_filas = [[''] * len(row) for _ in range(max_subfilas)]
                    for col_idx, cell in enumerate(row):
                        partes = [p.strip() for p in cell.split('\n')]
                        for i in range(max_subfilas):
                            if i < len(partes):
                                sub_filas[i][col_idx] = partes[i]
                    filas_resultado.extend(sub_filas)
                else:
                    filas_resultado.append(row)
            
            return filas_resultado
    except Exception as e:
        print(f"[DEBUG] CSV parser falló: {e}")
    
    # Fallback final: texto plano
    print("[DEBUG] Usando parser de texto plano")
    lineas = texto_completo.split('\n')
    for linea in lineas:
        linea = linea.strip()
        if not linea: continue
        
        parts = re.split(r'\s{2,}', linea)
        if len(parts) > 1:
            filas_resultado.append(parts)
        else:
            filas_resultado.append([linea])
    
    return filas_resultado

def procesar_archivo_pdf(archivo_memoria):
    print(f"\n{'='*70}")
    print("PROCESANDO PDF - VERSIÓN CON PARSER DE MARKDOWN MEJORADO (FIX TABLA 2)")
    print(f"{'='*70}")
    
    response_data = {
        'ejercicio': '', 'mercado': 'ACN', 'instrumento': '', 
        'fecha_pago': '', 'secuencia': '',
        'valor_historico': '0', 'factor_actualizacion': '0', 'numero_dividendo': '0',      
        'factores': {}
    }

    try:
        if hasattr(archivo_memoria, 'seek'): 
            archivo_memoria.seek(0)
        
        files = {'file': ('upload.pdf', archivo_memoria, 'application/pdf')}
        
        try:
            response = requests.post(DOCLING_API_URL, files=files, timeout=120)
            response.raise_for_status()
        except Exception as e: 
            raise Exception(f"Error Docling: {e}")

        data = response.json()
        texto_completo = data.get("content") or data.get("markdown") or str(data)
        
        # DEBUG: Guardar muestra más grande
        print("\n[DEBUG] Muestra del contenido (primeros 800 chars):")
        print(texto_completo[:800])
        print("...")
        
        # 1. METADATA
        meta = extraer_metadata_de_texto(texto_completo)
        response_data['ejercicio'] = str(meta['anno_comercial'])
        response_data['instrumento'] = meta['nombre_emisor']
        response_data['fecha_pago'] = meta['fecha_certificado'] or f"31/12/{meta['anno_comercial']}"
        response_data['secuencia'] = meta['secuencia'] or "0"

        # Inicializar factores
        for i in range(8, 38):
            response_data['factores'][i] = {
                'desc': f'Factor {i}', 
                'valor': '0', 
                'valor_decimal': '0'
            }

        # 2. OBTENER FILAS NORMALIZADAS
        filas_procesadas = obtener_filas_normalizadas(texto_completo)
        
        tablas_encontradas = 0 
        ultima_fila_datos = None
        
        print(f"\n[DEBUG] Total filas procesadas: {len(filas_procesadas)}")

        for idx_fila, celdas in enumerate(filas_procesadas):
            if not celdas: continue
            
            texto_fila = " ".join(str(c) for c in celdas).upper()
            es_total = "TOTAL" in texto_fila
            
            # Convertir celdas a valores numéricos
            valores_fila = extraer_valores_numericos_de_celdas(celdas)
            tiene_datos = any(v > 0 for v in valores_fila)
            
            # Capturar datos de filas normales (con fechas)
            tiene_fecha = any(re.search(r'\d{2}/\d{2}/\d{4}', str(c)) for c in celdas)
            
            if not es_total and tiene_fecha and tiene_datos:
                ultima_fila_datos = valores_fila
                # Factor de Actualización (cerca de 1.0)
                for i, v in enumerate(valores_fila):
                    if 0.9 <= v <= 1.5 and i > 2: 
                        response_data['factor_actualizacion'] = str(v)
                        break
                if len(valores_fila) > 1:
                    response_data['numero_dividendo'] = str(int(valores_fila[1]))
            
            # PROCESAMIENTO DE FILAS "TOTALES"
            if es_total:
                tablas_encontradas += 1
                
                print(f"\n{'='*70}")
                print(f"TABLA #{tablas_encontradas} DETECTADA (Fila {idx_fila})")
                print(f"{'='*70}")
                
                # Mostrar celdas individuales
                print(f"Celdas detectadas: {len(celdas)}")
                valores_no_cero = [(i, formatear_decimal_frontend(v)) for i, v in enumerate(valores_fila) if v > 0]
                print(f"Valores no-cero encontrados: {valores_no_cero}")
                
                # TABLA 1: Factores 8-19 (MONTOS DE DIVIDENDOS)
                if tablas_encontradas == 1:
                    print("\n[TABLA 1] Procesando MONTOS DE DIVIDENDOS...")
                    
                    valores_grandes = [(i, v) for i, v in enumerate(valores_fila) if v > 10000]
                    
                    if valores_grandes:
                        idx_historico, val_historico = max(valores_grandes, key=lambda x: x[1])
                        
                        print(f"\n[HISTÓRICO] Detectado en columna {idx_historico}")
                        print(f"  Valor: {formatear_decimal_frontend(val_historico)}")
                        
                        response_data['valor_historico'] = formatear_decimal_frontend(val_historico)
                        
                        response_data['factores'][8]['valor'] = formatear_decimal_frontend(val_historico)
                        response_data['factores'][8]['valor_decimal'] = str(val_historico / FACTOR_DIVISOR)
                        print(f"  Factor 8 (IDPC 2017+): {formatear_decimal_frontend(val_historico)}")
                        
                        factor_actual = 9
                        for i in range(idx_historico + 1, len(valores_fila)):
                            if factor_actual > 19:
                                break
                            val = valores_fila[i]
                            if val == val_historico and i == idx_historico + 1:
                                continue
                            response_data['factores'][factor_actual]['valor'] = formatear_decimal_frontend(val)
                            response_data['factores'][factor_actual]['valor_decimal'] = str(val / FACTOR_DIVISOR)
                            if val > 0:
                                print(f"  Factor {factor_actual} (col {i}): {formatear_decimal_frontend(val)}")
                            factor_actual += 1
                    else:
                        print("[ADVERTENCIA] No se encontró Monto Histórico en Tabla 1")
                
                # TABLA 2: Factores 20-37 (CRÉDITOS)
                elif tablas_encontradas == 2:
                    print("\n[TABLA 2] Procesando CRÉDITOS...")
                    
                    # CORRECCIÓN: Ajuste del mapeo de columnas.
                    # En la fila de "Totales", la columna 0 es la etiqueta "Totales" y la columna 1 
                    # ya suele ser el Factor 20 (se eliminan las columnas de fecha/ID).
                    # El mapeo anterior iniciaba en índice 2, lo que causaba un desplazamiento.
                    # Nuevo mapeo: Índice 1 -> Factor 20, Índice 6 -> Factor 25.
                    
                    mapa_columnas_tabla2 = {
                        1: 20, 2: 21, 3: 22, 4: 23,
                        5: 24, 6: 25, 7: 26, 8: 27,
                        9: 28, 10: 29, 11: 30, 12: 31,
                        13: 32, 14: 33, 15: 34, 16: 35,
                        17: 36, 18: 37
                    }
                    
                    for col_idx, factor_id in mapa_columnas_tabla2.items():
                        if col_idx < len(valores_fila):
                            val = valores_fila[col_idx]
                            
                            # Solo asignar si el valor es positivo o si no se ha asignado antes
                            # (para evitar sobrescribir con ceros si el parsing es ruidoso)
                            if val >= 0:
                                response_data['factores'][factor_id]['valor'] = formatear_decimal_frontend(val)
                                response_data['factores'][factor_id]['valor_decimal'] = str(val / FACTOR_DIVISOR)
                            
                            if val > 0:
                                print(f"  Factor {factor_id} (col {col_idx}): {formatear_decimal_frontend(val)}")

        # Validación final
        print(f"\n{'='*70}")
        print("RESUMEN DE EXTRACCIÓN")
        print(f"{'='*70}")
        print(f"Emisor: {response_data['instrumento']}")
        print(f"Año: {response_data['ejercicio']}")
        print(f"Valor Histórico: {response_data['valor_historico']}")
        print(f"Factor 8 (IDPC 2017+): {response_data['factores'][8]['valor']}")
        # Validación del fix: Factor 25 debe tener valor ahora
        print(f"Factor 24 (Sin Der): {response_data['factores'][24]['valor']}")
        print(f"Factor 25 (Con Der): {response_data['factores'][25]['valor']}")
        
        return response_data

    except Exception as e:
        print(f"\n[ERROR FATAL] {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}