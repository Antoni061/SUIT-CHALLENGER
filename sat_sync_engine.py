"""
MOTOR DE SINCRONIZACIÓN Y CONSULTA SAT PURA (CFDI 4.0 / 3.3 Engine)
===================================================================
Procesa y consulta exclusivamente Facturas Oficiales del SAT (XMLs CFDI)
con soporte de descarga individual en XML, exportación masiva en ZIP,
representación gráfica para impresión/PDF y cálculo exacto en USD y MXN.
"""

import xml.etree.ElementTree as ET
import os, json, glob, uuid, time, calendar, io, zipfile, base64
from datetime import datetime, date

from satcfdi.portal import Signer
from satcfdi.pacs.sat import SAT, EstadoComprobante

from odoo_sync_engine import (
    conectar_odoo, ODOO_DB, ODOO_API_KEY, EMPRESAS,
    normalizar_texto, fmt_mxn, fmt_num
)

SAT_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sat_config.json")
XML_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xml_proveedores")
INDEX_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sat_xml_index.json")

os.makedirs(XML_STORAGE_DIR, exist_ok=True)

CHALLENGER_RFCS = {
    "MEGB620114JX6": "BALDOMERO MEDINA GARZA",
    "ALM0003033S6": "AUTO LINEA MULTITRANS"
}

# ── CONFIGURACIÓN Y CREDENCIALES FIEL ───────────────────────────────────────
def cargar_config_fiel():
    if os.path.exists(SAT_CONFIG_FILE):
        try:
            with open(SAT_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"cer_path": "", "key_path": "", "password": "", "rfc": ""}

def guardar_config_fiel(cer_path, key_path, password, rfc=""):
    cfg = {"cer_path": cer_path, "key_path": key_path, "password": password, "rfc": rfc}
    with open(SAT_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg


# ── DESCARGA AUTOMÁTICA MASIVA DESDE EL SAT CON FIEL ─────────────────────────
def descargar_cfdis_sat(cer_path=None, key_path=None, password=None, anio=None, mes=None):
    cfg = cargar_config_fiel()
    cer_p = cer_path or cfg.get("cer_path")
    key_p = key_path or cfg.get("key_path")
    pwd   = password or cfg.get("password")

    if not cer_p or not key_p or not pwd:
        raise Exception("Faltan las credenciales de la e.firma (FIEL): .cer, .key o contraseña.")

    if not os.path.exists(cer_p) or not os.path.exists(key_p):
        raise Exception(f"No se encontraron los archivos de la FIEL en el disco: {cer_p} o {key_p}")

    with open(cer_p, "rb") as f: cer_bytes = f.read()
    with open(key_p, "rb") as f: key_bytes = f.read()

    signer = Signer.load(cer_bytes, key_bytes, pwd)
    rfc_empresa = signer.rfc

    if cer_path and key_path and password:
        guardar_config_fiel(cer_p, key_p, pwd, rfc=rfc_empresa)

    sat_ws = SAT(signer)

    now = datetime.now()
    target_year = int(anio or now.year)
    target_month = int(mes or now.month)

    from datetime import timedelta
    _, max_day = calendar.monthrange(target_year, target_month)

    f_ini = datetime(target_year, target_month, 1, 0, 0, 0)
    if target_year == now.year and target_month == now.month:
        f_fin = now - timedelta(hours=3)
    else:
        f_fin = datetime(target_year, target_month, max_day, 23, 59, 59)

    # 1. Solicitar descarga al SAT
    res_sol = sat_ws.recover_comprobante_received_request(
        fecha_inicial=f_ini,
        fecha_final=f_fin,
        estado_comprobante=EstadoComprobante.VIGENTE
    )

    if res_sol.get("CodEstatus") not in ("5000", "5004"):
        raise Exception(f"El SAT respondió: {res_sol.get('Mensaje')} (Código: {res_sol.get('CodEstatus')})")

    sol_id = res_sol.get("IdSolicitud")

    def _bg_downloader(ws_client, ticket_id):
        for _ in range(12):
            time.sleep(5)
            try:
                st = ws_client.recover_comprobante_status(ticket_id)
                pkgs = st.get("IdsPaquetes", [])
                if pkgs:
                    for pkg_id in pkgs:
                        pkg_bytes = ws_client.recover_comprobante_download(pkg_id)
                        if pkg_bytes:
                            with zipfile.ZipFile(io.BytesIO(pkg_bytes)) as zf:
                                for fname in zf.namelist():
                                    if fname.endswith(".xml"):
                                        out_p = os.path.join(XML_STORAGE_DIR, os.path.basename(fname))
                                        with open(out_p, "wb") as f_out:
                                            f_out.write(zf.read(fname))
                    construir_indice_sat_xmls(force=True)
                    break
            except Exception:
                pass

    import threading
    threading.Thread(target=_bg_downloader, args=(sat_ws, sol_id), daemon=True).start()

    return {
        "success": True,
        "solicitud_id": sol_id,
        "rfc_empresa": rfc_empresa,
        "razon_social": signer.legal_name,
        "mensaje": f"¡Solicitud aceptada por el SAT! (Ticket #{sol_id[:8]}). Descargando facturas de {signer.legal_name} en segundo plano..."
    }


# ── SINCRONIZADOR DE XMLs DESDE ADJUNTOS DE ODOO A DISCO ──────────────────────
def sincronizar_xmls_odoo_a_disco():
    try:
        uid, models = conectar_odoo(1)
        domain = [('res_model', '=', 'account.move'), ('name', 'like', '%.xml')]
        atts = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'ir.attachment', 'search_read',
            [domain],
            {'fields': ['id', 'name', 'res_id', 'datas'], 'limit': 3000}
        )
        guardados = 0
        for a in atts:
            if not a.get('datas'): continue
            try:
                raw = base64.b64decode(a['datas'])
                root = ET.fromstring(raw)
                for elem in root.iter():
                    if '}' in elem.tag: elem.tag = elem.tag.split('}', 1)[1]
                uuid_str = ""
                for elem in root.iter('TimbreFiscalDigital'):
                    uuid_str = elem.attrib.get('UUID', '').upper()
                    break
                if uuid_str:
                    target_path = os.path.join(XML_STORAGE_DIR, f"{uuid_str}.xml")
                    if not os.path.exists(target_path):
                        with open(target_path, 'wb') as f:
                            f.write(raw)
                        guardados += 1
            except Exception:
                pass
        return guardados
    except Exception as e:
        print(f"[ERROR sincronizar_xmls_odoo_a_disco]: {e}")
        return 0


# ── PARSER DE XML CFDI (3.3 y 4.0) ──────────────────────────────────────────
def parsear_xml_cfdi(filepath):
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except Exception:
        return None

    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]

    if root.tag != "Comprobante":
        return None

    tipo = root.attrib.get("TipoDeComprobante", "I").upper()
    fecha = root.attrib.get("Fecha", "")
    total = float(root.attrib.get("Total", 0.0) or 0.0)
    subtotal = float(root.attrib.get("SubTotal", 0.0) or 0.0)
    moneda = root.attrib.get("Moneda", "MXN").upper()
    metodo_pago = root.attrib.get("MetodoPago", "PUE").upper()
    forma_pago = root.attrib.get("FormaPago", "")
    serie = root.attrib.get("Serie", "")
    folio_attr = root.attrib.get("Folio", "")
    folio = f"{serie}{folio_attr}".strip() if (serie or folio_attr) else os.path.basename(filepath)

    tc_cfdi = float(root.attrib.get("TipoCambio", 0.0) or 0.0)
    if tc_cfdi <= 0.0:
        tc_cfdi = 17.0427 if moneda == "USD" else 1.0

    uuid_str = ""
    fecha_timbrado = ""
    no_certificado_sat = ""
    sello_cfd = root.attrib.get("Sello", "")
    sello_sat = ""
    for elem in root.iter("TimbreFiscalDigital"):
        uuid_str = elem.attrib.get("UUID", "").upper()
        fecha_timbrado = elem.attrib.get("FechaTimbrado", "")
        no_certificado_sat = elem.attrib.get("NoCertificadoSAT", "")
        sello_sat = elem.attrib.get("SelloSAT", "")
        break

    if not uuid_str:
        return None

    emisor_elem = root.find("Emisor")
    rfc_emisor = emisor_elem.attrib.get("Rfc", "").upper() if emisor_elem is not None else ""
    nombre_emisor = emisor_elem.attrib.get("Nombre", rfc_emisor) if emisor_elem is not None else "Proveedor Desconocido"
    regimen_emisor = emisor_elem.attrib.get("RegimenFiscal", "") if emisor_elem is not None else ""

    receptor_elem = root.find("Receptor")
    rfc_receptor = receptor_elem.attrib.get("Rfc", "").upper() if receptor_elem is not None else ""
    nombre_receptor = receptor_elem.attrib.get("Nombre", rfc_receptor) if receptor_elem is not None else ""
    uso_cfdi = receptor_elem.attrib.get("UsoCFDI", "G03") if receptor_elem is not None else ""

    # Conceptos
    conceptos = []
    for c in root.iter("Concepto"):
        conceptos.append({
            "clave_prod_serv": c.attrib.get("ClaveProdServ", ""),
            "no_identificacion": c.attrib.get("NoIdentificacion", ""),
            "descripcion": c.attrib.get("Descripcion", ""),
            "cantidad": float(c.attrib.get("Cantidad", 1.0) or 1.0),
            "clave_unidad": c.attrib.get("ClaveUnidad", ""),
            "unidad": c.attrib.get("Unidad", ""),
            "valor_unitario": float(c.attrib.get("ValorUnitario", 0.0) or 0.0),
            "importe": float(c.attrib.get("Importe", 0.0) or 0.0),
            "descuento": float(c.attrib.get("Descuento", 0.0) or 0.0),
        })

    # Impuestos
    impuestos_trasladados = 0.0
    impuestos_retenidos = 0.0
    for imp in root.iter("Impuestos"):
        impuestos_trasladados += float(imp.attrib.get("TotalImpuestosTrasladados", 0.0) or 0.0)
        impuestos_retenidos += float(imp.attrib.get("TotalImpuestosRetenidos", 0.0) or 0.0)

    # Documentos Relacionados en caso de Complemento de Pago (REP)
    doctos_relacionados = []
    if tipo == "P":
        for pago in root.iter("Pago"):
            fecha_pago = pago.attrib.get("FechaPago", fecha)
            monto_pago = float(pago.attrib.get("Monto", 0.0) or 0.0)
            moneda_pago = pago.attrib.get("MonedaP", "MXN")
            for doc in pago.iter("DoctoRelacionado"):
                id_doc = doc.attrib.get("IdDocumento", "").upper()
                imp_pagado = float(doc.attrib.get("ImpPagado", monto_pago) or 0.0)
                imp_saldo_ant = float(doc.attrib.get("ImpSaldoAnt", 0.0) or 0.0)
                imp_saldo_ins = float(doc.attrib.get("ImpSaldoInsoluto", 0.0) or 0.0)
                num_parcialidad = int(doc.attrib.get("NumParcialidad", 1) or 1)

                doctos_relacionados.append({
                    "uuid_factura": id_doc,
                    "fecha_pago": fecha_pago[:10],
                    "moneda": moneda_pago,
                    "imp_pagado": imp_pagado,
                    "imp_saldo_ant": imp_saldo_ant,
                    "imp_saldo_insoluto": imp_saldo_ins,
                    "num_parcialidad": num_parcialidad
                })

    # Total MXN oficial DOF
    if moneda == "USD":
        total_mxn = round(total * tc_cfdi, 2)
        subtotal_mxn = round(subtotal * tc_cfdi, 2)
    else:
        total_mxn = round(total, 2)
        subtotal_mxn = round(subtotal, 2)

    return {
        "uuid": uuid_str,
        "folio": folio,
        "serie": serie,
        "tipo": tipo,
        "fecha": fecha[:10] if fecha else "",
        "fecha_completa": fecha or fecha_timbrado,
        "fecha_timbrado": fecha_timbrado,
        "anio": fecha[:4] if fecha else "",
        "mes": int(fecha[5:7]) if (fecha and len(fecha) >= 7 and fecha[5:7].isdigit()) else 0,
        "rfc_emisor": rfc_emisor,
        "proveedor": nombre_emisor,
        "regimen_emisor": regimen_emisor,
        "rfc_receptor": rfc_receptor,
        "receptor": nombre_receptor,
        "uso_cfdi": uso_cfdi,
        "total": total,
        "subtotal": subtotal,
        "impuestos_trasladados": round(impuestos_trasladados, 2),
        "impuestos_retenidos": round(impuestos_retenidos, 2),
        "moneda": moneda,
        "is_usd": (moneda == "USD"),
        "tipo_cambio": round(tc_cfdi, 4),
        "total_mxn": total_mxn,
        "subtotal_mxn": subtotal_mxn,
        "metodo_pago": metodo_pago,
        "forma_pago": forma_pago,
        "conceptos": conceptos,
        "doctos_relacionados": doctos_relacionados,
        "filename": os.path.basename(filepath),
        "filepath": filepath,
        "no_certificado_sat": no_certificado_sat,
        "sello_cfd": sello_cfd,
        "sello_sat": sello_sat
    }


# ── GENERACIÓN Y LECTURA DEL ÍNDICE DE CACHÉ SAT ────────────────────────────
def construir_indice_sat_xmls(force=False):
    xml_files = glob.glob(os.path.join(XML_STORAGE_DIR, "*.xml"))
    
    if not force and os.path.exists(INDEX_CACHE_FILE):
        try:
            with open(INDEX_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if len(cached) == len(xml_files) and len(cached) > 0:
                return cached
        except Exception:
            pass

    indexed = {}
    for f in xml_files:
        p = parsear_xml_cfdi(f)
        if p and p.get("uuid"):
            indexed[p["uuid"]] = p

    try:
        with open(INDEX_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(indexed, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return indexed


# ── MOTOR PRINCIPAL: PROCESAR FACTURAS PURAS DEL SAT ─────────────────────────
def procesar_facturas_sat_puras(empresa_nombre="TODAS (Consolidado)", anio="TODOS", mes=0, tipo_comprobante="TODOS", direccion="PROVEEDORES"):
    indice = construir_indice_sat_xmls()
    cfdis = list(indice.values())

    challenger_rfcs = list(CHALLENGER_RFCS.keys())
    
    empresa_filtro_rfc = None
    if empresa_nombre == "BALDOMERO MEDINA GARZA":
        empresa_filtro_rfc = "MEGB620114JX6"
    elif empresa_nombre == "AUTO LINEA MULTITRANS":
        empresa_filtro_rfc = "ALM0003033S6"

    lista_filtrada = []
    for doc in cfdis:
        rfce = doc.get("rfc_emisor", "").upper()
        rfcr = doc.get("rfc_receptor", "").upper()

        es_recibida_proveedor = (rfcr in challenger_rfcs) or (rfce not in challenger_rfcs)
        es_emitida_cliente = (rfce in challenger_rfcs)

        if direccion == "PROVEEDORES" and not es_recibida_proveedor:
            continue
        elif direccion == "CLIENTES" and not es_emitida_cliente:
            continue

        if empresa_filtro_rfc:
            if direccion == "PROVEEDORES" and rfcr != empresa_filtro_rfc and rfcr in challenger_rfcs:
                continue
            elif direccion == "CLIENTES" and rfce != empresa_filtro_rfc:
                continue

        if anio and str(anio).upper() != "TODOS":
            if doc.get("anio") != str(anio).strip():
                continue

        if mes and int(mes) > 0:
            if doc.get("mes") != int(mes):
                continue

        if tipo_comprobante and tipo_comprobante.upper() != "TODOS":
            if doc.get("tipo") != tipo_comprobante.upper():
                continue

        lista_filtrada.append(doc)

    lista_filtrada.sort(key=lambda x: (x.get("fecha") or "", x.get("uuid") or ""), reverse=True)

    total_mxn = 0.0
    total_usd = 0.0
    total_subtotal_mxn = 0.0
    n_pue = 0
    n_ppd = 0
    n_rep = 0
    n_nc = 0
    provs_set = set()
    anios_detectados = set()

    for idx, doc in enumerate(lista_filtrada, 1):
        doc["posicion"] = idx
        total_mxn += doc.get("total_mxn", 0.0)
        total_subtotal_mxn += doc.get("subtotal_mxn", 0.0)
        
        if doc.get("is_usd"):
            total_usd += doc.get("total", 0.0)

        t = doc.get("tipo", "I")
        m = doc.get("metodo_pago", "PUE")
        
        if t == "I":
            if m == "PUE": n_pue += 1
            else: n_ppd += 1
        elif t == "P":
            n_rep += 1
        elif t == "E":
            n_nc += 1

        p_nombre = doc.get("proveedor") or doc.get("rfc_emisor") or ""
        if p_nombre:
            provs_set.add(p_nombre.strip().upper())

        y = doc.get("anio")
        if y: anios_detectados.add(y)

    anios_list = sorted(list(anios_detectados), reverse=True)
    if not anios_list:
        anios_list = ["2026", "2025", "2024", "2023"]

    return {
        "cuentas": lista_filtrada,
        "totales": {
            "total_facturas_sat": len(lista_filtrada),
            "num_facturas": len(lista_filtrada),
            "total_monto_mxn": round(total_mxn, 2),
            "total_deuda_consolidada_mxn": round(total_mxn, 2),
            "total_subtotal_mxn": round(total_subtotal_mxn, 2),
            "total_monto_usd": round(total_usd, 2),
            "total_deuda_usd": round(total_usd, 2),
            "proveedores_unicos": len(provs_set),
            "facturas_pue": n_pue,
            "facturas_ppd": n_ppd,
            "complementos_rep": n_rep,
            "notas_credito": n_nc,
            "tc_dof_actual": 17.0427,
            "anios_disponibles": anios_list,
            "empresa_seleccionada": empresa_nombre,
            "direccion": direccion
        }
    }


def procesar_cuentas_por_pagar(empresa_nombre="TODAS (Consolidado)", anio="TODOS", xml_dir=XML_STORAGE_DIR):
    return procesar_facturas_sat_puras(empresa_nombre=empresa_nombre, anio=anio, direccion="PROVEEDORES")


# ── OBTENER ARCHIVO XML PARA DESCARGA DIRECTA ────────────────────────────────
def obtener_xml_por_uuid(uuid_str):
    if not uuid_str: return None
    clean_uuid = uuid_str.strip().upper()
    
    direct_path = os.path.join(XML_STORAGE_DIR, f"{clean_uuid}.xml")
    if os.path.exists(direct_path):
        return direct_path

    indice = construir_indice_sat_xmls()
    doc = indice.get(clean_uuid)
    if doc:
        fp = doc.get("filepath")
        if fp and os.path.exists(fp): return fp
        fn = doc.get("filename")
        if fn:
            rel_p = os.path.join(XML_STORAGE_DIR, fn)
            if os.path.exists(rel_p): return rel_p

    for f in glob.glob(os.path.join(XML_STORAGE_DIR, "*.xml")):
        if clean_uuid in os.path.basename(f).upper():
            return f

    return None


# ── GENERADOR DE ARCHIVO ZIP CON FACTURAS SAT SELECCIONADAS ─────────────────
def generar_zip_facturas_sat(uuids=None, empresa_nombre="TODAS (Consolidado)", anio="TODOS", mes=0, direccion="PROVEEDORES"):
    if uuids:
        target_uuids = [u.strip().upper() for u in uuids if u.strip()]
        archivos = []
        for u in target_uuids:
            p = obtener_xml_por_uuid(u)
            if p: archivos.append((u, p))
    else:
        res = procesar_facturas_sat_puras(empresa_nombre=empresa_nombre, anio=anio, mes=mes, direccion=direccion)
        archivos = []
        for doc in res.get("cuentas", []):
            u = doc.get("uuid")
            p = doc.get("filepath") or obtener_xml_por_uuid(u)
            if p and os.path.exists(p):
                archivos.append((u, p))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for u, fpath in archivos:
            arcname = f"CFDI_SAT_{u}.xml"
            zf.write(fpath, arcname=arcname)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()
