"""
MOTOR DE GASTOS A PROVEEDORES Y CONCILIACIÓN BANCARIA (Expense & Bank Reconciliation Engine)
=============================================================================================
Gestiona la subida de comprobantes de pago a proveedores (WhatsApp, PDF, imágenes, transferencias SPEI),
la carga de estados de cuenta bancarios (BBVA, Kapital Bank, Bajío, Afirme, etc.) para las dos
compañías (BALDOMERO MEDINA GARZA y AUTO LINEA MULTITRANS), y ejecuta la conciliación automática
y manual entre egresos bancarios y comprobantes de gasto.
"""

import os
import json
import re
import uuid
import calendar
from datetime import datetime, date, timedelta
import unicodedata
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

try:
    import pypdf
except ImportError:
    pypdf = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
COMPROBANTES_DIR = os.path.join(UPLOADS_DIR, "comprobantes")
ESTADOS_CUENTA_DIR = os.path.join(UPLOADS_DIR, "estados_cuenta")

for d in [DATA_DIR, UPLOADS_DIR, COMPROBANTES_DIR, ESTADOS_CUENTA_DIR]:
    os.makedirs(d, exist_ok=True)

COMPROBANTES_FILE = os.path.join(DATA_DIR, "gastos_comprobantes.json")
ESTADOS_CUENTA_FILE = os.path.join(DATA_DIR, "banco_movimientos.json")
CONCILIACIONES_FILE = os.path.join(DATA_DIR, "conciliaciones_manuales.json")

# Normalizar texto (eliminar acentos y mayúsculas)
def normalizar_cadena(s):
    if not s:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(s))
        if unicodedata.category(c) != 'Mn'
    ).lower().strip()

def fmt_dinero(val):
    try:
        return f"${float(val):,.2f}"
    except Exception:
        return "$0.00"

def parsear_fecha_flexible(texto_fecha):
    if not texto_fecha:
        return datetime.now().strftime("%Y-%m-%d")
    tf = str(texto_fecha).strip()
    # YYYY-MM-DD
    m = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', tf)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    # DD-MM-YYYY or DD/MM/YYYY
    m = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', tf)
    if m:
        d, mo, y = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    # Formato con nombre de mes: "01 sep 2026" / "02 septiembre 2026"
    meses_es = {
        'ene': 1, 'enero': 1, 'feb': 2, 'febrero': 2, 'mar': 3, 'marzo': 3,
        'abr': 4, 'abril': 4, 'may': 5, 'mayo': 5, 'jun': 6, 'junio': 6,
        'jul': 7, 'julio': 7, 'ago': 8, 'agosto': 8, 'sep': 9, 'septiembre': 9, 'set': 9,
        'oct': 10, 'octubre': 10, 'nov': 11, 'noviembre': 11, 'dic': 12, 'diciembre': 12
    }
    tf_norm = normalizar_cadena(tf)
    for mes_nombre, mes_num in meses_es.items():
        if mes_nombre in tf_norm:
            m_dia = re.search(r'(\d{1,2})', tf_norm)
            m_anio = re.search(r'(\d{4})', tf_norm)
            dia_val = int(m_dia.group(1)) if m_dia else 1
            anio_val = int(m_anio.group(1)) if m_anio else datetime.now().year
            return f"{anio_val:04d}-{mes_num:02d}-{dia_val:02d}"
    return datetime.now().strftime("%Y-%m-%d")

# ==============================================================================
# ALMACENAMIENTO PERSISTENTE
# ==============================================================================
def cargar_json(archivo, default=None):
    if default is None:
        default = []
    if os.path.exists(archivo):
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return default

def guardar_json(archivo, datos):
    with open(archivo, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def inicializar_datos_demo():
    """Inicializa datos reales/demo basados en las capturas del usuario si los archivos están vacíos."""
    comprobantes = cargar_json(COMPROBANTES_FILE, [])
    if not comprobantes:
        comprobantes = [
            {
                "id": "COMP-20260901-001",
                "empresa": "BALDOMERO MEDINA GARZA",
                "fecha": "2026-09-01",
                "hora": "10:58:11",
                "banco_origen": "BBVA",
                "cuenta_origen": "0477242417",
                "banco_destino": "MERCADO PAGO W",
                "cuenta_destino": "722969010864935526",
                "beneficiario": "FELIX SANCHES",
                "proveedor_asignado": "Félix Sánchez",
                "concepto": "FELIX",
                "nota_whatsapp": "FELIX",
                "referencia": "010926",
                "clave_rastreo": "BNET01002609010040710159",
                "folio_operacion": "2733659545",
                "importe": 3000.00,
                "comision": 0.00,
                "total": 3000.00,
                "tipo_comprobante": "Transferencia SPEI BBVA",
                "archivo_nombre": "Comprobante_BBVA_Felix_3000.jpg",
                "archivo_ruta": "",
                "creado_en": "2026-09-01T10:58:11"
            },
            {
                "id": "COMP-20260901-002",
                "empresa": "BALDOMERO MEDINA GARZA",
                "fecha": "2026-09-01",
                "hora": "17:30:35",
                "banco_origen": "Kapital Bank",
                "cuenta_origen": "Crédito Flex",
                "banco_destino": "Santander",
                "cuenta_destino": "072441002322062146",
                "beneficiario": "JOSE PEREZ",
                "proveedor_asignado": "José Pérez / CMP",
                "concepto": "Disposición de crédito Flex - Factura 1",
                "nota_whatsapp": "cmp",
                "referencia": "FT26244598954165",
                "clave_rastreo": "FT26244598954165",
                "folio_operacion": "KAP-72",
                "importe": 17585.60,
                "comision": 204.00,
                "total": 17789.60,
                "tipo_comprobante": "Disposición Kapital Bank",
                "archivo_nombre": "Comprobante Disposición de crédito Flex (72).pdf",
                "archivo_ruta": "",
                "creado_en": "2026-09-01T17:30:35"
            },
            {
                "id": "COMP-20260902-003",
                "empresa": "BALDOMERO MEDINA GARZA",
                "fecha": "2026-09-02",
                "hora": "20:35:00",
                "banco_origen": "BBVA",
                "cuenta_origen": "CUENTA • 42417",
                "banco_destino": "AFIRME BMG",
                "cuenta_destino": "18340",
                "beneficiario": "AFIRME BMG",
                "proveedor_asignado": "Traspaso BMG Afirme",
                "concepto": "Traspsoy",
                "nota_whatsapp": "Traspaso cuenta propia",
                "referencia": "0309260",
                "clave_rastreo": "BNET01002609030041161582",
                "folio_operacion": "7370116926",
                "importe": 25000.00,
                "comision": 6.50,
                "total": 25006.50,
                "tipo_comprobante": "Transferencia SPEI BBVA",
                "archivo_nombre": "Comprobante_Traspaso_Afirme_25000.jpg",
                "archivo_ruta": "",
                "creado_en": "2026-09-02T20:35:00"
            },
            {
                "id": "COMP-20260901-004",
                "empresa": "AUTO LINEA MULTITRANS",
                "fecha": "2026-09-01",
                "hora": "12:15:00",
                "banco_origen": "BBVA",
                "cuenta_origen": "0477242417",
                "banco_destino": "BAJIO",
                "cuenta_destino": "0040708290",
                "beneficiario": "PROVEEDOR QUÍMICOS Y SOLVENTES",
                "proveedor_asignado": "Químicos y Solventes del Bajío",
                "concepto": "Pago Factura 7546",
                "nota_whatsapp": "pago solventes",
                "referencia": "0010926ECA00754696",
                "clave_rastreo": "0010926ECA00754696",
                "folio_operacion": "948201",
                "importe": 1259.09,
                "comision": 0.00,
                "total": 1259.09,
                "tipo_comprobante": "Transferencia SPEI Bajío",
                "archivo_nombre": "Comprobante_Bajio_1259.jpg",
                "archivo_ruta": "",
                "creado_en": "2026-09-01T12:15:00"
            }
        ]
        guardar_json(COMPROBANTES_FILE, comprobantes)

    movimientos = cargar_json(ESTADOS_CUENTA_FILE, [])
    if not movimientos:
        movimientos = [
            {
                "id": "MOV-20260901-001",
                "empresa": "BALDOMERO MEDINA GARZA",
                "banco": "BBVA",
                "cuenta": "CUENTA • 42417",
                "fecha": "2026-09-01",
                "descripcion": "SPEI ENVIADO MERCADO PAGO W / 722969010864935526 FELIX BNET01002609010040710159",
                "referencia": "010926",
                "clave_rastreo": "BNET01002609010040710159",
                "tipo": "CARGO",
                "cargo": 3000.00,
                "abono": 0.00,
                "saldo": 145820.50
            },
            {
                "id": "MOV-20260901-002",
                "empresa": "AUTO LINEA MULTITRANS",
                "banco": "BBVA",
                "cuenta": "CUENTA • 42417",
                "fecha": "2026-09-01",
                "descripcion": "SPEI ENVIADO BAJIO / 0040708290 030 0010926ECA00754696",
                "referencia": "0010926ECA00754696",
                "clave_rastreo": "0010926ECA00754696",
                "tipo": "CARGO",
                "cargo": 1259.09,
                "abono": 0.00,
                "saldo": 89430.12
            },
            {
                "id": "MOV-20260901-003",
                "empresa": "BALDOMERO MEDINA GARZA",
                "banco": "Kapital Bank",
                "cuenta": "Crédito Flex",
                "fecha": "2026-09-01",
                "descripcion": "DISPOSICION FLEX DIGITAL JOSE PEREZ 072441002322062146 FT26244598954165",
                "referencia": "FT26244598954165",
                "clave_rastreo": "FT26244598954165",
                "tipo": "CARGO",
                "cargo": 17585.60,
                "abono": 0.00,
                "saldo": 250000.00
            },
            {
                "id": "MOV-20260901-004",
                "empresa": "BALDOMERO MEDINA GARZA",
                "banco": "Kapital Bank",
                "cuenta": "Crédito Flex",
                "fecha": "2026-09-01",
                "descripcion": "COMISION DISPOSICION CREDITO FLEX + IVA ($175.86 + $28.14)",
                "referencia": "COM-KAP-72",
                "clave_rastreo": "",
                "tipo": "CARGO",
                "cargo": 204.00,
                "abono": 0.00,
                "saldo": 249796.00
            },
            {
                "id": "MOV-20260902-005",
                "empresa": "BALDOMERO MEDINA GARZA",
                "banco": "BBVA",
                "cuenta": "CUENTA • 42417",
                "fecha": "2026-09-02",
                "descripcion": "SPEI ENVIADO AFIRME BMG / 18340 TRASPSOY BNET01002609030041161582",
                "referencia": "0309260",
                "clave_rastreo": "BNET01002609030041161582",
                "tipo": "CARGO",
                "cargo": 25000.00,
                "abono": 0.00,
                "saldo": 120820.50
            },
            {
                "id": "MOV-20260902-006",
                "empresa": "BALDOMERO MEDINA GARZA",
                "banco": "BBVA",
                "cuenta": "CUENTA • 42417",
                "fecha": "2026-09-02",
                "descripcion": "COMISION TRANSFERENCIA SPEI BNET01002609030041161582",
                "referencia": "COM-SPEI",
                "clave_rastreo": "",
                "tipo": "CARGO",
                "cargo": 6.50,
                "abono": 0.00,
                "saldo": 120814.00
            },
            {
                "id": "MOV-20260903-007",
                "empresa": "BALDOMERO MEDINA GARZA",
                "banco": "BBVA",
                "cuenta": "CUENTA • 42417",
                "fecha": "2026-09-03",
                "descripcion": "CARGO AUTOMATICO CFE SUMINISTRADOR SERVICIOS BASICOS 09842187",
                "referencia": "CFE-9842",
                "clave_rastreo": "",
                "tipo": "CARGO",
                "cargo": 4350.00,
                "abono": 0.00,
                "saldo": 116464.00
            },
            {
                "id": "MOV-20260904-008",
                "empresa": "AUTO LINEA MULTITRANS",
                "banco": "BBVA",
                "cuenta": "CUENTA • 42417",
                "fecha": "2026-09-04",
                "descripcion": "SPEI ENVIADO GASOLINERA SERVICIO QUERETARO RECARGA COMBUSTIBLE",
                "referencia": "GAS-0904",
                "clave_rastreo": "BNET010026090400887192",
                "tipo": "CARGO",
                "cargo": 8900.00,
                "abono": 0.00,
                "saldo": 80530.12
            }
        ]
        guardar_json(ESTADOS_CUENTA_FILE, movimientos)

inicializar_datos_demo()

# ==============================================================================
# PARSERS DE COMPROBANTES (PDF & TEXTO)
# ==============================================================================
def extraer_datos_pdf_comprobante(pdf_path):
    """Extrae texto de comprobante PDF (Kapital Bank, BBVA, etc.) y parsea datos estructurados."""
    if not pypdf or not os.path.exists(pdf_path):
        return {}
    
    texto_completo = ""
    try:
        reader = pypdf.PdfReader(pdf_path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                texto_completo += t + "\n"
    except Exception as e:
        print(f"[WARN PDF Extract]: {e}")
        return {}

    datos = {}
    texto_norm = texto_completo.replace("\xa0", " ")
    
    # 1. Banco emisor
    if "Kapital" in texto_norm or "KPTL" in texto_norm:
        datos["banco_origen"] = "Kapital Bank"
        datos["cuenta_origen"] = "Crédito Flex"
        datos["tipo_comprobante"] = "Disposición Kapital Bank"
    elif "BBVA" in texto_norm:
        datos["banco_origen"] = "BBVA"
        datos["tipo_comprobante"] = "Transferencia BBVA"
    elif "Bajío" in texto_norm or "BAJIO" in texto_norm:
        datos["banco_origen"] = "Bajío"
        datos["tipo_comprobante"] = "Transferencia Bajío"
    elif "Afirme" in texto_norm:
        datos["banco_origen"] = "Afirme"
        datos["tipo_comprobante"] = "Transferencia Afirme"
    else:
        datos["banco_origen"] = "Bancario"
        datos["tipo_comprobante"] = "Comprobante de Pago"

    # 2. Fecha y hora
    m_fecha = re.search(r'Fecha y hora\s*[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{4})(?:\s*\|\s*(\d{1,2}:\d{1,2}(?::\d{1,2})?))?', texto_norm, re.IGNORECASE)
    if not m_fecha:
        m_fecha = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})', texto_norm)
    if m_fecha:
        datos["fecha"] = parsear_fecha_flexible(m_fecha.group(1))
        if len(m_fecha.groups()) > 1 and m_fecha.group(2):
            datos["hora"] = m_fecha.group(2)

    # 3. Importes
    # Kapital Bank: "Importe total $17,585.60" o "Comisión por disposición $175.86"
    m_tot = re.search(r'Importe total\s*\$?\s*([\d,]+\.\d{2})', texto_norm, re.IGNORECASE)
    if not m_tot:
        m_tot = re.search(r'Importe\s*\$?\s*([\d,]+\.\d{2})', texto_norm, re.IGNORECASE)
    if m_tot:
        datos["importe"] = float(m_tot.group(1).replace(",", ""))

    m_com = re.search(r'Total de comisi[oó]n\*?\s*\$?\s*([\d,]+\.\d{2})', texto_norm, re.IGNORECASE)
    if not m_com:
        m_com = re.search(r'Comisi[oó]n(?: por disposici[oó]n| por transferencia)?\s*\$?\s*([\d,]+\.\d{2})', texto_norm, re.IGNORECASE)
    if m_com:
        datos["comision"] = float(m_com.group(1).replace(",", ""))
    else:
        datos["comision"] = 0.0

    imp = datos.get("importe", 0.0)
    com = datos.get("comision", 0.0)
    datos["total"] = round(imp + com, 2)

    # 4. Beneficiario / Factura
    m_factura = re.search(r'Factura\s*\d*\s*\n?\s*([A-ZÁÉÍÓÚÑ\s]+)\s*\n?\$?[\d,]+\.\d{2}\s*\n?([\d\s\-A-Z]+)', texto_norm)
    if m_factura:
        datos["beneficiario"] = m_factura.group(1).strip()
        ref_line = m_factura.group(2).strip()
        if "-" in ref_line:
            parts = [p.strip() for p in ref_line.split("-")]
            datos["cuenta_destino"] = parts[0]
            datos["referencia"] = parts[1]
            datos["clave_rastreo"] = parts[1]
        else:
            datos["referencia"] = ref_line
    else:
        m_ben = re.search(r'Nombre(?: del beneficiario)?\s*[:\s]*([A-ZÁÉÍÓÚÑ\s]+)', texto_norm, re.IGNORECASE)
        if m_ben:
            datos["beneficiario"] = m_ben.group(1).strip()

    # 5. Concepto
    m_conc = re.search(r'Concepto(?: de pago)?\s*[:\s]*([^\n\r]+)', texto_norm, re.IGNORECASE)
    if m_conc:
        datos["concepto"] = m_conc.group(1).strip()

    # 6. Clave de rastreo
    m_rastreo = re.search(r'Clave de rastreo\s*[:\s]*([A-Za-z0-9]+)', texto_norm, re.IGNORECASE)
    if m_rastreo:
        datos["clave_rastreo"] = m_rastreo.group(1).strip()

    # 7. Cuenta de retiro
    m_retiro = re.search(r'Cuenta de retiro\s*[:\s]*([0-9\s]+)', texto_norm, re.IGNORECASE)
    if m_retiro:
        datos["cuenta_origen"] = m_retiro.group(1).strip()

    # 8. Folio
    m_folio = re.search(r'Folio(?: de operaci[oó]n| de internet)?\s*[:\s]*([0-9A-Za-z]+)', texto_norm, re.IGNORECASE)
    if m_folio:
        datos["folio_operacion"] = m_folio.group(1).strip()

    return datos

def extraer_datos_de_texto_o_nota(texto, empresa="BALDOMERO MEDINA GARZA"):
    """Intenta extraer datos de un texto pegado o nota de WhatsApp."""
    datos = {}
    t = texto or ""
    # Buscar importe: "$3,000.00" o "3000"
    m_imp = re.search(r'\$?\s*([\d,]+\.\d{2})', t)
    if m_imp:
        datos["importe"] = float(m_imp.group(1).replace(",", ""))
    # Buscar fecha
    datos["fecha"] = parsear_fecha_flexible(t)
    # Proveedor sugerido de palabras cortas (ej. "cmp", "felix", "resina")
    datos["nota_whatsapp"] = t.strip()
    datos["proveedor_asignado"] = t.strip()
    datos["empresa"] = empresa
    return datos

# ==============================================================================
# MOTOR DE CONCILIACIÓN AUTOMÁTICA
# ==============================================================================
def ejecutar_conciliacion_engine(empresa="TODAS (Consolidado)", mes=None, anio=None, banco_filtro="TODOS"):
    """
    Cruza los movimientos bancarios contra los comprobantes de gastos:
    1. Filtra por empresa, mes y año.
    2. Aplica reglas de coincidencia (Clave de rastreo, Monto exacto, Monto + comisión, Tolerancia de fecha).
    3. Retorna KPIs, lista de conciliados, faltantes de comprobante y comprobantes pendientes.
    """
    comprobantes = cargar_json(COMPROBANTES_FILE, [])
    movimientos = cargar_json(ESTADOS_CUENTA_FILE, [])
    conciliaciones_manuales = cargar_json(CONCILIACIONES_FILE, {})

    # Filtrar comprobantes
    comprobantes_filtrados = []
    for c in comprobantes:
        if empresa and empresa != "TODAS (Consolidado)":
            if c.get("empresa") != empresa:
                continue
        if mes or anio:
            f_str = c.get("fecha", "")
            try:
                dt = datetime.strptime(f_str[:10], "%Y-%m-%d").date()
                if mes and dt.month != int(mes):
                    continue
                if anio and dt.year != int(anio):
                    continue
            except Exception:
                pass
        comprobantes_filtrados.append(c)

    # Filtrar movimientos bancarios (solo cargos / retiros / egresos)
    movimientos_filtrados = []
    for m in movimientos:
        if empresa and empresa != "TODAS (Consolidado)":
            if m.get("empresa") != empresa:
                continue
        if banco_filtro and banco_filtro != "TODOS":
            if normalizar_cadena(banco_filtro) not in normalizar_cadena(m.get("banco", "")):
                continue
        if mes or anio:
            f_str = m.get("fecha", "")
            try:
                dt = datetime.strptime(f_str[:10], "%Y-%m-%d").date()
                if mes and dt.month != int(mes):
                    continue
                if anio and dt.year != int(anio):
                    continue
            except Exception:
                pass
        # Solo consideramos cargos (salidas de dinero de la cuenta)
        if float(m.get("cargo", 0) or 0) > 0.01:
            movimientos_filtrados.append(m)

    # Conjuntos de asignados
    mov_usados = set()
    comp_usados = set()
    matches = []

    # 1. Conciliaciones manuales forzadas por el usuario
    for mov_id, comp_id in conciliaciones_manuales.items():
        mov_obj = next((m for m in movimientos_filtrados if m["id"] == mov_id), None)
        comp_obj = next((c for c in comprobantes_filtrados if c["id"] == comp_id), None)
        if mov_obj and comp_obj:
            mov_usados.add(mov_id)
            comp_usados.add(comp_id)
            diff = round(float(mov_obj.get("cargo", 0)) - float(comp_obj.get("importe", 0)), 2)
            matches.append({
                "tipo_match": "MANUAL",
                "score": 100,
                "estado": "CONCILIADO",
                "movimiento": mov_obj,
                "comprobante": comp_obj,
                "diferencia": diff,
                "motivo": "Conciliación manual confirmada por el usuario"
            })

    # 2. Match exacto por Clave de Rastreo o Folio de Operación
    for mov in movimientos_filtrados:
        if mov["id"] in mov_usados:
            continue
        rastreo_mov = normalizar_cadena(mov.get("clave_rastreo") or mov.get("referencia") or "")
        if not rastreo_mov or len(rastreo_mov) < 6:
            continue
        
        for comp in comprobantes_filtrados:
            if comp["id"] in comp_usados:
                continue
            rastreo_comp = normalizar_cadena(comp.get("clave_rastreo") or comp.get("referencia") or comp.get("folio_operacion") or "")
            if rastreo_comp and len(rastreo_comp) >= 6 and (rastreo_mov in rastreo_comp or rastreo_comp in rastreo_mov):
                mov_usados.add(mov["id"])
                comp_usados.add(comp["id"])
                diff = round(float(mov.get("cargo", 0)) - float(comp.get("importe", 0)), 2)
                matches.append({
                    "tipo_match": "CLAVE_RASTREO",
                    "score": 100,
                    "estado": "CONCILIADO",
                    "movimiento": mov,
                    "comprobante": comp,
                    "diferencia": diff,
                    "motivo": f"Coincidencia exacta por Clave de Rastreo / Referencia ({comp.get('clave_rastreo') or comp.get('referencia')})"
                })
                break

    # 3. Match exacto por Monto + Fecha idéntica
    for mov in movimientos_filtrados:
        if mov["id"] in mov_usados:
            continue
        m_monto = float(mov.get("cargo", 0))
        m_fecha = mov.get("fecha", "")

        for comp in comprobantes_filtrados:
            if comp["id"] in comp_usados:
                continue
            c_monto = float(comp.get("importe", 0))
            c_total = float(comp.get("total", c_monto))
            c_fecha = comp.get("fecha", "")

            # Coincidencia exacta de monto o monto total con comisión
            if (abs(m_monto - c_monto) < 0.02 or abs(m_monto - c_total) < 0.02) and m_fecha == c_fecha:
                mov_usados.add(mov["id"])
                comp_usados.add(comp["id"])
                matches.append({
                    "tipo_match": "MONTO_Y_FECHA",
                    "score": 98,
                    "estado": "CONCILIADO",
                    "movimiento": mov,
                    "comprobante": comp,
                    "diferencia": round(m_monto - c_monto, 2),
                    "motivo": f"Monto idéntico ({fmt_dinero(m_monto)}) y misma fecha ({m_fecha})"
                })
                break

    # 4. Match por Monto + Fecha cercana (±2 días)
    for mov in movimientos_filtrados:
        if mov["id"] in mov_usados:
            continue
        m_monto = float(mov.get("cargo", 0))
        try:
            m_dt = datetime.strptime(mov.get("fecha", "")[:10], "%Y-%m-%d").date()
        except Exception:
            continue

        for comp in comprobantes_filtrados:
            if comp["id"] in comp_usados:
                continue
            c_monto = float(comp.get("importe", 0))
            c_total = float(comp.get("total", c_monto))
            try:
                c_dt = datetime.strptime(comp.get("fecha", "")[:10], "%Y-%m-%d").date()
            except Exception:
                continue

            dias_diff = abs((m_dt - c_dt).days)
            if (abs(m_monto - c_monto) < 0.02 or abs(m_monto - c_total) < 0.02) and dias_diff <= 2:
                mov_usados.add(mov["id"])
                comp_usados.add(comp["id"])
                matches.append({
                    "tipo_match": "MONTO_FECHA_CERCANA",
                    "score": 90,
                    "estado": "CONCILIADO",
                    "movimiento": mov,
                    "comprobante": comp,
                    "diferencia": round(m_monto - c_monto, 2),
                    "motivo": f"Monto coincidente ({fmt_dinero(m_monto)}) con desfase bancario de {dias_diff} día(s)"
                })
                break

    # 5. Agrupar no conciliados y armar lista completa para el tablero
    gastos_sin_comprobante = [m for m in movimientos_filtrados if m["id"] not in mov_usados]
    comprobantes_pendientes = [c for c in comprobantes_filtrados if c["id"] not in comp_usados]

    # Marcar banderas de conciliado
    for mov in movimientos_filtrados:
        mov["conciliado"] = mov["id"] in mov_usados

    for comp in comprobantes_filtrados:
        comp["conciliado"] = comp["id"] in comp_usados
        if "monto" not in comp:
            comp["monto"] = float(comp.get("importe", 0))
        if "monto_total" not in comp:
            comp["monto_total"] = float(comp.get("total", comp["monto"]))

    # Armar lista unificada de cruce para el Tablero Lado a Lado
    tablero_cruce = []
    for m_item in matches:
        tablero_cruce.append({
            "id": m_item["movimiento"]["id"],
            "movimiento_banco": m_item["movimiento"],
            "comprobante": m_item["comprobante"],
            "estado_conciliacion": "CONCILIADO",
            "match_score": m_item.get("score", 100),
            "razon_diferencia": m_item.get("motivo", "Conciliación automática")
        })

    for sin_c in gastos_sin_comprobante:
        tablero_cruce.append({
            "id": sin_c["id"],
            "movimiento_banco": sin_c,
            "comprobante": None,
            "estado_conciliacion": "SIN_COMPROBANTE",
            "match_score": 0,
            "razon_diferencia": "Sin comprobante de gasto"
        })

    # Ordenar por fecha descendente
    tablero_cruce.sort(key=lambda x: str(x["movimiento_banco"].get("fecha", "")), reverse=True)

    # Calcular KPIs
    tot_egresos_banco = sum(float(m.get("cargo", 0)) for m in movimientos_filtrados)
    tot_comprobantes_subidos = sum(float(c.get("total", c.get("importe", 0))) for c in comprobantes_filtrados)
    tot_conciliado = sum(float(item["movimiento_banco"].get("cargo", 0)) for item in tablero_cruce if item["estado_conciliacion"] == "CONCILIADO")
    tot_sin_comprobante = sum(float(m.get("cargo", 0)) for m in gastos_sin_comprobante)
    tot_comp_pendientes = sum(float(c.get("total", c.get("importe", 0))) for c in comprobantes_pendientes)

    pct_conciliado = round((tot_conciliado / tot_egresos_banco * 100.0), 1) if tot_egresos_banco > 0 else 100.0

    kpis_dict = {
        "empresa": empresa,
        "mes": mes,
        "anio": anio,
        "total_banco_egresos": round(tot_egresos_banco, 2),
        "total_movimientos_banco": len(movimientos_filtrados),
        "total_comprobantes": len(comprobantes_filtrados),
        "total_comprobantes_monto": round(tot_comprobantes_subidos, 2),
        "monto_conciliado": round(tot_conciliado, 2),
        "total_conciliados": len(matches),
        "porcentaje_conciliado": pct_conciliado,
        "monto_sin_comprobante": round(tot_sin_comprobante, 2),
        "total_sin_comprobante": len(gastos_sin_comprobante),
        "monto_comprobantes_pendientes": round(tot_comp_pendientes, 2),
        "total_comprobantes_pendientes": len(comprobantes_pendientes)
    }

    return {
        "kpis": kpis_dict,
        "resumen": kpis_dict,
        "conciliados": tablero_cruce,
        "matches_puros": matches,
        "movimientos_banco": movimientos_filtrados,
        "comprobantes": comprobantes_filtrados,
        "gastos_sin_comprobante": gastos_sin_comprobante,
        "comprobantes_pendientes": comprobantes_pendientes
    }

# ==============================================================================
# PARSERS DE ESTADOS DE CUENTA BANCARIOS (EXCEL, CSV, TXT)
# ==============================================================================
def parsear_estado_cuenta_archivo(file_path, banco="BBVA", empresa="BALDOMERO MEDINA GARZA", cuenta_nombre=""):
    """Lee y extrae transacciones bancarias desde un archivo Excel (.xlsx, .xls) o CSV."""
    if not os.path.exists(file_path):
        return []

    movimientos = []
    ext = os.path.splitext(file_path)[1].lower()

    if ext in ['.xlsx', '.xls']:
        try:
            import pandas as pd
            df = pd.read_excel(file_path, header=None)
            movimientos = procesar_dataframe_bancario(df, banco, empresa, cuenta_nombre)
        except Exception as e:
            print(f"[WARN Excel Bank Parse]: {e}")
    elif ext in ['.csv', '.txt']:
        try:
            import pandas as pd
            df = pd.read_csv(file_path, header=None, sep=None, engine='python')
            movimientos = procesar_dataframe_bancario(df, banco, empresa, cuenta_nombre)
        except Exception:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                texto = f.read()
                movimientos = parsear_texto_movimientos_bancarios(texto, banco, empresa, cuenta_nombre)
    
    # Guardar nuevos movimientos sin duplicar
    if movimientos:
        existentes = cargar_json(ESTADOS_CUENTA_FILE, [])
        mapa_existentes = {f"{m.get('fecha')}_{m.get('cargo')}_{normalizar_cadena(m.get('descripcion'))[:30]}": m for m in existentes}
        nuevos_agregados = 0
        for mov in movimientos:
            key = f"{mov.get('fecha')}_{mov.get('cargo')}_{normalizar_cadena(mov.get('descripcion'))[:30]}"
            if key not in mapa_existentes:
                existentes.append(mov)
                mapa_existentes[key] = mov
                nuevos_agregados += 1
        guardar_json(ESTADOS_CUENTA_FILE, existentes)

    return movimientos

def procesar_dataframe_bancario(df, banco="BBVA", empresa="BALDOMERO MEDINA GARZA", cuenta_nombre=""):
    """Detecta filas y columnas de fecha, concepto, cargo, abono y saldo."""
    movimientos = []
    for idx, row in df.iterrows():
        fila_str = " ".join([str(val) for val in row.values if str(val) != "nan" and str(val) != "None"])
        fila_norm = normalizar_cadena(fila_str)

        # Ignorar encabezados comunes
        if any(h in fila_norm for h in ['fecha', 'concepto', 'saldo inicial', 'movimientos del periodo', 'estado de cuenta']):
            continue

        # Extraer montos
        montos_encontrados = re.findall(r'[-+]?\$?\s*([\d,]+\.\d{2})', fila_str)
        if not montos_encontrados:
            continue

        fecha_val = parsear_fecha_flexible(fila_str)
        
        # Determinar cargo / retiro
        cargo_val = float(montos_encontrados[0].replace(",", ""))
        
        # Buscar claves de rastreo o referencias
        m_bnet = re.search(r'(BNET\d+|[A-Z0-9]{15,30})', fila_str)
        clave_rastreo = m_bnet.group(1) if m_bnet else ""

        m_ref = re.search(r'(?:REF|REFERENCIA|FOLIO|AUT)[:\s]*(\d+)', fila_str, re.IGNORECASE)
        ref_val = m_ref.group(1) if m_ref else ""

        mov_id = f"MOV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        movimientos.append({
            "id": mov_id,
            "empresa": empresa,
            "banco": banco,
            "cuenta": cuenta_nombre or f"{banco} Principal",
            "fecha": fecha_val,
            "descripcion": fila_str[:180].strip(),
            "referencia": ref_val,
            "clave_rastreo": clave_rastreo,
            "tipo": "CARGO",
            "cargo": cargo_val,
            "abono": 0.0,
            "saldo": 0.0
        })
    return movimientos

def parsear_texto_movimientos_bancarios(texto, banco="BBVA", empresa="BALDOMERO MEDINA GARZA", cuenta_nombre=""):
    """Parsea texto libre copiado del portal bancario o WhatsApp."""
    lineas = texto.strip().split("\n")
    movimientos = []
    for l in lineas:
        l = l.strip()
        if not l:
            continue
        m_imp = re.search(r'[-+]?\$?\s*([\d,]+\.\d{2})', l)
        if not m_imp:
            continue
        
        cargo_val = float(m_imp.group(1).replace(",", ""))
        fecha_val = parsear_fecha_flexible(l)
        
        m_bnet = re.search(r'(BNET\d+|[A-Z0-9]{15,30})', l)
        clave_rastreo = m_bnet.group(1) if m_bnet else ""

        m_ref = re.search(r'(?:REF|REFERENCIA|FOLIO)[:\s]*(\d+)', l, re.IGNORECASE)
        ref_val = m_ref.group(1) if m_ref else ""

        mov_id = f"MOV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        movimientos.append({
            "id": mov_id,
            "empresa": empresa,
            "banco": banco,
            "cuenta": cuenta_nombre or f"{banco} Principal",
            "fecha": fecha_val,
            "descripcion": l[:180].strip(),
            "referencia": ref_val,
            "clave_rastreo": clave_rastreo,
            "tipo": "CARGO",
            "cargo": cargo_val,
            "abono": 0.0,
            "saldo": 0.0
        })
    return movimientos

# ==============================================================================
# EXPORTACIÓN A EXCEL PRO
# ==============================================================================
def generar_excel_conciliacion(empresa="TODAS (Consolidado)", mes=None, anio=None):
    """Genera un libro de Excel profesional con formato corporativo y 4 hojas de análisis."""
    data = ejecutar_conciliacion_engine(empresa, mes, anio)
    resumen = data["resumen"]
    conciliados = data["conciliados"]
    sin_comprobante = data["gastos_sin_comprobante"]
    pendientes = data["comprobantes_pendientes"]

    wb = Workbook()
    
    # Fuentes y estilos
    font_titulo = Font(name='Segoe UI', size=16, bold=True, color='FFFFFF')
    font_subtitulo = Font(name='Segoe UI', size=11, bold=True, color='CBD5E1')
    font_header = Font(name='Segoe UI', size=10, bold=True, color='FFFFFF')
    font_body = Font(name='Segoe UI', size=9, color='1E293B')
    font_bold = Font(name='Segoe UI', size=9, bold=True, color='0F172A')
    font_kpi_num = Font(name='Segoe UI', size=14, bold=True, color='0F172A')

    fill_dark = PatternFill(start_color='0F172A', end_color='0F172A', fill_type='solid')
    fill_blue_head = PatternFill(start_color='1E3A8A', end_color='1E3A8A', fill_type='solid')
    fill_emerald_head = PatternFill(start_color='065F46', end_color='065F46', fill_type='solid')
    fill_rose_head = PatternFill(start_color='881337', end_color='881337', fill_type='solid')
    fill_amber_head = PatternFill(start_color='78350F', end_color='78350F', fill_type='solid')
    fill_zebra = PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid')

    border_thin = Border(
        left=Side(style='thin', color='E2E8F0'), right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'), bottom=Side(style='thin', color='E2E8F0')
    )

    # ──────────────────────────────────────────────────────────────────────────
    # HOJA 1: RESUMEN EJECUTIVO & CONCILIADOS
    # ──────────────────────────────────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Conciliación Bancaria"
    ws1.views.sheetView[0].showGridLines = True

    # Encabezado
    ws1.merge_cells('A1:I1')
    ws1['A1'] = f"CHALLENGER AUTOMOTIVE — CONCILIACIÓN DE GASTOS Y ESTADOS DE CUENTA"
    ws1['A1'].font = font_titulo
    ws1['A1'].fill = fill_dark
    ws1['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws1.row_dimensions[1].height = 35

    ws1.merge_cells('A2:I2')
    ws1['A2'] = f"Empresa: {resumen['empresa']}  |  Período: {mes or 'Todos'}/{anio or 'Todos'}  |  Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws1['A2'].font = font_subtitulo
    ws1['A2'].fill = fill_dark
    ws1['A2'].alignment = Alignment(horizontal='center', vertical='center')
    ws1.row_dimensions[2].height = 22

    # KPIs Cards
    kpis = [
        ("Total Egresos Banco", resumen.get("total_banco_egresos", 0.0), "A4:B4", "A5:B5"),
        ("Comprobantes Subidos", resumen.get("total_comprobantes_monto", 0.0), "C4:D4", "C5:D5"),
        ("Monto Conciliado", resumen.get("monto_conciliado", 0.0), "E4:F4", "E5:F5"),
        ("Sin Comprobante (Faltante)", resumen.get("monto_sin_comprobante", 0.0), "G4:G4", "G5:G5"),
        ("% Conciliado", f"{resumen.get('porcentaje_conciliado', 0.0)}%", "H4:I4", "H5:I5")
    ]

    for label, val, r1, r2 in kpis:
        ws1.merge_cells(r1)
        ws1.merge_cells(r2)
        top_left_1 = r1.split(':')[0]
        top_left_2 = r2.split(':')[0]
        ws1[top_left_1] = label
        ws1[top_left_1].font = Font(name='Segoe UI', size=9, bold=True, color='64748B')
        ws1[top_left_1].alignment = Alignment(horizontal='center', vertical='center')
        ws1[top_left_2] = fmt_dinero(val) if isinstance(val, (int, float)) else str(val)
        ws1[top_left_2].font = font_kpi_num
        ws1[top_left_2].alignment = Alignment(horizontal='center', vertical='center')

    # Tabla de Conciliados
    headers_1 = ["#", "Fecha Banco", "Banco / Cuenta", "Descripción Estado de Cuenta", "Cargo Banco", "Fecha Comp.", "Proveedor / A quién fue", "Concepto / Ref", "Importe Comp.", "Estatus"]
    row_num = 7
    for col_idx, h in enumerate(headers_1, 1):
        cell = ws1.cell(row=row_num, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_emerald_head
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    ws1.row_dimensions[row_num].height = 26

    matches_list = data.get("matches_puros") or [c for c in conciliados if c.get("estado_conciliacion") == "CONCILIADO"]

    for idx, item in enumerate(matches_list, 1):
        row_num += 1
        mov = item.get("movimiento") or item.get("movimiento_banco") or {}
        comp = item.get("comprobante") or {}
        row_data = [
            idx,
            mov.get("fecha", "-"),
            f"{mov.get('banco', 'BANCO')} - {mov.get('cuenta', 'Principal')}",
            mov.get("descripcion") or mov.get("concepto") or "-",
            mov.get("cargo", 0.0),
            comp.get("fecha", "-"),
            comp.get("proveedor_asignado") or comp.get("beneficiario") or comp.get("proveedor") or "-",
            f"{comp.get('concepto', '')} ({comp.get('clave_rastreo', '')})",
            comp.get("monto_total") or comp.get("total") or comp.get("importe") or comp.get("monto") or 0.0,
            "CONCILIADO"
        ]
        for col_idx, val in enumerate(row_data, 1):
            cell = ws1.cell(row=row_num, column=col_idx, value=val)
            cell.font = font_body
            cell.border = border_thin
            if idx % 2 == 0:
                cell.fill = fill_zebra
            if col_idx in [5, 9]:
                cell.number_format = '$#,##0.00'
                cell.alignment = Alignment(horizontal='right')
            elif col_idx in [1, 2, 6, 10]:
                cell.alignment = Alignment(horizontal='center')

    # ──────────────────────────────────────────────────────────────────────────
    # HOJA 2: SALIDAS DE BANCO SIN COMPROBANTE (ALERTAS ROJAS)
    # ──────────────────────────────────────────────────────────────────────────
    ws2 = wb.create_sheet(title="Sin Comprobante (Faltantes)")
    ws2.views.sheetView[0].showGridLines = True

    ws2.merge_cells('A1:G1')
    ws2['A1'] = "ALERTAS DE EGRESOS BANCARIOS SIN COMPROBANTE DE GASTO"
    ws2['A1'].font = font_titulo
    ws2['A1'].fill = fill_rose_head
    ws2['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws2.row_dimensions[1].height = 32

    headers_2 = ["#", "Fecha Movimiento", "Empresa", "Banco / Cuenta", "Descripción del Cargo", "Clave / Referencia", "Cargo Banco ($)"]
    row_num = 3
    for col_idx, h in enumerate(headers_2, 1):
        cell = ws2.cell(row=row_num, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_rose_head
        cell.alignment = Alignment(horizontal='center', vertical='center')
    ws2.row_dimensions[row_num].height = 24

    for idx, mov in enumerate(sin_comprobante, 1):
        row_num += 1
        row_data = [
            idx,
            mov.get("fecha"),
            mov.get("empresa"),
            f"{mov.get('banco')} - {mov.get('cuenta')}",
            mov.get("descripcion"),
            mov.get("clave_rastreo") or mov.get("referencia") or "—",
            mov.get("cargo")
        ]
        for col_idx, val in enumerate(row_data, 1):
            cell = ws2.cell(row=row_num, column=col_idx, value=val)
            cell.font = font_body
            cell.border = border_thin
            if idx % 2 == 0:
                cell.fill = fill_zebra
            if col_idx == 7:
                cell.number_format = '$#,##0.00'
                cell.font = font_bold
                cell.alignment = Alignment(horizontal='right')
            elif col_idx in [1, 2]:
                cell.alignment = Alignment(horizontal='center')

    # ──────────────────────────────────────────────────────────────────────────
    # HOJA 3: COMPROBANTES PENDIENTES EN BANCO
    # ──────────────────────────────────────────────────────────────────────────
    ws3 = wb.create_sheet(title="Comprobantes Pendientes")
    ws3.views.sheetView[0].showGridLines = True

    ws3.merge_cells('A1:H1')
    ws3['A1'] = "COMPROBANTES REPORTADOS PENDIENTES DE REFLEJARSE EN BANCO"
    ws3['A1'].font = font_titulo
    ws3['A1'].fill = fill_amber_head
    ws3['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws3.row_dimensions[1].height = 32

    headers_3 = ["#", "Fecha Comp.", "Empresa", "Proveedor / Destinatario", "Concepto", "Banco / Cuenta Origen", "Clave Rastreo / Folio", "Importe ($)"]
    row_num = 3
    for col_idx, h in enumerate(headers_3, 1):
        cell = ws3.cell(row=row_num, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_amber_head
        cell.alignment = Alignment(horizontal='center', vertical='center')
    ws3.row_dimensions[row_num].height = 24

    for idx, comp in enumerate(pendientes, 1):
        row_num += 1
        row_data = [
            idx,
            comp.get("fecha"),
            comp.get("empresa"),
            comp.get("proveedor_asignado") or comp.get("beneficiario"),
            comp.get("concepto"),
            f"{comp.get('banco_origen')} - {comp.get('cuenta_origen')}",
            comp.get("clave_rastreo") or comp.get("folio_operacion") or "—",
            comp.get("importe")
        ]
        for col_idx, val in enumerate(row_data, 1):
            cell = ws3.cell(row=row_num, column=col_idx, value=val)
            cell.font = font_body
            cell.border = border_thin
            if idx % 2 == 0:
                cell.fill = fill_zebra
            if col_idx == 8:
                cell.number_format = '$#,##0.00'
                cell.font = font_bold
                cell.alignment = Alignment(horizontal='right')
            elif col_idx in [1, 2]:
                cell.alignment = Alignment(horizontal='center')

    # Autoajustar ancho de columnas en todas las hojas
    for sheet in [ws1, ws2, ws3]:
        for col in sheet.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value:
                    val_str = str(cell.value)
                    if len(val_str) > max_len and len(val_str) < 60:
                        max_len = len(val_str)
            sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Guardar en archivo temporal
    export_path = os.path.join(DATA_DIR, f"Reporte_Conciliacion_Gastos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    wb.save(export_path)
    return export_path
