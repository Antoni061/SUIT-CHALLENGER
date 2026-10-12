"""
IMPORTADOR AUTOMÁTICO DE ESTADOS DE CUENTA REALES EN PDF
=========================================================
Parsea con precisión militar los 2 estados de cuenta PDF enviados por el usuario:
1. Kapital Bank (Agosto 2026) -> BALDOMERO MEDINA GARZA
2. BBVA Maestra Pyme (Agosto 2026) -> AUTO LINEA MULTITRANS SA DE CV
"""

import os, re, json, uuid
from datetime import datetime
import pypdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ESTADOS_CUENTA_FILE = os.path.join(DATA_DIR, "banco_movimientos.json")
COMPROBANTES_FILE = os.path.join(DATA_DIR, "gastos_comprobantes.json")

def normalizar_fecha(fecha_str, anio="2026"):
    if not fecha_str:
        return f"{anio}-08-01"
    
    meses = {
        'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
    }
    
    # 05-Ago-2026
    m1 = re.search(r'(\d{1,2})-([A-Za-z]{3})-(\d{4})', fecha_str)
    if m1:
        d, m, y = m1.groups()
        m_num = meses.get(m.lower()[:3], '08')
        return f"{y}-{m_num}-{int(d):02d}"
    
    # 01/AGO
    m2 = re.search(r'(\d{1,2})/([A-Za-z]{3})', fecha_str)
    if m2:
        d, m = m2.groups()
        m_num = meses.get(m.lower()[:3], '08')
        return f"{anio}-{m_num}-{int(d):02d}"
        
    return f"{anio}-08-01"

def parsear_kapital_pdf(pdf_path):
    reader = pypdf.PdfReader(pdf_path)
    all_text = ""
    for page in reader.pages:
        all_text += page.extract_text() + "\n"
    
    pattern = r'(\d{2}-[A-Za-z]{3}-\d{4})\s+([A-Z0-9;]+)\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([-]?[\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})'
    matches = list(re.finditer(pattern, all_text))
    
    movimientos = []
    last_end = 0
    
    for idx, m in enumerate(matches):
        fecha_raw, ref, dep_str, ret_str, saldo_str = m.groups()
        start_pos = m.start()
        
        preceding = all_text[last_end:start_pos].strip()
        lines_prec = [
            l.strip() for l in preceding.split('\n')
            if l.strip() and not l.startswith('Página') and not l.startswith('Pgina')
            and not l.startswith('Número') and not l.startswith('Nmero')
            and not l.startswith('DETALLE DE MOVIMIENTOS') and not l.startswith('FECHA CONCEPTO')
            and not 'KPTL MEXICO' in l and not 'IPAB' in l and not 'kapital.com' in l
            and not 'La reproducción' in l
        ]
        concepto = ' '.join(lines_prec).strip() or "Movimiento Kapital"
        last_end = m.end()
        
        dep = float(dep_str.replace(',', ''))
        ret = abs(float(ret_str.replace(',', '')))
        saldo = float(saldo_str.replace(',', ''))
        
        fecha_iso = normalizar_fecha(fecha_raw)
        
        # Clasificar cargo o abono
        tipo = "CARGO" if ret > 0 else "ABONO"
        monto_cargo = ret if ret > 0 else 0.0
        monto_abono = dep if dep > 0 else 0.0
        
        # Extraer SAT UUID o beneficiario
        m_sat = re.search(r'SAT\s*([A-F0-9]{32,36})', concepto, re.IGNORECASE)
        sat_uuid = m_sat.group(1) if m_sat else ""
        
        m_banco_dest = re.search(r'BANCO\s+([A-Z\s]+?)(?:CUENTA|SAT|$)', concepto)
        banco_dest = m_banco_dest.group(1).strip() if m_banco_dest else ""
        
        mov_id = f"KPTL-{fecha_iso.replace('-', '')}-{idx+1:04d}-{uuid.uuid4().hex[:4]}"
        
        movimientos.append({
            "id": mov_id,
            "empresa": "BALDOMERO MEDINA GARZA",
            "banco": "KAPITAL BANK",
            "cuenta": "Cuenta Mi Pyme BAM 00001590968",
            "fecha": fecha_iso,
            "descripcion": concepto[:250].strip(),
            "concepto": concepto[:250].strip(),
            "referencia": ref,
            "clave_rastreo": sat_uuid or ref,
            "banco_destino": banco_dest,
            "tipo": tipo,
            "cargo": monto_cargo,
            "abono": monto_abono,
            "saldo": saldo,
            "conciliado": False,
            "comprobante_id": None
        })
    
    return movimientos

def parsear_bbva_pdf(pdf_path):
    reader = pypdf.PdfReader(pdf_path)
    all_text = ""
    for p_idx in range(1, 13):
        all_text += reader.pages[p_idx].extract_text() + "\n"
    
    # Expresión para líneas de movimiento
    date_pattern = r'(\d{2}/[A-Za-z]{3})\s+(\d{2}/[A-Za-z]{3})\s+([A-Z0-9]{2,4})\s+([^\n\d]+?)\s+([\d,]+\.\d{2})(?:\s+([\d,]+\.\d{2}))?(?:\s+([\d,]+\.\d{2}))?'
    matches = list(re.finditer(date_pattern, all_text))
    
    movimientos = []
    
    for i in range(len(matches)):
        m = matches[i]
        f_op, f_liq, cod, desc, m1, m2, m3 = m.groups()
        start_pos = m.start()
        end_pos = matches[i+1].start() if i+1 < len(matches) else len(all_text)
        
        # Bloque de contexto para buscar nombres de beneficiarios, conceptos y rastreo BNET
        # Revisamos líneas antes (para nombres que aparecen arriba) y después
        context_before = all_text[max(0, start_pos - 150):start_pos]
        context_after = all_text[start_pos:min(len(all_text), end_pos + 100)]
        
        full_block = context_before + "\n" + context_after
        
        # Buscar Beneficiario (líneas en mayúsculas de 2 a 4 palabras)
        beneficiario = ""
        for line in context_before.split('\n')[-3:] + context_after.split('\n')[:4]:
            line_s = line.strip()
            if (len(line_s.split()) >= 2 and len(line_s) > 5 and len(line_s) < 45 
                and line_s.isupper() 
                and not any(k in line_s for k in ['BBVA', 'PAGINA', 'ESTADO', 'MAESTRA', 'FECHA', 'SALDO', 'OPER', 'CARGOS', 'ABONOS', 'AV.', 'MEXICO', 'RFC', 'TERMINALES', 'VENTAS'])):
                beneficiario = line_s
                break
        
        # Buscar Clave de Rastreo BNET o SPIN
        m_bnet = re.search(r'(BNET\d{15,30}|SPIN-\d+[\w]+|CPO\d+)', full_block)
        clave_rastreo = m_bnet.group(1) if m_bnet else ""
        
        # Buscar Referencia numérica
        m_ref = re.search(r'Ref\.\s*(\d+)', full_block)
        referencia_num = m_ref.group(1) if m_ref else ""
        
        # Buscar Concepto específico
        m_concepto_extra = re.search(r'(?:Ref\.\s*\d+[\s\d]*\n|\d{7,10}\s+)([\w\s\*\-]+?)(?:\s+Ref|\n|$)', context_after)
        concepto_detalle = m_concepto_extra.group(1).strip() if m_concepto_extra else ""
        
        fecha_iso = normalizar_fecha(f_op)
        
        val1 = float(m1.replace(',', ''))
        val2 = float(m2.replace(',', '')) if m2 else 0.0
        val3 = float(m3.replace(',', '')) if m3 else 0.0
        
        # En BBVA: si el código es V42, V45, AA7, T20 (SPEI RECIBIDO), T22 (DEVUELTO) -> Abono
        # Si el código es A01, V43, V44, V46, V47, T17 (SPEI ENVIADO), N06, H09, P31, S39, S40, X01, K45, G30 -> Cargo
        cod_upper = cod.upper()
        es_abono = cod_upper in ['V42', 'V45', 'AA7', 'T22'] or ('RECIBIDO' in desc.upper())
        
        if es_abono:
            cargo = 0.0
            abono = val1
            tipo = "ABONO"
        else:
            cargo = val1
            abono = 0.0
            tipo = "CARGO"
            
        saldo = val3 if val3 > 0 else (val2 if val2 > 0 else 0.0)
        
        desc_completa = f"{cod} {desc.strip()}"
        if beneficiario:
            desc_completa += f" — {beneficiario}"
        if concepto_detalle:
            desc_completa += f" ({concepto_detalle})"
            
        mov_id = f"BBVA-{fecha_iso.replace('-', '')}-{i+1:04d}-{uuid.uuid4().hex[:4]}"
        
        movimientos.append({
            "id": mov_id,
            "empresa": "AUTO LINEA MULTITRANS",
            "banco": "BBVA",
            "cuenta": "Maestra Pyme BBVA 0122351684",
            "fecha": fecha_iso,
            "descripcion": desc_completa[:250],
            "concepto": desc_completa[:250],
            "referencia": clave_rastreo or referencia_num or cod,
            "clave_rastreo": clave_rastreo,
            "beneficiario": beneficiario,
            "tipo": tipo,
            "cargo": cargo,
            "abono": abono,
            "saldo": saldo,
            "conciliado": False,
            "comprobante_id": None
        })
        
    return movimientos

def main():
    pdf_kapital = r"C:\Users\usuario\.gemini\antigravity\brain\6ddca8b1-dfd2-42c4-a0eb-ee3dc8d4736f\.user_uploaded\media_1790628518091.pdf"
    pdf_bbva = r"C:\Users\usuario\.gemini\antigravity\brain\6ddca8b1-dfd2-42c4-a0eb-ee3dc8d4736f\.user_uploaded\media_1790628523985.pdf"
    
    print("Iniciando extraccion de movimientos reales de los estados de cuenta...")
    
    movs_k = parsear_kapital_pdf(pdf_kapital)
    print(f"[OK] Kapital Bank: {len(movs_k)} movimientos extraidos (Baldomero Medina Garza).")
    
    movs_b = parsear_bbva_pdf(pdf_bbva)
    print(f"[OK] BBVA: {len(movs_b)} movimientos extraidos (Auto Linea Multitrans).")
    
    todos_movimientos = movs_k + movs_b
    
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ESTADOS_CUENTA_FILE, 'w', encoding='utf-8') as f:
        json.dump(todos_movimientos, f, indent=2, ensure_ascii=False)
        
    print(f"[OK] Total de {len(todos_movimientos)} movimientos guardados en {ESTADOS_CUENTA_FILE}.")

if __name__ == "__main__":
    main()
