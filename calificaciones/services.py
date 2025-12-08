import pdfplumber
import re
from datetime import datetime
from decimal import Decimal

# ==============================================================================
# 1. MAPAS DE KEYWORDS (Configuración de Columnas)
# ==============================================================================

MAPA_KEYWORDS_C70 = {
    'numero_dividendo': ['nro', 'cert', 'folio'],
    'factor8': ['generados', 'contar', '01.01.2017'],
    'factor9': ['acumulados', 'hasta', '31.12.2016'],
    'factor10': ['pago', 'voluntario'],
    'factor11': ['sin', 'derecho', 'credito'],
    'factor12': ['rap', 'diferencia'],
    'factor13': ['otras', 'rentas'],
    'factor14': ['desproporcionadas'],
    'factor15': ['isfut', '20.780'],
    'factor16': ['isfut', '21.210'],
    'factor17': ['18.401', 'afectas'],
    'factor18': ['18.401', 'exentas'],
    'factor19': ['no', 'constitutivos'],
    'factor20': ['ipe'],
    'factor21': ['tasa', 'adicional'],
    'factor_actualizacion': ['tef', 'tasa'],
    'isfut': ['isfut']
}

MAPA_KEYWORDS_C44 = {
    'fecha_pago': ['fecha', 'operacion'],
    'instrumento': ['nombre', 'fondo'], 
    'valor_historico': ['monto', 'historico'],
    'factor_actualizacion': ['factor', 'actualiz'],
    'factor8': ['no', 'sujetos', 'restitucion', '2019', 'con'], 
    'factor9': ['no', 'sujetos', 'restitucion', '2019', 'sin'],
    'factor10': ['afectas', 'restitucion', '2020', 'con'],
    'factor11': ['afectas', 'restitucion', '2020', 'sin'],
    'factor17': ['exentas', 'restitucion', 'con'],
    'factor18': ['exentas', 'restitucion', 'sin']
}

# ==============================================================================
# 2. FUNCIONES DE DICCIONARIO Y LIMPIEZA
# ==============================================================================

def limpiar_texto(texto):
    if not texto: return ""
    return str(texto).lower().strip().replace('\n', ' ')

def limpiar_moneda(valor):
    if not valor: return Decimal(0)
    if isinstance(valor, (int, float, Decimal)): return valor
    val_str = str(valor).strip().replace('.', '').replace(',', '.') # 1.000,00 -> 1000.00
    val_str = re.sub(r'[^\d\.-]', '', val_str)
    try: return Decimal(val_str)
    except: return Decimal(0)

def detectar_tipo_certificado(texto):
    texto = texto.upper()
    if "CERTIFICADO" in texto and "70" in texto: return "C70"
    if "CERTIFICADO" in texto and "44" in texto: return "C44"
    return "DESCONOCIDO"

# ==============================================================================
# 3. LÓGICA DE EXTRACCIÓN DE DATOS (CLIENTE Y FECHA)
# ==============================================================================

def detectar_cliente_completo(texto_pdf):
    """
    Extrae RUT y Nombre del titular usando un patrón flexible.
    Determina si es Jurídica o Natural por reglas de negocio.
    """
    cliente = {
        'nombre': 'Cliente Desconocido',
        'rut': '',
        'tipo_persona': 'natural',
        'es_nuevo': True
    }
    
    # Normalizar espacios
    texto_clean = re.sub(r'\s+', ' ', texto_pdf)

    # Regex Universal: Busca "titular/Sr(a) [NOMBRE] ... RUT [NUMERO]"
    # Permite caracteres especiales en el nombre (. , & Ñ)
    patron = r'(?:titular|Sr\.?\s*\(?a\)?)\s+(.+?)(?:,|\s+RUT)\s*RUT\s*N?[°º]?\s*[:\.]?\s*([\d\.]+-[0-9kK])'
    match = re.search(patron, texto_clean, re.IGNORECASE)
    
    if match:
        nombre_raw = match.group(1).strip().upper()
        rut_raw = match.group(2).replace('.', '').strip().upper()
        
        # Limpieza final nombre
        if nombre_raw.endswith(','): nombre_raw = nombre_raw[:-1]
        
        cliente['nombre'] = nombre_raw
        cliente['rut'] = rut_raw
        
        # Heurística de Tipo de Persona
        es_juridica = False
        keywords_empresa = ['SPA', 'S.A.', 'LTDA', 'LIMITADA', 'E.I.R.L', 'SOCIEDAD', 'INVERSIONES', 'FONDO', 'BANCO', 'CORREDORES']
        
        # Regla A: Nombre contiene siglas de empresa
        if any(k in nombre_raw.split() for k in keywords_empresa):
            es_juridica = True
        
        # Regla B: RUT mayor a 48 millones
        try:
            rut_num = int(rut_raw.split('-')[0])
            if rut_num > 48000000:
                es_juridica = True
        except:
            pass

        cliente['tipo_persona'] = 'juridica' if es_juridica else 'natural'

    return cliente

def detectar_fecha_emision(texto_pdf):
    """
    Busca la fecha del documento en la cabecera (Ej: Santiago, 27 Marzo de 2024).
    Retorna objeto date o la fecha de hoy por defecto.
    """
    meses = {
        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06',
        'julio': '07', 'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
    }
    
    # Patrón texto: "27 Marzo de 2024"
    patron_txt = r'(\d{1,2})\s+de?\s*([a-zA-Z]+)\s+de?l?\s*(\d{4})'
    match = re.search(patron_txt, texto_pdf, re.IGNORECASE)
    
    if match:
        dia, mes_txt, anno = match.groups()
        mes_num = meses.get(mes_txt.lower())
        if mes_num:
            try:
                return datetime.strptime(f"{dia}-{mes_num}-{anno}", "%d-%m-%Y").date()
            except:
                pass
    
    # Patrón numérico: "27/03/2024"
    match_num = re.search(r'(\d{2})/(\d{2})/(\d{4})', texto_pdf)
    if match_num:
        try:
            return datetime.strptime(match_num.group(0), "%d/%m/%Y").date()
        except:
            pass
            
    return datetime.now().date()

# ==============================================================================
# 4. MOTOR DE PROCESAMIENTO DE TABLAS
# ==============================================================================

def identificar_indices_columnas(filas_tabla, tipo_cert):
    """Mapea nombres de campos a índices de columna según keywords."""
    mapa_indices = {}
    keywords_map = MAPA_KEYWORDS_C70 if tipo_cert == 'C70' else MAPA_KEYWORDS_C44
    
    # Analizamos más filas (15) porque los encabezados del C70 son verticales y largos
    cabecera_analisis = filas_tabla[:15]
    max_cols = max(len(f) for f in cabecera_analisis) if cabecera_analisis else 0
    
    for col_idx in range(max_cols):
        # Concatenamos todo el texto vertical de esa columna
        texto_columna = " ".join([
            limpiar_texto(fila[col_idx]) 
            for fila in cabecera_analisis 
            if col_idx < len(fila) and fila[col_idx]
        ])
        
        for campo, keywords in keywords_map.items():
            if campo in mapa_indices: continue
            # Si TODAS las palabras clave están presentes
            if all(k in texto_columna for k in keywords):
                mapa_indices[campo] = col_idx
                
    return mapa_indices

def extraer_datos_fila(fila, mapa_indices):
    """Extrae datos de una fila específica usando el mapa."""
    datos = {'ingreso_montos': False, 'fecha_pago': None}
    
    for campo, indice in mapa_indices.items():
        if indice < len(fila):
            val_raw = fila[indice]
            
            if 'factor' in campo or 'monto' in campo:
                datos[campo] = limpiar_moneda(val_raw)
            elif campo == 'isfut':
                datos[campo] = True if limpiar_moneda(val_raw) > 0 else False
            elif campo == 'fecha_pago':
                datos[campo] = str(val_raw) # Se mantiene temporalmente
            else:
                datos[campo] = val_raw
        else:
             datos[campo] = 0 if 'factor' in campo else ""
    return datos

def procesar_archivo_pdf(archivo_memoria):
    """
    Función principal llamada desde la vista.
    """
    datos_retorno = {
        'tipo': 'DESCONOCIDO',
        'metadata': {'rut_emisor': '', 'anno': datetime.now().year},
        'cliente_detectado': {}, 
        'filas': [],
        'error': None
    }

    try:
        with pdfplumber.open(archivo_memoria) as pdf:
            # 1. Metadatos (Página 1)
            first_page = pdf.pages[0]
            texto_pag1 = first_page.extract_text() or ""
            
            datos_retorno['cliente_detectado'] = detectar_cliente_completo(texto_pag1)
            datos_retorno['tipo'] = detectar_tipo_certificado(texto_pag1)
            fecha_emision = detectar_fecha_emision(texto_pag1)
            
            match_anno = re.search(r'año\s*(?:comercial|tributario)\s*(\d{4})', texto_pag1, re.IGNORECASE)
            if match_anno: datos_retorno['metadata']['anno'] = int(match_anno.group(1))

            # 2. Extracción de Tablas (Unificación de Páginas)
            todas_las_filas = []
            for page in pdf.pages:
                # 'lines' es fundamental para C70 y C44
                tablas = page.extract_table(table_settings={"vertical_strategy": "lines", "horizontal_strategy": "lines"})
                if not tablas: 
                    tablas = page.extract_table()
                if tablas: 
                    todas_las_filas.extend(tablas)
            
            if not todas_las_filas:
                datos_retorno['error'] = "No se encontraron tablas legibles."
                return datos_retorno

            # 3. Mapeo
            mapa_indices = identificar_indices_columnas(todas_las_filas, datos_retorno['tipo'])
            if not mapa_indices:
                 datos_retorno['error'] = "No se identificaron columnas válidas."
                 return datos_retorno

            # 4. Estrategia de Selección de Datos
            fila_totales = None
            
            # Buscar fila "Total" (Prioridad para C70)
            for fila in todas_las_filas:
                texto_fila = " ".join([str(x).lower() for x in fila if x])
                if "total" in texto_fila:
                    fila_totales = fila
                    break
            
            if fila_totales and datos_retorno['tipo'] == 'C70':
                # Si es C70 y tiene totales, usamos solo esa fila
                datos_fila = extraer_datos_fila(fila_totales, mapa_indices)
                datos_fila['fecha_pago'] = fecha_emision.strftime("%d/%m/%Y")
                datos_fila['instrumento'] = "RESUMEN ANUAL CERTIFICADO"
                datos_retorno['filas'].append(datos_fila)
            else:
                # Si no hay totales o es C44 (detalle), procesamos filas de datos
                for fila in todas_las_filas:
                    # Validamos si parece una fila de datos (tiene números o fecha)
                    texto_unido = "".join([str(x) for x in fila if x])
                    
                    # Criterio C44: Buscar filas con fechas válidas en la columna mapeada
                    idx_fecha = mapa_indices.get('fecha_pago')
                    if idx_fecha is not None and len(fila) > idx_fecha:
                         val_fecha = str(fila[idx_fecha])
                         if re.match(r'\d{1,2}/\d{1,2}/\d{4}', val_fecha):
                             datos_fila = extraer_datos_fila(fila, mapa_indices)
                             datos_retorno['filas'].append(datos_fila)
                    
                    # Fallback C70 sin totales detectados (raro):
                    elif datos_retorno['tipo'] == 'C70' and len(texto_unido) > 10 and "fecha" not in texto_unido.lower():
                         datos_fila = extraer_datos_fila(fila, mapa_indices)
                         if not datos_fila['fecha_pago']:
                             datos_fila['fecha_pago'] = fecha_emision.strftime("%d/%m/%Y")
                         datos_retorno['filas'].append(datos_fila)

    except Exception as e:
        datos_retorno['error'] = f"Error al procesar PDF: {str(e)}"

    return datos_retorno