"""
MOTOR DE SINCRONIZACIÓN Y CACHÉ ODOO 19 (Background Cron Sync Engine)
======================================================================
Maneja la conexión XML-RPC con Odoo 19, cálculo de comisiones, productos e inventario,
mantenimiento de caché persistente en disco y bucle de sincronización periódica en segundo plano.
"""

import xmlrpc.client
import json, os, calendar, unicodedata, time, math, re
from datetime import date, datetime, timedelta
import threading

# ── CONFIGURACIÓN ODOO ───────────────────────────────────────────────────────
ODOO_URL      = "https://challenger.odoo.com"
ODOO_DB       = "challenger"
ODOO_USER     = "e.zapatero@multitrans.mx"
ODOO_API_KEY  = "a2e7a464d404136e38afb0467adf823707f7fbdc"
PROP_VENDEDOR_KEY = "923a9347bd99f03b"

EMPRESAS = {
    "TODAS (Consolidado)": {"company_id": None, "prefijos_excluir": []},
    "BALDOMERO MEDINA GARZA": {"company_id": 1, "prefijos_excluir": ["PBNK1/"]},
    "AUTO LINEA MULTITRANS": {"company_id": 2, "prefijos_excluir": []},
}

CLIENTES_INTEREMPRESA_EXCLUIDOS = [
    "auto linea multitrans",
    "autolinea multitrans",
    "baldomero medina garza",
]

COMISION_CHALLENGER = 0.09
COMISION_MULTIMARCA = 0.09
COMISION_PASTA      = 0.025

PASTA_KW = [
    "easy master", "em800", "em-800", "em 800",
    "pasta r-50", "pasta r50", "pasta r-80", "pasta r80", "r-80-4",
    "body filler",
]

MATERIA_PRIMA_KW = [
    "materia prima", "materias primas", "mp al", "mp-", "[mp", " raw ",
    "resifel", "uracron", "joncryl", "synteven", "possalc", "omyacarb",
    "octoato", "peroxido", "resina ep", "resina para body",
    "[pig-", "[sol-", "[res-", "[env-", "[car-", "[adi-", "[cat-"
]

CLIENTES_ESPECIALES = {
    "sandra belinda medina": 0.05,
}

# ── CLASIFICACIÓN DE PRODUCTOS (embebida + comisiones_app import) ──
import sys
_scratch_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _scratch_dir not in sys.path:
    sys.path.append(_scratch_dir)

try:
    from comisiones_app import CLASIFICACION_PRODUCTOS as CLASIFICACION_PRODUCTOS_FULL
    CLASIFICACION_PRODUCTOS = CLASIFICACION_PRODUCTOS_FULL
except Exception:
    CLASIFICACION_PRODUCTOS = {
        "229-8801 PERRINDO MARRON 179": "CHALLENGER", "229-96424 PERRINDO MARRON 179": "CHALLENGER", "2K DTM CATALIZADOR 250 ML": "CHALLENGER", "2K DTM CATALIZADOR LT": "CHALLENGER", "2K DTM FONDO DE RELLENO GL": "CHALLENGER", "2K DTM FONDO DE RELLENO LT": "CHALLENGER", "2K FONDO DE RELLENO CATALIZADOR 250ML": "CHALLENGER", "831-4": "CHALLENGER", "AC-7534-50X": "CHALLENGER", "ADITIVO DOWSIL 11": "CHALLENGER", "ADVANTAGE 357": "CHALLENGER", "AUTOLUX 930 GL": "MULTIMARCA", "AZTK KIT TRANSPARENTE SUPER P500 LT": "MULTIMARCA", "BC BLANCO GL": "CHALLENGER", "BC BLANCO LT": "CHALLENGER", "BC NEGRO DEEP BLACK GL": "CHALLENGER", "BC NEGRO GL": "CHALLENGER", "BC ROJO FERRARI GL": "CHALLENGER", "BORLA DE LANA DOBLE CARA KLINGSPOR": "MULTIMARCA", "C311 HARDENER STANDARD 5:1 945ML": "MULTIMARCA", "C356 ESTANDAR 500 ML": "MULTIMARCA", "CATALIZADOR GLOSS GL": "CHALLENGER", "CATALIZADOR GLOSS LT": "CHALLENGER", "CINTA MASKING 3/4 18MMX 50M 3M": "MULTIMARCA", "CLEAR VOLLER HS ALTO BRILLO (6LTS)": "MULTIMARCA", "CT5 RAPIDO 945ML": "MULTIMARCA", "DELTRON DC2021 KIT": "MULTIMARCA", "DISCO LIJA 120 KLIGSPOR": "MULTIMARCA", "DISCO LIJA 320 KLIGSPOR": "MULTIMARCA", "EASY MASTER 800 CATALIZADOR 200ML": "CHALLENGER", "EASY MASTER 800 LT": "CHALLENGER", "ESMALTE ACRILICO BLANCO GL": "CHALLENGER", "ESMALTE POLIURETANO BLANCO GL": "CHALLENGER", "FINAL MATE TRANSPARENTE LT": "CHALLENGER", "FONDO DE RELLENO 2K GRIS GL": "CHALLENGER", "GLOSS TRANSPARENTE CHALLENGER LT": "CHALLENGER", "KIT 2K DTM GL": "CHALLENGER", "MAXIFILL GL": "MULTIMARCA", "PASTA BODY FILLER R80 3 LT": "CHALLENGER", "PASTA R-50": "CHALLENGER", "SUPER PRIMER 2K 800ML": "CHALLENGER", "THINNER ACRILICO LT": "CHALLENGER", "TRANSPARENTE UNIX 150 HS 5L": "MULTIMARCA", "TRANSPARENTE VT 141 3.78 LT": "MULTIMARCA"
    }

def pct_cliente_especial(cliente_nombre, empresa_cfg, overrides=None):
    n = normalizar_texto(cliente_nombre)
    if overrides is not None:
        for clave, pct in overrides.items():
            if normalizar_texto(clave) in n:
                return pct
    if empresa_cfg.get("reglas_especiales"):
        for clave, pct in CLIENTES_ESPECIALES.items():
            if normalizar_texto(clave) in n:
                return pct
    return None

# ── UTILIDADES ───────────────────────────────────────────────────────────────
def normalizar_texto(texto):
    if not texto: return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(texto))
        if unicodedata.category(c) != 'Mn'
    ).lower().strip()

def _limpiar_nombre(nombre):
    n = (nombre or "").strip()
    if n.startswith("["):
        idx = n.find("]")
        if idx != -1: n = n[idx+1:].strip()
    return n

def es_materia_prima(nombre, almacen=""):
    n = normalizar_texto(nombre)
    a = normalizar_texto(almacen)
    if "materia prima" in a or "mp al" in a:
        return True
    return any(k in n for k in MATERIA_PRIMA_KW)

def es_pasta(nombre):
    return any(k in normalizar_texto(nombre) for k in PASTA_KW)

def clasificar_producto(nombre, almacen=""):
    if es_materia_prima(nombre, almacen):
        return "MATERIA PRIMA"
    if es_pasta(nombre):
        return "PASTA"
    nombre_limpio = _limpiar_nombre(nombre)
    for clave in (nombre_limpio, (nombre or "").strip()):
        if clave in CLASIFICACION_PRODUCTOS:
            return CLASIFICACION_PRODUCTOS[clave]
    nl = normalizar_texto(nombre_limpio)
    for prod, clasif in CLASIFICACION_PRODUCTOS.items():
        if normalizar_texto(prod) == nl:
            return clasif
    return "CHALLENGER"

def fmt_mxn(val):
    try:    return f"${val:,.2f}"
    except: return "$0.00"

def fmt_num(val):
    try:    return f"{val:,.2f}" if isinstance(val, float) and not val.is_integer() else f"{int(val):,}"
    except: return "0"

def almacenes_coinciden(filtro, almacen_real):
    if not filtro or filtro in ("Todos los Almacenes", "TODOS"):
        return True
    return normalizar_texto(filtro) == normalizar_texto(almacen_real)


# ── CONEXIÓN XML-RPC ─────────────────────────────────────────────────────────
def conectar_odoo(company_id=None):
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common", allow_none=True)
    ctx = {"allowed_company_ids": [company_id], "company_id": company_id} if company_id else {}
    uid = None
    for attempt in range(4):
        try:
            uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_API_KEY, ctx)
            if uid:
                break
        except Exception as e_c:
            if "429" in str(e_c) and attempt < 3:
                time.sleep(1.2 * (attempt + 1))
                continue
            raise
    if not uid:
        raise Exception("Credenciales de Odoo incorrectas.")
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object", allow_none=True)
    return uid, models


def obtener_vendedores_odoo(company_id=1, solo_oficiales=True):
    uid, models = conectar_odoo(company_id)
    partners = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        "res.partner", "search_read",
        [[("customer_rank", ">", 0)]],
        {"fields": ["properties"], "limit": 100}
    )
    tags_no_vendedores = {
        'cedis qro', 'cedis', 'sin asignar', 'sin asignacion', 'empleado', 'externo',
        'bmg', 'ventas', 'mirelia cervantes cervantes', 'mirelia', 'rigoberto hernandez zavala',
        'rigoberto', 'administrador', 'admin', 'odoobot', 'alexis ramirez martinez',
        'carolina alvarez suarez', 'david daiko', 'david fernando sanchez hernandez',
        'hugo baldomero medina rivera', 'maria del carmen guerrero rodriguez'
    }
    for p in partners:
        for prop in (p.get("properties") or []):
            if prop.get("name") == PROP_VENDEDOR_KEY:
                raw_sel = prop.get("selection") or []
                res = []
                for v, lbl in raw_sel:
                    lbl_clean = lbl.strip()
                    lbl_norm = normalizar_texto(lbl_clean)
                    if solo_oficiales and lbl_norm in tags_no_vendedores:
                        continue
                    res.append((v, lbl_clean))
                res.sort(key=lambda x: x[1])
                return res
    return []


# ── MOTOR DE CÁLCULO DE COMISIONES ───────────────────────────────────────────
def calcular_comisiones_engine(mes, anio, vendedor_valor, vendedor_nombre, empresa_nombre,
                               overrides_especiales=None, incluir_pbnk=True,
                               excluir_retrasos_45=True, limite_dias=45):
    empresa_cfg = EMPRESAS.get(empresa_nombre, EMPRESAS["BALDOMERO MEDINA GARZA"])
    cid = empresa_cfg["company_id"]
    prefijos_excluir = empresa_cfg["prefijos_excluir"] if not incluir_pbnk else []

    uid, models = conectar_odoo(cid)

    primer_dia = date(anio, mes, 1).strftime("%Y-%m-%d")
    primer_dia_pos = date(anio, mes, 1).strftime("%Y-%m-%d 00:00:00")
    ultimo_dia = date(anio, mes, calendar.monthrange(anio, mes)[1]).strftime("%Y-%m-%d")
    ultimo_dia_pos = date(anio, mes, calendar.monthrange(anio, mes)[1]).strftime("%Y-%m-%d 23:59:59")

    # 1. Detectar configuraciones de Punto de Venta (POS) correspondientes al vendedor / sucursal
    pos_configs = []
    try:
        pos_configs = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'pos.config', 'search_read', [[]],
            {'fields': ['id', 'name', 'picking_type_id']}
        )
    except Exception as e_cfg:
        print(f"[WARN pos.config search]: {e_cfg}")

    CONFIG_SELLER_MAP = {
        '28376856de739e77': ['guadalajara', 'jorge ivan'],
        # Fabián Lizarraga trabaja venta y cobranza directa a clientes (sin terminal POS en tienda)
        'cda2139611d125fc': [],
        'ba56f876fb0681e3': ['tijuana', 'julian garcia'],
        'c2f93a605a94727f': ['camioneta de ivan', 'victor ivan'],
        '7e5e800f6f45f61a': ['monterrey', 'alberto mascorro', 'mascorro'],
        'e5c3209834b07a37': ['estado de mexico', 'hugo ignacio', 'hugo rojas'],
        '17b0d4cf90be6174': ['veracruz', 'miguel escobar'],
        '1a16a0166d84f5ea': ['veracruz', 'jaime rios']
    }

    seller_norm = normalizar_texto(vendedor_nombre)
    matching_config_ids = []
    keywords = CONFIG_SELLER_MAP.get(vendedor_valor, [])
    if keywords:
        for cfg in pos_configs:
            c_name_norm = normalizar_texto(cfg.get('name', ''))
            pt_norm = normalizar_texto(cfg['picking_type_id'][1]) if cfg.get('picking_type_id') else ''
            is_match = False
            for kw in keywords:
                if kw in c_name_norm or kw in pt_norm:
                    is_match = True
                    break
            if is_match:
                matching_config_ids.append(cfg['id'])

    # 2. Consultar órdenes del Punto de Venta (POS)
    pos_orders = []
    pos_invoice_ids = set()
    if matching_config_ids:
        try:
            pos_orders = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'pos.order', 'search_read',
                [[
                    ('config_id', 'in', matching_config_ids),
                    ('date_order', '>=', primer_dia_pos),
                    ('date_order', '<=', ultimo_dia_pos),
                    ('state', 'not in', ['draft', 'cancel'])
                ]],
                {'fields': ['id', 'name', 'pos_reference', 'date_order', 'partner_id', 'amount_total', 'account_move', 'lines', 'payment_ids', 'state']}
            )
            for o in pos_orders:
                if o.get('account_move'):
                    pos_invoice_ids.add(o['account_move'][0])
        except Exception as e_pos:
            print(f"[WARN pos.order search]: {e_pos}")

    # 3. Leer líneas de productos de las órdenes de POS en batch
    all_pos_line_ids = []
    for o in pos_orders:
        all_pos_line_ids.extend(o.get('lines', []))

    pos_lines_by_order = {}
    if all_pos_line_ids:
        try:
            pos_line_records = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'pos.order.line', 'search_read',
                [[('id', 'in', all_pos_line_ids)]],
                {'fields': ['id', 'order_id', 'product_id', 'qty', 'price_unit', 'price_subtotal', 'price_subtotal_incl', 'discount']}
            )
            for l in pos_line_records:
                oid = l['order_id'][0]
                if oid not in pos_lines_by_order:
                    pos_lines_by_order[oid] = []
                pos_lines_by_order[oid].append(l)
        except Exception as e_lines:
            print(f"[WARN pos.order.line]: {e_lines}")

    # 4. Búsqueda directa y rápida de clientes asignados en Odoo
    partner_ids = []
    try:
        partner_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner', 'search',
            [[('properties.' + PROP_VENDEDOR_KEY, '=', vendedor_valor)]]
        )
    except Exception:
        partner_ids, offset, BATCH = [], 0, 200
        while True:
            lote = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                "res.partner", "search_read", [[]],
                {"fields": ["id", "properties"], "limit": BATCH, "offset": offset}
            )
            if not lote: break
            for p in lote:
                for prop in (p.get("properties") or []):
                    if prop.get("name") == PROP_VENDEDOR_KEY:
                        val = prop.get("value")
                        val_str = val[0] if isinstance(val, (list, tuple)) and val else val
                        if val_str == vendedor_valor:
                            partner_ids.append(p["id"])
                        break
            offset += BATCH
            if len(lote) < BATCH: break

    if partner_ids:
        try:
            hijos = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                "res.partner", "search",
                [[("commercial_partner_id", "in", partner_ids)]]
            )
            partner_ids = list(set(partner_ids) | set(hijos))
        except Exception:
            pass

    # 5. Procesar órdenes POS en el detalle de liquidación
    resultados = []
    total_chall = 0.0
    total_multi = 0.0
    total_pasta = 0.0
    total_com = 0.0
    n_excluidos_clientes = 0
    n_excluidos_pfx = 0

    for o in pos_orders:
        partner_tuple = o.get('partner_id')
        p_id_order = partner_tuple[0] if partner_tuple and isinstance(partner_tuple, (list, tuple)) else None
        if partner_ids and (not p_id_order or p_id_order not in partner_ids):
            continue
        cliente_nom = partner_tuple[1] if partner_tuple else 'Cliente Mostrador'
        c_norm = normalizar_texto(cliente_nom)
        if any(ex in c_norm for ex in CLIENTES_INTEREMPRESA_EXCLUIDOS):
            n_excluidos_clientes += 1
            continue

        tot_order = float(o.get('amount_total', 0.0) or 0.0)
        f_order_str = str(o.get('date_order', primer_dia))[:10]

        pct_esp = pct_cliente_especial(cliente_nom, empresa_cfg, overrides_especiales)

        m_chall = m_multi = m_pasta = 0.0
        lines_desglosadas = []
        productos_detalle = []

        for l in pos_lines_by_order.get(o['id'], []):
            prod_nom = l['product_id'][1] if l.get('product_id') else 'Producto'
            sub = float(l.get('price_subtotal') or 0.0)
            cat = clasificar_producto(prod_nom)
            if cat == 'PASTA':
                m_pasta += sub
                tasa = COMISION_PASTA
                productos_detalle.append(f"[2.5%] {prod_nom} ({fmt_mxn(sub)})")
            elif cat == 'MULTIMARCA':
                m_multi += sub
                tasa = pct_esp if pct_esp is not None else COMISION_MULTIMARCA
                t_lbl = (pct_esp * 100) if pct_esp is not None else 9.0
                productos_detalle.append(f"[{t_lbl:.0f}%] {prod_nom} ({fmt_mxn(sub)})")
            else:
                m_chall += sub
                tasa = pct_esp if pct_esp is not None else COMISION_CHALLENGER
                t_lbl = (pct_esp * 100) if pct_esp is not None else 9.0
                productos_detalle.append(f"[{t_lbl:.0f}%] {prod_nom} ({fmt_mxn(sub)})")

            lines_desglosadas.append({
                'producto': prod_nom,
                'subtotal': sub,
                'categoria': cat,
                'tasa': tasa * 100,
                'monto_comision': sub * tasa
            })

        order_subtotal = m_chall + m_multi + m_pasta
        if order_subtotal > 0:
            prop_c = m_chall / order_subtotal
            prop_m = m_multi / order_subtotal
            prop_p = m_pasta / order_subtotal
        else:
            prop_c, prop_m, prop_p = 1.0, 0.0, 0.0

        cob_c = tot_order * prop_c
        cob_m = tot_order * prop_m
        cob_p = tot_order * prop_p

        if pct_esp is not None:
            com = (cob_c + cob_m) * pct_esp + cob_p * COMISION_PASTA
        else:
            com = cob_c * COMISION_CHALLENGER + cob_m * COMISION_MULTIMARCA + cob_p * COMISION_PASTA

        total_chall += cob_c
        total_multi += cob_m
        total_pasta += cob_p
        total_com += com

        inv_nom = o['account_move'][1] if o.get('account_move') else o.get('name', '')
        if '(' in inv_nom:
            inv_nom = inv_nom.split('(')[0].strip()

        resultados.append({
            "fecha": f_order_str,
            "fecha_venc": f_order_str,
            "cliente": cliente_nom,
            "factura": inv_nom,
            "num_pago": o.get('pos_reference') or o.get('name'),
            "dias_retraso": 0,
            "en_tiempo": True,
            "cobrado": tot_order,
            "base_challenger": cob_c,
            "base_multi": cob_m + cob_p,
            "base_pasta": cob_p,
            "comision": com,
            "comision_original": com,
            "productos_detalle": productos_detalle,
            "lineas_detalle": lines_desglosadas,
            "pct_especial": pct_esp,
            "cuenta": True,
            "tasa_aplicada": (pct_esp * 100) if pct_esp is not None else 9.0,
            "origen": "Punto de Venta"
        })

    # 6. Consultar pagos del cliente (account.payment)
    pagos_raw = []
    try:
        pay_domain = [
            ("payment_type", "in", ["inbound", "outbound"]),
            ("date", ">=", primer_dia),
            ("date", "<=", ultimo_dia)
        ]
        if cid is not None:
            pay_domain.append(("company_id", "=", cid))

        if partner_ids:
            pay_domain.extend([
                "|",
                ("partner_id", "in", partner_ids),
                ("partner_id.properties." + PROP_VENDEDOR_KEY, "=", vendedor_valor)
            ])
        else:
            pay_domain.append(("partner_id.properties." + PROP_VENDEDOR_KEY, "=", vendedor_valor))

        pagos_raw = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            "account.payment", "search_read",
            [pay_domain],
            {"fields": ["id", "name", "date", "amount",
                        "amount_company_currency_signed", "amount_signed",
                        "partner_id", "payment_type", "state", "reconciled_invoice_ids"],
             "order": "date asc"}
        )
    except Exception as e_pay:
        print(f"[WARN account.payment search]: {e_pay}")

    if prefijos_excluir:
        filtrados = []
        for p in pagos_raw:
            nm = p.get("name") or ""
            if any(nm.startswith(pfx) for pfx in prefijos_excluir):
                n_excluidos_pfx += 1
            else:
                filtrados.append(p)
        pagos_raw = filtrados

    # Preservar cada pago por su ID único en Odoo (no descartar folios repetidos que son pagos distintos)
    pagos_dict = {}
    for p in pagos_raw:
        pagos_dict[p["id"]] = p
    pagos = list(pagos_dict.values())

    # Batch-fetch facturas y líneas de pagos tradicionales en 1 sola consulta
    all_fac_ids = []
    for pago in pagos:
        rec_invs = pago.get("reconciled_invoice_ids", [])
        if rec_invs and all(inv_id in pos_invoice_ids for inv_id in rec_invs):
            continue
        all_fac_ids.extend(rec_invs)
    all_fac_ids = list(set(all_fac_ids))

    facturas_map = {}
    lines_map = {}
    if all_fac_ids:
        try:
            CHUNK_F = 300
            for i in range(0, len(all_fac_ids), CHUNK_F):
                f_chunk = all_fac_ids[i:i+CHUNK_F]
                fac_records = models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    "account.move", "read", [f_chunk],
                    {"fields": ["id", "name", "invoice_date", "invoice_date_due", "invoice_line_ids"]}
                )
                all_line_ids = []
                for f in fac_records:
                    facturas_map[f["id"]] = f
                    all_line_ids.extend(f.get("invoice_line_ids") or [])

                if all_line_ids:
                    CHUNK_L = 300
                    for j in range(0, len(all_line_ids), CHUNK_L):
                        l_chunk = all_line_ids[j:j+CHUNK_L]
                        line_records = models.execute_kw(
                            ODOO_DB, uid, ODOO_API_KEY,
                            "account.move.line", "read", [l_chunk],
                            {"fields": ["id", "move_id", "display_type", "product_id", "name", "price_subtotal"]}
                        )
                        for l in line_records:
                            m_val = l.get("move_id")
                            m_id = m_val[0] if isinstance(m_val, (list, tuple)) else m_val
                            if m_id not in lines_map:
                                lines_map[m_id] = []
                            lines_map[m_id].append(l)
        except Exception as e_batch:
            print(f"[WARN batch invoices]: {e_batch}")

    for pago in pagos:
        rec_invs = pago.get("reconciled_invoice_ids", [])
        # Desduplicación inteligente: si las facturas ya fueron incluidas en el POS, evitar duplicar
        if rec_invs and all(inv_id in pos_invoice_ids for inv_id in rec_invs):
            continue

        cliente = (pago["partner_id"] or [None, ""])[1]
        cliente_norm = normalizar_texto(cliente)

        if any(c_ex in cliente_norm for c_ex in CLIENTES_INTEREMPRESA_EXCLUIDOS):
            n_excluidos_clientes += 1
            continue

        is_outbound = pago.get("payment_type") == "outbound"
        is_canceled = pago.get("state") in ["cancel", "canceled"]
        raw_val = abs(pago.get("amount_company_currency_signed") or
                      pago.get("amount_signed") or pago.get("amount", 0))
        cobrado = -raw_val if is_outbound else raw_val
        fecha_pago = pago["date"]
        fac_ids    = pago.get("reconciled_invoice_ids", [])
        nombre     = pago.get("name") or str(pago.get("id"))

        pct_esp = pct_cliente_especial(cliente, empresa_cfg, overrides_especiales)

        if not fac_ids:
            pct = pct_esp if pct_esp is not None else COMISION_MULTIMARCA
            com = cobrado * pct if not is_canceled else 0.0
            cuenta = not is_canceled
            if cuenta:
                total_multi += cobrado
                total_com += com
            resultados.append({
                "fecha": fecha_pago, "fecha_venc": "—", "cliente": cliente, "factura": "(sin factura)",
                "num_pago": nombre, "dias_retraso": 0, "en_tiempo": True,
                "cobrado": cobrado, "base_challenger": 0.0, "base_multi": cobrado,
                "base_pasta": 0.0, "comision": com, "productos_detalle": [],
                "lineas_detalle": [{
                    "producto": "(Pago global directo sin desglosar)",
                    "subtotal": cobrado,
                    "categoria": "MULTIMARCA",
                    "tasa": pct * 100,
                    "monto_comision": com
                }],
                "pct_especial": pct_esp,
                "cuenta": cuenta, "cancelado": is_canceled, "tasa_aplicada": pct * 100
            })
            continue

        facturas = [facturas_map[fid] for fid in fac_ids if fid in facturas_map]

        monto_chall = monto_multi = monto_pasta = 0.0
        nombres_fac, productos_detalle = [], []
        fecha_venc_max = None

        for fac in facturas:
            nombres_fac.append(fac.get("name", ""))
            fv = fac.get("invoice_date_due") or fac.get("invoice_date")
            if fv:
                try:
                    d = datetime.strptime(str(fv)[:10], "%Y-%m-%d").date()
                    if fecha_venc_max is None or d > fecha_venc_max: fecha_venc_max = d
                except Exception:
                    pass
            lineas = lines_map.get(fac["id"], [])
            lineas_desglosadas = []
            for l in lineas:
                if l.get("display_type") in ("line_section", "line_note"): continue
                sub = float(l.get("price_subtotal") or 0.0)
                nprod = (l.get("product_id") or [False, ""])[1] or l.get("name", "")
                cat = clasificar_producto(nprod)
                if cat == "PASTA":
                    monto_pasta += sub
                    tasa = COMISION_PASTA
                    productos_detalle.append(f"[2.5%] {nprod} ({fmt_mxn(sub)})")
                elif cat == "MULTIMARCA":
                    monto_multi += sub
                    tasa = pct_esp if pct_esp is not None else COMISION_MULTIMARCA
                    t_lbl = (pct_esp * 100) if pct_esp is not None else 9.0
                    productos_detalle.append(f"[{t_lbl:.0f}%] {nprod} ({fmt_mxn(sub)})")
                else:
                    monto_chall += sub
                    tasa = pct_esp if pct_esp is not None else COMISION_CHALLENGER
                    t_lbl = (pct_esp * 100) if pct_esp is not None else 9.0
                    productos_detalle.append(f"[{t_lbl:.0f}%] {nprod} ({fmt_mxn(sub)})")
                
                lineas_desglosadas.append({
                    "producto": nprod,
                    "subtotal": sub,
                    "categoria": cat,
                    "tasa": tasa * 100,
                    "monto_comision": sub * tasa
                })

        dias_retraso = 0
        en_tiempo = True
        if fecha_venc_max:
            fp = datetime.strptime(fecha_pago, "%Y-%m-%d").date()
            diff = (fp - fecha_venc_max).days
            en_tiempo = diff <= 0
            dias_retraso = 0 if diff <= 0 else diff

        tp = monto_chall + monto_multi + monto_pasta
        prop_c = (monto_chall / tp) if tp else 0.0
        prop_m = (monto_multi / tp) if tp else 0.0
        prop_p = (monto_pasta / tp) if tp else 1.0

        cob_c = cobrado * prop_c
        cob_m = cobrado * prop_m
        cob_p = cobrado * prop_p

        if pct_esp is not None:
            com = (cob_c + cob_m) * pct_esp + cob_p * COMISION_PASTA
        else:
            com = cob_c * COMISION_CHALLENGER + cob_m * COMISION_MULTIMARCA + cob_p * COMISION_PASTA

        cuenta = not is_canceled
        if is_canceled:
            com_efectiva = 0.0
        elif excluir_retrasos_45 and not en_tiempo and dias_retraso > limite_dias:
            cuenta = False
            com_efectiva = 0.0
        else:
            com_efectiva = com

        if cuenta:
            total_chall += cob_c
            total_multi += cob_m + cob_p
            total_com += com_efectiva

        resultados.append({
            "fecha": fecha_pago,
            "fecha_venc": str(fecha_venc_max) if fecha_venc_max else "—",
            "cliente": cliente,
            "factura": ", ".join(nombres_fac) if nombres_fac else "(sin factura)",
            "num_pago": nombre,
            "dias_retraso": dias_retraso,
            "en_tiempo": en_tiempo,
            "cobrado": cobrado,
            "base_challenger": cob_c,
            "base_multi": cob_m + cob_p,
            "base_pasta": cob_p,
            "comision": com_efectiva,
            "comision_original": com,
            "productos_detalle": productos_detalle,
            "lineas_detalle": lineas_desglosadas,
            "pct_especial": pct_esp,
            "cuenta": cuenta,
            "cancelado": is_canceled,
            "tasa_aplicada": (pct_esp * 100) if pct_esp is not None else 9.0
        })

    # Ordenar por fecha descendente
    resultados.sort(key=lambda r: r["fecha"], reverse=True)

    return {
        "detalle": resultados,
        "totales": {
            "cobrado": round(sum(r["cobrado"] for r in resultados if r["cuenta"]), 2),
            "cobrado_total": round(sum(r["cobrado"] for r in resultados), 2),
            "comision": round(total_com, 2),
            "challenger": round(total_chall, 2),
            "multi": round(total_multi, 2)
        },
        "n_clientes": len(set(r["cliente"] for r in resultados)),
        "n_excluidos_pfx": n_excluidos_pfx,
        "n_excluidos_clientes": n_excluidos_clientes
    }


# ── MOTOR DE PRODUCTOS MÁS VENDIDOS ──────────────────────────────────────────
def obtener_mapa_kits_odoo(models, uid):
    try:
        boms = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'mrp.bom', 'search_read',
            [[('type', '=', 'phantom')]],
            {'fields': ['product_tmpl_id', 'bom_line_ids']}
        )
        kit_map = {}
        for b in boms:
            tmpl = b.get('product_tmpl_id')
            if not tmpl: continue
            kit_nom = _limpiar_nombre(tmpl[1])
            b_lines = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'mrp.bom.line', 'search_read',
                [[('id', 'in', b.get('bom_line_ids', []))]],
                {'fields': ['product_id']}
            )
            for bl in b_lines:
                p_tuple = bl.get('product_id')
                if p_tuple:
                    comp_name = _limpiar_nombre(p_tuple[1])
                    kit_map[comp_name] = kit_nom
        if kit_map: return kit_map
    except Exception:
        pass
    return {
        "GLOSS TRANSPARENTE CHALLENGER LT": "KIT GLOSS LT",
        "GLOSS REDUCTOR LT": "KIT GLOSS LT",
        "CATALIZADOR GLOSS 250ML": "KIT GLOSS LT",
        "GLOSS TRANSPARENTE GL": "KIT GLOSS GL",
        "REDUCTOR GLOSS GL": "KIT GLOSS GL",
        "CATALIZADOR GLOSS LT": "KIT GLOSS GL",
        "TPP-5000 TRANSPARENTE LT 4-1-4": "KIT TPP 5000 LT",
        "TPP-5000 250 ML CATALIZADOR 4-1-4": "KIT TPP 5000 LT",
        "TPP-5000 GL": "KIT DE TPP DE GL",
        "TPP-5000 CATALIZADOR LT": "KIT DE TPP DE GL",
        "FONDO DE RELLENO 2K GRIS LT": "Kit 2k Gris Lt",
        "2K FONDO DE RELLENO CATALIZADOR 250ML": "Kit 2k Gris Lt",
        "FONDO DE RELLENO 2K GRIS GL": "Kit 2k Gris GL",
        "CATALIZADOR FONDO DE RELLENO 2K 1LT": "Kit 2k Gris GL",
        "SUPER PRIMER 2K 800ML": "Kit Super Primer 2k",
        "CATALIZADOR SUPER PRIMER 2K 200ML": "Kit Super Primer 2k",
        "EASY MASTER 800 LT": "KIT EASY MASTER 800",
        "EASY MASTER 800 CATALIZADOR 200ML": "KIT EASY MASTER 800",
        "2K DTM FONDO DE RELLENO LT": "KIT 2K DTM LT",
        "2K DTM CATALIZADOR 250 ML": "KIT 2K DTM LT",
        "2K DTM FONDO DE RELLENO GL": "KIT 2K DTM GL",
        "2K DTM CATALIZADOR LT": "KIT 2K DTM GL"
    }


def obtener_productos_engine(fecha_inicio, fecha_fin, empresa_nombre="TODAS (Consolidado)", excluir_interempresa=True):
    empresa_cfg = EMPRESAS.get(empresa_nombre)
    cid = empresa_cfg["company_id"] if empresa_cfg else None
    prefijos_excluir = empresa_cfg["prefijos_excluir"] if empresa_cfg else []

    uid, models = conectar_odoo(cid or 1)
    kit_map = obtener_mapa_kits_odoo(models, uid)

    domain = [
        ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
        ("move_id.state", "=", "posted"),
        ("display_type", "=", "product"),
        ("date", ">=", fecha_inicio),
        ("date", "<=", fecha_fin),
    ]
    if cid:
        domain.append(("company_id", "=", cid))

    fields = [
        "id", "product_id", "name", "quantity", "price_unit", "price_subtotal",
        "move_id", "date", "partner_id", "product_uom_id", "company_id"
    ]

    lineas_raw = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        "account.move.line", "search_read", [domain],
        {"fields": fields, "limit": 10000}
    )

    if not lineas_raw:
        return {
            "productos": [],
            "totales": {
                "monto": 0, "monto_bruto": 0, "monto_nc": 0, "monto_neto": 0,
                "cantidad": 0, "cantidad_bruta": 0, "cantidad_devuelta": 0, "cantidad_neta": 0,
                "facturas": 0, "ncs": 0, "variedad": 0
            },
            "lineas": [],
            "n_excluidos_clientes": 0
        }

    move_ids = list(set([l["move_id"][0] for l in lineas_raw if l.get("move_id")]))
    moves_raw = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY, "account.move", "search_read",
        [[("id", "in", move_ids)]],
        {"fields": ["id", "name", "move_type", "invoice_user_id", "partner_id", "company_id", "date", "invoice_date"]}
    )
    move_map = {m["id"]: m for m in moves_raw}

    CONCEPTOS_AJUSTES = {"DEVOLUCION DE MATERIAL", "DESCUENTO", "AJUSTE", "ANTICIPO", "REDONDEO"}

    productos_dict = {}
    facturas_unicas = set()
    ncs_unicas = set()
    lineas_detalle = []

    monto_bruto = 0.0
    monto_nc = 0.0
    cantidad_bruta = 0.0
    cantidad_devuelta = 0.0
    n_excluidos_clientes = 0

    for lin in lineas_raw:
        mid = lin.get("move_id")[0] if lin.get("move_id") else None
        mv = move_map.get(mid, {})
        mname = mv.get("name") or (lin.get("move_id")[1] if lin.get("move_id") else "")
        mtype = mv.get("move_type", "out_invoice")
        is_nc = (mtype == "out_refund")

        if prefijos_excluir and any(mname.startswith(pfx) for pfx in prefijos_excluir):
            continue

        partner_name = (lin.get("partner_id") or mv.get("partner_id") or [None, "Sin Cliente"])[1]
        partner_norm = normalizar_texto(partner_name)

        if excluir_interempresa and any(c_ex in partner_norm for c_ex in CLIENTES_INTEREMPRESA_EXCLUIDOS):
            n_excluidos_clientes += 1
            continue

        prod_info = lin.get("product_id")
        if not prod_info:
            continue

        vendedor_name = (mv.get("invoice_user_id") or [None, "Venta Directa / Sin Asignar"])[1]
        empresa_lin = (lin.get("company_id") or mv.get("company_id") or [None, "Empresa"])[1]
        fecha_lin = lin.get("date") or mv.get("invoice_date") or ""

        raw_pname = prod_info[1] if len(prod_info) > 1 else (lin.get("name") or "Producto Desconocido")
        nombre_limpio = _limpiar_nombre(raw_pname)
        nombre_canonico = kit_map.get(nombre_limpio, nombre_limpio)
        clave_prod = normalizar_texto(nombre_canonico)

        cant = float(lin.get("quantity", 0.0) or 0)
        subtotal = float(lin.get("price_subtotal", 0.0) or 0)
        precio_u = float(lin.get("price_unit", 0.0) or 0)
        uom_name = (lin.get("product_uom_id") or [None, "Pza"])[1]

        # Unificación de Kits y Lista de Materiales
        es_componente = nombre_limpio in kit_map
        if es_componente and (precio_u < 1.0 or subtotal < 1.0):
            cant_efectiva = 0.0
        else:
            cant_efectiva = cant

        is_concept_adj = any(adj in nombre_canonico.upper() for adj in CONCEPTOS_AJUSTES)
        clasif = clasificar_producto(nombre_canonico)

        if is_nc:
            ncs_unicas.add(mname)
            monto_nc += subtotal
            cantidad_devuelta += cant_efectiva
            subtotal_signed = -subtotal
            cant_signed = -cant_efectiva
        else:
            facturas_unicas.add(mname)
            monto_bruto += subtotal
            cantidad_bruta += cant_efectiva
            subtotal_signed = subtotal
            cant_signed = cant_efectiva

        if clave_prod not in productos_dict:
            productos_dict[clave_prod] = {
                "id": prod_info[0],
                "nombre": nombre_canonico,
                "nombre_limpio": nombre_canonico,
                "clasificacion": clasif,
                "es_ajuste": is_concept_adj,
                "cantidad_bruta": 0.0,
                "subtotal_bruto": 0.0,
                "cantidad_devuelta": 0.0,
                "subtotal_nc": 0.0,
                "subtotal_neto": 0.0,
                "cantidad_neta": 0.0,
                "precios": [],
                "facturas": set(),
                "ncs": set(),
                "clientes_map": {},
                "vendedores_map": {},
                "lineas": [],
                "uom": uom_name
            }

        pdata = productos_dict[clave_prod]
        if is_nc:
            pdata["cantidad_devuelta"] += cant_efectiva
            pdata["subtotal_nc"] += subtotal
            pdata["ncs"].add(mname)
        else:
            pdata["cantidad_bruta"] += cant_efectiva
            pdata["subtotal_bruto"] += subtotal
            pdata["facturas"].add(mname)
            if precio_u >= 1.0:
                pdata["precios"].append(precio_u)

        pdata["subtotal_neto"] += subtotal_signed
        pdata["cantidad_neta"] += cant_signed

        # Client breakdown
        if partner_name not in pdata["clientes_map"]:
            pdata["clientes_map"][partner_name] = {"cliente": partner_name, "cantidad": 0.0, "subtotal": 0.0, "facturas": set()}
        pdata["clientes_map"][partner_name]["cantidad"] += cant_signed
        pdata["clientes_map"][partner_name]["subtotal"] += subtotal_signed
        pdata["clientes_map"][partner_name]["facturas"].add(mname)

        # Seller breakdown
        if vendedor_name not in pdata["vendedores_map"]:
            pdata["vendedores_map"][vendedor_name] = {"vendedor": vendedor_name, "cantidad": 0.0, "subtotal": 0.0, "facturas": set()}
        pdata["vendedores_map"][vendedor_name]["cantidad"] += cant_signed
        pdata["vendedores_map"][vendedor_name]["subtotal"] += subtotal_signed
        pdata["vendedores_map"][vendedor_name]["facturas"].add(mname)

        # Individual line
        line_item = {
            "fecha": fecha_lin,
            "factura": mname,
            "tipo_doc": "Nota de Crédito" if is_nc else "Factura",
            "es_nc": is_nc,
            "cliente": partner_name,
            "vendedor": vendedor_name,
            "empresa": empresa_lin,
            "cantidad": cant_efectiva,
            "precio_unitario": precio_u,
            "subtotal": subtotal_signed,
            "uom": uom_name
        }
        pdata["lineas"].append(line_item)
        lineas_detalle.append(line_item)

    monto_neto = monto_bruto - monto_nc
    cantidad_neta = cantidad_bruta - cantidad_devuelta

    lista_productos = []
    for clave_prod, data in productos_dict.items():
        precios = data["precios"]
        precio_prom = (sum(precios) / len(precios)) if precios else 0.0
        pct_monto = (data["subtotal_bruto"] / monto_bruto * 100) if monto_bruto > 0 else 0.0

        clientes_lista = sorted(
            [{"cliente": k, "cantidad": v["cantidad"], "subtotal": v["subtotal"], "num_facturas": len(v["facturas"])} for k, v in data["clientes_map"].items()],
            key=lambda x: x["subtotal"], reverse=True
        )
        vendedores_lista = sorted(
            [{"vendedor": k, "cantidad": v["cantidad"], "subtotal": v["subtotal"], "num_facturas": len(v["facturas"])} for k, v in data["vendedores_map"].items()],
            key=lambda x: x["subtotal"], reverse=True
        )

        lista_productos.append({
            "id": data["id"],
            "nombre": data["nombre"],
            "nombre_limpio": data["nombre_limpio"],
            "clasificacion": data["clasificacion"],
            "es_ajuste": data["es_ajuste"],
            "cantidad": data["cantidad_bruta"],
            "cantidad_devuelta": data["cantidad_devuelta"],
            "cantidad_neta": data["cantidad_neta"],
            "subtotal": data["subtotal_bruto"],
            "subtotal_nc": data["subtotal_nc"],
            "subtotal_neto": data["subtotal_neto"],
            "precio_promedio": precio_prom,
            "num_facturas": len(data["facturas"]),
            "num_ncs": len(data["ncs"]),
            "num_clientes": len(data["clientes_map"]),
            "num_vendedores": len(data["vendedores_map"]),
            "clientes": clientes_lista,
            "vendedores": vendedores_lista,
            "lineas": sorted(data["lineas"], key=lambda x: x["fecha"], reverse=True),
            "uom": data["uom"],
            "pct_monto": pct_monto
        })

    productos_catalogo = [p for p in lista_productos if not p["es_ajuste"]]
    ajustes_lista = [p for p in lista_productos if p["es_ajuste"]]

    productos_catalogo.sort(key=lambda x: x["subtotal"], reverse=True)
    for i, p in enumerate(productos_catalogo, 1):
        p["posicion"] = i

    for i, p in enumerate(ajustes_lista, len(productos_catalogo) + 1):
        p["posicion"] = i

    productos_final = productos_catalogo + ajustes_lista

    return {
        "productos": productos_final,
        "totales": {
            "monto": monto_bruto,
            "monto_bruto": monto_bruto,
            "monto_nc": monto_nc,
            "monto_neto": monto_neto,
            "cantidad": cantidad_bruta,
            "cantidad_bruta": cantidad_bruta,
            "cantidad_devuelta": cantidad_devuelta,
            "cantidad_neta": cantidad_neta,
            "facturas": len(facturas_unicas),
            "ncs": len(ncs_unicas),
            "variedad": len(productos_catalogo)
        },
        "lineas": lineas_detalle,
        "n_excluidos_clientes": n_excluidos_clientes
    }


# ── MOTOR DE MONITOR DE ALMACENES Y STOCK ────────────────────────────────────
def obtener_stock_engine(company_id=None, almacen_filtro="Todos los Almacenes", dias_analisis=30, excluir_interempresa=True):
    uid, models = conectar_odoo(company_id)

    warehouses_raw = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        "stock.warehouse", "search_read", [[]],
        {"fields": ["id", "name", "code", "company_id", "lot_stock_id", "view_location_id"]}
    )
    wh_names_set = set(w["name"] for w in warehouses_raw)

    locations_raw = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        "stock.location", "search_read",
        [[("usage", "=", "internal")]],
        {"fields": ["id", "name", "complete_name", "location_id"]}
    )

    # Mapeo exacto de Localización a Almacén
    loc_to_wh = {}
    for loc in locations_raw:
        loc_id = loc["id"]
        cname = loc["complete_name"]
        matched_wh = cname.split("/")[0]

        for w in warehouses_raw:
            w_name = w["name"]
            lot_info = w.get("lot_stock_id")
            view_info = w.get("view_location_id")
            if (lot_info and lot_info[0] == loc_id) or (view_info and view_info[0] == loc_id):
                matched_wh = w_name; break
            if view_info and (cname == view_info[1] or cname.startswith(view_info[1] + "/")):
                matched_wh = w_name; break
            if lot_info and (cname == lot_info[1] or cname.startswith(lot_info[1].split("/")[0] + "/")):
                matched_wh = w_name; break

        loc_to_wh[loc_id] = matched_wh

    quant_domain = [("location_id.usage", "=", "internal")]
    if company_id: quant_domain.append(("company_id", "=", company_id))

    quants_raw = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        "stock.quant", "search_read",
        [quant_domain],
        {"fields": ["id", "product_id", "location_id", "quantity", "reserved_quantity", "company_id"], "limit": 15000}
    )

    # Consulta oficial de Precios de Venta de Catálogo en Odoo (product.product list_price)
    product_ids_all = list(set(q["product_id"][0] for q in quants_raw if q.get("product_id")))
    precios_catalogo = {}
    if product_ids_all:
        products_info_raw = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            "product.product", "search_read",
            [[("id", "in", product_ids_all)]],
            {"fields": ["id", "name", "default_code", "list_price", "standard_price"], "limit": 15000}
        )
        for p in products_info_raw:
            lp = float(p.get("list_price", 0.0) or 0.0)
            precios_catalogo[p["id"]] = {
                "precio_venta_base": round(lp, 2),
                "precio_venta_iva": round(lp * 1.16, 2), # PRECIO DE VENTA MÁS IVA (16%)
                "costo": float(p.get("standard_price", 0.0) or 0.0)
            }

    fecha_fin_dt = date.today()
    fecha_ini_dt = fecha_fin_dt - timedelta(days=dias_analisis)

    move_domain = [
        ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
        ("move_id.state", "=", "posted"),
        ("display_type", "=", "product"),
        ("date", ">=", fecha_ini_dt.strftime("%Y-%m-%d")),
        ("date", "<=", fecha_fin_dt.strftime("%Y-%m-%d")),
    ]
    if company_id: move_domain.append(("company_id", "=", company_id))

    ventas_raw = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        "account.move.line", "search_read",
        [move_domain],
        {"fields": ["product_id", "quantity", "price_subtotal", "partner_id"], "limit": 15000}
    )

    ventas_por_producto = {}
    n_excluidos_clientes = 0
    for v in ventas_raw:
        partner_name = (v.get("partner_id") or [None, ""])[1]
        if excluir_interempresa and any(c_ex in normalizar_texto(partner_name) for c_ex in CLIENTES_INTEREMPRESA_EXCLUIDOS):
            n_excluidos_clientes += 1; continue
        prod_info = v.get("product_id")
        if not prod_info: continue
        pid = prod_info[0]
        if pid not in ventas_por_producto: ventas_por_producto[pid] = {"cantidad": 0.0, "subtotal": 0.0}
        ventas_por_producto[pid]["cantidad"] += v.get("quantity", 0.0)
        ventas_por_producto[pid]["subtotal"] += v.get("price_subtotal", 0.0)

    items_dict = {}
    for q in quants_raw:
        prod_info = q.get("product_id")
        if not prod_info: continue
        pid = prod_info[0]
        pname = prod_info[1]
        loc_id = q["location_id"][0]
        wh_nombre = loc_to_wh.get(loc_id, q["location_id"][1])

        if almacen_filtro and almacen_filtro != "Todos los Almacenes":
            if not almacenes_coinciden(almacen_filtro, wh_nombre):
                continue

        qty = q.get("quantity", 0.0)
        res = q.get("reserved_quantity", 0.0)
        key = (pid, wh_nombre)

        if key not in items_dict:
            clasif = clasificar_producto(pname, wh_nombre)
            items_dict[key] = {
                "product_id": pid, "producto": pname, "nombre_limpio": _limpiar_nombre(pname),
                "almacen": wh_nombre, "clasificacion": clasif,
                "stock_actual": 0.0, "reserved": 0.0
            }
        items_dict[key]["stock_actual"] += qty
        items_dict[key]["reserved"] += res

    lista_inventario = []
    tot_a_la_mano = 0.0
    tot_disp = 0.0
    tot_valor = 0.0
    tot_ventas = 0.0
    tot_ventas_mes = 0.0
    tot_sugerido_pedir = 0.0
    tot_inversion_reorden = 0.0
    n_reordenar = 0
    n_agotados = 0
    n_optimo = 0
    n_sobrestock = 0
    n_sin_movimiento = 0

    # Agrupador para resumen por almacén
    resumen_almacenes_map = {}

    for (pid, wh_nombre), data in items_dict.items():
        st_act = data["stock_actual"] # A la mano (Odoo on-hand physical quantity)
        st_res = data["reserved"]
        st_disp = max(0.0, st_act - st_res) if st_act >= st_res else (st_act - st_res)

        v_data = ventas_por_producto.get(pid, {"cantidad": 0.0, "subtotal": 0.0})
        v_periodo = float(v_data["cantidad"])
        v_subtotal = float(v_data["subtotal"])
        v_diaria = v_periodo / max(1, dias_analisis)

        # ── CÁLCULO DE ESTIMACIÓN MENSUAL Y PUNTOS DE REORDEN ──────────────
        # 1. Venta Promedio Mensual (Run-Rate de 30 días)
        venta_mensual_est = round(v_diaria * 30.0, 2)

        # 2. Stock Mínimo de Seguridad (15 días de venta)
        if v_diaria > 0:
            stock_minimo = max(1, math.ceil(v_diaria * 15.0))
            stock_sugerido_mes = max(1, math.ceil(v_diaria * 30.0)) # Meta 1 Mes
            stock_maximo = max(2, math.ceil(v_diaria * 60.0))       # Meta 2 Meses
        else:
            stock_minimo = 0
            stock_sugerido_mes = 0
            stock_maximo = 50

        # 3. Sugerido a Pedir / Reabastecer basado en stock A LA MANO
        if stock_sugerido_mes > 0 and st_act < stock_sugerido_mes:
            sugerido_pedir = float(math.ceil(stock_sugerido_mes - st_act))
        else:
            sugerido_pedir = 0.0

        # 4. Días de Cobertura / Autonomía basado en stock A LA MANO
        dias_cobertura = (st_act / v_diaria) if v_diaria > 0 else 999.0

        # 5. Estado Inteligente del Inventario basado en stock A LA MANO
        if st_act <= 0:
            estado = "AGOTADO"
            n_agotados += 1
        elif st_act < stock_minimo or dias_cobertura <= 15:
            estado = "REORDENAR"
            n_reordenar += 1
        elif v_periodo == 0 and st_act > 50:
            estado = "SOBRESTOCK"
            n_sobrestock += 1
        elif st_act > stock_maximo and st_act > 50 and v_periodo > 0:
            estado = "SOBRESTOCK"
            n_sobrestock += 1
        elif v_periodo == 0:
            estado = "SIN_MOVIMIENTO"
            n_sin_movimiento += 1
        else:
            estado = "OPTIMO"
            n_optimo += 1

        prod_pinfo = precios_catalogo.get(pid, {})
        precio_venta_base = prod_pinfo.get("precio_venta_base", 0.0)
        precio_venta_con_iva = prod_pinfo.get("precio_venta_iva", 0.0)

        # Si el list_price fuera 0, como respaldo usamos el subtotal/cantidad con IVA 16%
        if precio_venta_con_iva <= 0 and v_periodo > 0:
            precio_venta_con_iva = round((v_subtotal / v_periodo) * 1.16, 2)
            precio_venta_base = round(v_subtotal / v_periodo, 2)

        precio_est = precio_venta_con_iva # PRECIO DE VENTA MÁS IVA (16%)
        valor_est = round(st_act * precio_est, 2)
        inversion_reorden = round(sugerido_pedir * precio_est, 2)

        tot_a_la_mano += st_act
        tot_disp += st_disp
        tot_valor += valor_est
        tot_ventas += v_periodo
        tot_ventas_mes += venta_mensual_est
        tot_sugerido_pedir += sugerido_pedir
        tot_inversion_reorden += inversion_reorden

        # Acumular en resumen del almacén
        if wh_nombre not in resumen_almacenes_map:
            resumen_almacenes_map[wh_nombre] = {
                "almacen": wh_nombre, "a_la_mano": 0.0, "disponible": 0.0, "valor": 0.0,
                "ventas_mes": 0.0, "sugerido_pedir": 0.0, "inversion_reorden": 0.0,
                "num_agotados": 0, "num_reordenar": 0, "num_productos": 0
            }
        r_wh = resumen_almacenes_map[wh_nombre]
        r_wh["a_la_mano"] += st_act
        r_wh["disponible"] += st_disp
        r_wh["valor"] += valor_est
        r_wh["ventas_mes"] += venta_mensual_est
        r_wh["sugerido_pedir"] += sugerido_pedir
        r_wh["inversion_reorden"] += inversion_reorden
        r_wh["num_productos"] += 1
        if estado == "AGOTADO": r_wh["num_agotados"] += 1
        if estado == "REORDENAR": r_wh["num_reordenar"] += 1

        lista_inventario.append({
            "product_id": pid,
            "producto": data["producto"],
            "nombre_limpio": data["nombre_limpio"],
            "almacen": wh_nombre,
            "clasificacion": data["clasificacion"],
            "a_la_mano": st_act,
            "stock_actual": st_act,
            "reservado": st_res,
            "disponible": st_disp,
            "ventas_periodo": v_periodo,
            "venta_diaria": round(v_diaria, 3),
            "venta_mensual_est": venta_mensual_est,
            "stock_minimo": stock_minimo,
            "stock_sugerido_mes": stock_sugerido_mes,
            "stock_maximo": stock_maximo,
            "sugerido_pedir": sugerido_pedir,
            "dias_cobertura": dias_cobertura,
            "estado": estado,
            "precio_venta_base": precio_venta_base,
            "precio_venta_iva": precio_venta_con_iva,
            "precio_unitario_est": precio_est, # Precio de venta con IVA (16%)
            "valor_estimado": valor_est,
            "inversion_reorden": inversion_reorden
        })

    lista_inventario.sort(key=lambda x: (x["sugerido_pedir"] > 0, x["sugerido_pedir"], x["disponible"]), reverse=True)
    for i, item in enumerate(lista_inventario, 1): item["posicion"] = i

    resumen_almacenes_list = sorted(list(resumen_almacenes_map.values()), key=lambda x: x["sugerido_pedir"], reverse=True)

    return {
        "inventario": lista_inventario,
        "almacenes_detectados": sorted(list(wh_names_set)),
        "almacenes_resumen": resumen_almacenes_list,
        "totales": {
            "a_la_mano": round(tot_a_la_mano, 2),
            "stock_actual": round(tot_a_la_mano, 2),
            "disponible": round(tot_disp, 2),
            "valor": round(tot_valor, 2),
            "ventas": round(tot_ventas, 2),
            "ventas_mes_est": round(tot_ventas_mes, 2),
            "sugerido_pedir": round(tot_sugerido_pedir, 2),
            "inversion_reorden": round(tot_inversion_reorden, 2),
            "reordenar": n_reordenar,
            "agotados": n_agotados,
            "optimo": n_optimo,
            "sobrestock": n_sobrestock,
            "sin_movimiento": n_sin_movimiento,
            "variedad": len(lista_inventario)
        },
        "n_excluidos_clientes": n_excluidos_clientes
    }


# ── DATOS DEMO (OFFLINE / FALLBACK) ─────────────────────────────────────────
def generar_datos_demo_stock():
    demo_prods = [
        ("AUTOLUX 930 GL", "MULTIMARCA", "CHALLENGER AUTOMOTIVE - QUERETARO", 350, 45, 140, 450.0),
        ("BC BLANCO GL", "CHALLENGER", "CHALLENGER AUTOMOTIVE - QUERETARO", 520, 80, 290, 680.0),
        ("EASY MASTER 800 LT", "PASTA", "BALDOMERO MEDINA GARZA - PLANTA DE PRODUCCION", 810, 120, 340, 320.0),
        ("[RES-017] URACRON 430", "MATERIA PRIMA", "MATERIA PRIMA ALMACEN", 6950, 0, 100, 150.0),
        ("[RES-008] JONCRYL 551", "MATERIA PRIMA", "MATERIA PRIMA ALMACEN", 4800, 0, 80, 210.0),
        ("[SOL-024] XILOL", "MATERIA PRIMA", "MATERIA PRIMA ALMACEN", 3200, 0, 50, 85.0),
        ("[CAR-009] POSSALC 6", "MATERIA PRIMA", "MATERIA PRIMA ALMACEN", 2537, 0, 40, 95.0),
        ("[PIG-020] RAVEN 5000 3 ULTRA", "MATERIA PRIMA", "MATERIA PRIMA ALMACEN", 1500, 0, 30, 420.0),
        ("FONDO DE RELLENO 2K GRIS GL", "CHALLENGER", "ALBERTO MASCORRO - MONTERREY", 45, 10, 120, 580.0),
        ("C311 HARDENER STANDARD 5:1 945ML", "MULTIMARCA", "FABIAN LIZARRAGA - BAJIO", 18, 0, 95, 290.0),
        ("BC NEGRO DEEP BLACK GL", "CHALLENGER", "HUGO IGNACIO ROJAS - ESTADO DE MEXICO", 0, 0, 80, 710.0),
        ("THINNER ACRILICO LT", "CHALLENGER", "CHALLENGER AUTOMOTIVE - QUERETARO", 1200, 150, 450, 95.0),
        ("TRANSPARENTE VT 141 3.78 LT", "MULTIMARCA", "MIGUEL ESCOBAR - VERACRUZ", 210, 25, 60, 620.0),
    ]

    lista = []
    tot_disp = tot_ventas = tot_ventas_mes = tot_valor = tot_sugerido_pedir = tot_inversion_reorden = n_reordenar = n_agotados = n_optimo = n_sobrestock = n_sin_movimiento = 0
    resumen_almacenes_map = {}

    for i, (nom, clas, wh, st, res, v_per, pr_est) in enumerate(demo_prods, 1):
        disp = max(0.0, float(st - res))
        v_dia = float(v_per) / 30.0
        v_mes = round(v_dia * 30.0, 2)
        st_min = max(1, math.ceil(v_dia * 15.0))
        st_sug_mes = max(1, math.ceil(v_dia * 30.0))
        st_max = max(2, math.ceil(v_dia * 60.0))
        sug_pedir = max(0.0, float(st_sug_mes - disp)) if disp < st_sug_mes else 0.0
        dias_cob = (disp / v_dia) if v_dia > 0 else 999.0
        val_est = disp * pr_est
        inv_reorden = sug_pedir * pr_est

        if disp <= 0: est = "AGOTADO"; n_agotados += 1
        elif disp < st_min or dias_cob <= 15: est = "REORDENAR"; n_reordenar += 1
        elif disp > st_max and disp > 50: est = "SOBRESTOCK"; n_sobrestock += 1
        elif v_per == 0: est = "SIN_MOVIMIENTO"; n_sin_movimiento += 1
        else: est = "OPTIMO"; n_optimo += 1

        tot_disp += disp; tot_ventas += v_per; tot_ventas_mes += v_mes
        tot_valor += val_est; tot_sugerido_pedir += sug_pedir; tot_inversion_reorden += inv_reorden

        if wh not in resumen_almacenes_map:
            resumen_almacenes_map[wh] = {"almacen": wh, "disponible": 0.0, "valor": 0.0, "ventas_mes": 0.0, "sugerido_pedir": 0.0, "inversion_reorden": 0.0, "num_agotados": 0, "num_reordenar": 0, "num_productos": 0}
        rw = resumen_almacenes_map[wh]
        rw["disponible"] += disp; rw["valor"] += val_est; rw["ventas_mes"] += v_mes; rw["sugerido_pedir"] += sug_pedir; rw["inversion_reorden"] += inv_reorden; rw["num_productos"] += 1
        if est == "AGOTADO": rw["num_agotados"] += 1
        if est == "REORDENAR": rw["num_reordenar"] += 1

        lista.append({
            "posicion": i, "product_id": i, "producto": nom, "nombre_limpio": nom,
            "almacen": wh, "clasificacion": clas, "stock_actual": float(st),
            "reservado": float(res), "disponible": float(disp), "ventas_periodo": float(v_per),
            "venta_diaria": round(v_dia, 3), "venta_mensual_est": v_mes,
            "stock_minimo": st_min, "stock_sugerido_mes": st_sug_mes, "stock_maximo": st_max,
            "sugerido_pedir": sug_pedir, "dias_cobertura": dias_cob, "estado": est,
            "precio_unitario_est": pr_est, "valor_estimado": val_est, "inversion_reorden": inv_reorden
        })

    return {
        "inventario": lista,
        "almacenes_detectados": [
            "CHALLENGER AUTOMOTIVE - QUERETARO", "ALBERTO MASCORRO - MONTERREY",
            "HUGO IGNACIO ROJAS - ESTADO DE MEXICO", "BALDOMERO MEDINA GARZA - PLANTA DE PRODUCCION",
            "MIGUEL ESCOBAR - VERACRUZ", "FABIAN LIZARRAGA - BAJIO", "JULIAN GARCIA - TIJUANA",
            "UNIDAD MOVIL ALEJANDRO GARCIA RAMIREZ - HERMOSILLO", "TALLER EXTERNO",
            "Muestras-Jesus", "MATERIA PRIMA ALMACEN", "JORGE IVAN GARCIA - JALISCO"
        ],
        "almacenes_resumen": list(resumen_almacenes_map.values()),
        "totales": {
            "disponible": tot_disp, "valor": tot_valor, "ventas": tot_ventas,
            "ventas_mes_est": tot_ventas_mes, "sugerido_pedir": tot_sugerido_pedir,
            "inversion_reorden": tot_inversion_reorden, "reordenar": n_reordenar,
            "agotados": n_agotados, "optimo": n_optimo, "sobrestock": n_sobrestock,
            "sin_movimiento": n_sin_movimiento, "variedad": len(lista)
        },
        "n_excluidos_clientes": 0
    }


# ── ADMINISTRADOR DE CRON Y CACHÉ EN SEGUNDO PLANO ────────────────────────────
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_odoo.json")
COBRANZA_DISK_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cache_cartera_cobranza.json")

_COBRANZA_MEM_CACHE = {}
_COBRANZA_MEM_TIME = {}

NO_VENDEDORES_SISTEMA = {
    'ventas', 'bmg', 'sistemas', 'administrador', 'admin', 'odoobot',
    'cedis', 'cedis qro', 'empleado', 'externo', 'sin asignar', 'sin asignacion', ''
}

def _obtener_cartera_cobranza_engine_impl(empresa_nombre="TODAS (Consolidado)", vendedor_valor="TODOS", vendedor_nombre="TODOS", excluir_interempresa=True):
    empresa_cfg = EMPRESAS.get(empresa_nombre)
    company_id = empresa_cfg["company_id"] if empresa_cfg else None

    uid, models = conectar_odoo(company_id or 1)

    # 1. Fetch Official Sales Reps list
    vendedores_list = obtener_vendedores_odoo(company_id or 1)
    vendedores_oficiales_map = {val: lbl for val, lbl in vendedores_list}

    # 2. Search all posted invoices (from 2026-01-01)
    domain = [
        ('move_type', 'in', ['out_invoice', 'out_refund']),
        ('state', '=', 'posted'),
        ('invoice_date', '>=', '2026-01-01')
    ]
    if company_id is not None:
        domain.append(('company_id', '=', company_id))

    fields = [
        'name', 'invoice_date', 'invoice_date_due', 'partner_id',
        'invoice_user_id', 'amount_total', 'amount_untaxed', 'amount_residual',
        'payment_state', 'invoice_line_ids', 'move_type'
    ]

    invs = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'account.move', 'search_read', [domain],
        {'fields': fields, 'limit': 4000}
    )

    hoy = date.today()
    CLIENTES_INTEREMPRESA = ["auto linea multitrans", "autolinea multitrans", "baldomero medina garza"]

    # Pre-fetch partner properties & contact details in ONE fast batch (only for partners in these invoices)
    partner_ids_all = list(set([
        inv['partner_id'][0] for inv in invs
        if inv.get('partner_id') and isinstance(inv['partner_id'], (list, tuple))
    ]))

    partner_vendor_map = {}
    partner_contacts_map = {}
    partner_user_map = {}

    if partner_ids_all:
        CHUNK_P = 200
        for b_i in range(0, len(partner_ids_all), CHUNK_P):
            b_pids = partner_ids_all[b_i:b_i+CHUNK_P]
            try:
                p_records = models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    'res.partner', 'search_read',
                    [[('id', 'in', b_pids)]],
                    {'fields': ['id', 'name', 'properties', 'commercial_partner_id', 'user_id', 'vat', 'phone', 'phone_sanitized', 'email', 'city', 'contact_address_inline', 'invoice_emails']}
                )
                for pr in p_records:
                    pid = pr['id']
                    v_val = None
                    for prop in (pr.get('properties') or []):
                        if prop.get('name') == PROP_VENDEDOR_KEY:
                            val = prop.get('value')
                            v_val = val[0] if isinstance(val, (list, tuple)) and val else val
                            break
                    if v_val and v_val in vendedores_oficiales_map:
                        partner_vendor_map[pid] = v_val
                        comm_tuple = pr.get('commercial_partner_id')
                        if comm_tuple and isinstance(comm_tuple, (list, tuple)):
                            partner_vendor_map[comm_tuple[0]] = v_val

                    if pr.get('user_id') and isinstance(pr['user_id'], (list, tuple)):
                        partner_user_map[pid] = pr['user_id']

                    tel = pr.get('phone_sanitized') or pr.get('phone') or ''
                    mail = pr.get('email') or pr.get('invoice_emails') or ''
                    partner_contacts_map[pid] = {
                        'vat': pr.get('vat') or '',
                        'phone': str(tel).strip() if tel else '',
                        'phone_raw': str(pr.get('phone') or '').strip(),
                        'email': str(mail).strip() if mail else '',
                        'city': str(pr.get('city') or '').strip(),
                        'address': str(pr.get('contact_address_inline') or '').strip()
                    }
            except Exception as e_p:
                print(f"[ERROR partner_contacts_map]: {e_p}")

    # Pre-fetch line details for unpaid lines only (to save bandwidth)
    unpaid_line_ids = []
    for inv in invs:
        if float(inv.get('amount_residual', 0) or 0) > 0:
            unpaid_line_ids.extend(inv.get('invoice_line_ids') or [])

    lines_map = {}
    if unpaid_line_ids and len(unpaid_line_ids) <= 3000:
        try:
            line_fields = ['move_id', 'name', 'quantity', 'price_unit', 'price_subtotal']
            lines_data = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'account.move.line', 'search_read',
                [[('id', 'in', unpaid_line_ids)]],
                {'fields': line_fields}
            )
            for l in lines_data:
                m_id = l.get('move_id')[0] if (l.get('move_id') and isinstance(l.get('move_id'), (list, tuple))) else l.get('move_id')
                if m_id not in lines_map:
                    lines_map[m_id] = []
                lines_map[m_id].append({
                    'producto': l.get('name') or 'Producto',
                    'cantidad': float(l.get('quantity', 0) or 0),
                    'precio_unit': float(l.get('price_unit', 0) or 0),
                    'subtotal': float(l.get('price_subtotal', 0) or 0)
                })
        except Exception:
            pass

    cuentas = []
    tot_cartera = 0
    tot_al_dia = 0
    tot_reciente_0_60 = 0
    tot_pasada_60_100 = 0
    tot_atrasada_100_mas = 0

    count_reciente_0_60 = 0
    count_pasada_60_100 = 0
    count_atrasada_100_mas = 0
    count_al_dia = 0

    # Grouped clients map for active unpaid portfolio
    clientes_agrupados = {}

    # Monthly recovery cycles map: "Vendido en Mes X vs A Recuperar en Mes X+1"
    meses_nombres_es = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    ciclos_mensuales = {}

    for inv in invs:
        inv_id = inv.get('id')
        partner_tuple = inv.get('partner_id')
        cliente_nom = partner_tuple[1] if (partner_tuple and isinstance(partner_tuple, (list, tuple))) else 'Cliente Desconocido'
        cliente_id = partner_tuple[0] if (partner_tuple and isinstance(partner_tuple, (list, tuple))) else None

        if excluir_interempresa:
            c_norm = normalizar_texto(cliente_nom)
            if any(ex in c_norm for ex in CLIENTES_INTEREMPRESA):
                continue

        # Resolve Salesperson using official sales reps
        v_val_cli = partner_vendor_map.get(cliente_id)
        vendedor_tuple = inv.get('invoice_user_id')

        vend_nom = 'Sin Vendedor Asignado'
        vend_val = 'SIN_ASIGNAR'

        if v_val_cli and v_val_cli in vendedores_oficiales_map:
            vend_nom = vendedores_oficiales_map[v_val_cli]
            vend_val = v_val_cli
        elif vendedor_tuple and isinstance(vendedor_tuple, (list, tuple)):
            raw_v_nom = vendedor_tuple[1]
            norm_v = normalizar_texto(raw_v_nom)
            if norm_v not in NO_VENDEDORES_SISTEMA:
                for v_k, v_n in vendedores_oficiales_map.items():
                    if normalizar_texto(v_n) == norm_v or normalizar_texto(v_k) == norm_v:
                        vend_nom = v_n
                        vend_val = v_k
                        break
                if vend_nom in ('Sin Asignar', 'Sin Vendedor Asignado', '') and norm_v not in NO_VENDEDORES_SISTEMA:
                    vend_nom = raw_v_nom
        if vend_nom in ('Sin Asignar', 'Sin Vendedor Asignado', ''):
            if cliente_id in partner_user_map:
                u_tup = partner_user_map[cliente_id]
                if u_tup and isinstance(u_tup, (list, tuple)):
                    norm_u = normalizar_texto(u_tup[1])
                    if norm_u not in NO_VENDEDORES_SISTEMA:
                        for v_k, v_n in vendedores_oficiales_map.items():
                            if normalizar_texto(v_n) == norm_u or normalizar_texto(v_k) == norm_u:
                                vend_nom = v_n
                                vend_val = v_k
                                break
                        if vend_nom in ('Sin Asignar', 'Sin Vendedor Asignado', '') and norm_u not in NO_VENDEDORES_SISTEMA:
                            vend_nom = u_tup[1]

        if normalizar_texto(vend_nom) in NO_VENDEDORES_SISTEMA:
            vend_nom = 'Sin Vendedor Asignado'
            vend_val = 'SIN_ASIGNAR'

        f_fact_str = inv.get('invoice_date') or ''
        f_venc_str = inv.get('invoice_date_due') or f_fact_str

        dias_retraso = 0
        f_fact_dt = None
        f_venc_dt = None
        if f_fact_str:
            try:
                f_fact_dt = datetime.strptime(f_fact_str, '%Y-%m-%d').date()
            except Exception:
                pass
        if f_venc_str:
            try:
                f_venc_dt = datetime.strptime(f_venc_str, '%Y-%m-%d').date()
                if hoy > f_venc_dt:
                    dias_retraso = (hoy - f_venc_dt).days
            except Exception:
                pass

        if not f_fact_dt:
            continue

        # Calculate exact requested aging buckets:
        if dias_retraso <= 0:
            rango_cobranza = 'AL_DIA'
            estatus_cartera = 'AL_DIA'
        elif dias_retraso <= 60:
            rango_cobranza = 'RECIENTE_0_60'
            estatus_cartera = 'RECIENTE_0_60'
        elif dias_retraso <= 100:
            rango_cobranza = 'PASADA_60_100'
            estatus_cartera = 'PASADA_60_100'
        else:
            rango_cobranza = 'ATRASADA_100_MAS'
            estatus_cartera = 'ATRASADA_100_MAS'

        is_refund = inv.get('move_type') == 'out_refund'
        total_raw = float(inv.get('amount_total', 0) or 0)
        untaxed_raw = float(inv.get('amount_untaxed', 0) or 0)
        saldo_raw = float(inv.get('amount_residual', 0) or 0)
        
        total = -abs(total_raw) if is_refund else total_raw
        untaxed = -abs(untaxed_raw) if is_refund else untaxed_raw
        saldo = -abs(saldo_raw) if is_refund else saldo_raw
        abonado = max(0.0, total - saldo)

        contact_info = partner_contacts_map.get(cliente_id, {})
        telefono = contact_info.get('phone', '')
        telefono_raw = contact_info.get('phone_raw', '')
        email = contact_info.get('email', '')
        rfc = contact_info.get('vat', '')
        ciudad = contact_info.get('city', '')
        direccion = contact_info.get('address', '')

        # -----------------------------------------------------------------
        # A) PROCESAR CICLO DE VENTA VS RECUPERACIÓN AL SIGUIENTE MES
        # -----------------------------------------------------------------
        mes_key = f_fact_dt.strftime('%Y-%m') # ej '2026-08'
        mes_venta_nom = f"{meses_nombres_es.get(f_fact_dt.month, '')} {f_fact_dt.year}"
        
        # Siguiente mes
        sig_y = f_fact_dt.year if f_fact_dt.month < 12 else f_fact_dt.year + 1
        sig_m = f_fact_dt.month + 1 if f_fact_dt.month < 12 else 1
        mes_sig_nom = f"{meses_nombres_es.get(sig_m, '')} {sig_y}"
        mes_sig_key = f"{sig_y:04d}-{sig_m:02d}"

        venc_mes_key = f_venc_dt.strftime('%Y-%m') if f_venc_dt else mes_sig_key

        # Filtrar ciclo por vendedor si se especificó filtro de vendedor
        es_del_vendedor_ciclo = True
        if vendedor_valor and str(vendedor_valor).upper() != 'TODOS':
            match_c_val = (str(vend_val) == str(vendedor_valor)) or (v_val_cli and str(v_val_cli) == str(vendedor_valor))
            match_c_nom = (vendedor_nombre and str(vendedor_nombre).upper() != 'TODOS' and (normalizar_texto(vendedor_nombre) in normalizar_texto(vend_nom) or normalizar_texto(vend_nom) in normalizar_texto(vendedor_nombre))) or (str(vendedor_valor).lower() in normalizar_texto(vend_nom))
            es_del_vendedor_ciclo = match_c_val or match_c_nom

        if es_del_vendedor_ciclo:
            if mes_key not in ciclos_mensuales:
                ciclos_mensuales[mes_key] = {
                    'mes_key': mes_key,
                    'mes_venta': mes_venta_nom,
                    'mes_siguiente': mes_sig_nom,
                    'mes_siguiente_key': mes_sig_key,
                    'total_vendido': 0.0,
                    'subtotal_vendido': 0.0,
                    'a_recuperar_mes_sig': 0.0,
                    'ya_recuperado': 0.0,
                    'saldo_pendiente': 0.0,
                    'facturas_count': 0,
                    'clientes_set': set(),
                    'vendedores_map': {},
                    'facturas': []
                }

            cm = ciclos_mensuales[mes_key]
            cm['total_vendido'] += total
            cm['subtotal_vendido'] += untaxed
            cm['ya_recuperado'] += abonado
            cm['saldo_pendiente'] += saldo
            cm['facturas_count'] += 1
            cm['clientes_set'].add(cliente_nom)

            # Regla de recuperación: proyectado al mes siguiente
            cm['a_recuperar_mes_sig'] += total

            # Desglose por vendedor en el mes
            if vend_nom not in cm['vendedores_map']:
                cm['vendedores_map'][vend_nom] = {
                    'vendedor': vend_nom,
                    'vendedor_id': vend_val,
                    'total_vendido': 0.0,
                    'subtotal_vendido': 0.0,
                    'a_recuperar_mes_sig': 0.0,
                    'ya_recuperado': 0.0,
                    'saldo_pendiente': 0.0,
                    'facturas_count': 0
                }
            vm_ciclo = cm['vendedores_map'][vend_nom]
            vm_ciclo['total_vendido'] += total
            vm_ciclo['subtotal_vendido'] += untaxed
            vm_ciclo['a_recuperar_mes_sig'] += total
            vm_ciclo['ya_recuperado'] += abonado
            vm_ciclo['saldo_pendiente'] += saldo
            vm_ciclo['facturas_count'] += 1

            # Agregar factura al ciclo
            f_estatus_cobro = 'PAGADA' if saldo <= 0.01 else ('PARCIAL' if abonado > 0 else 'PENDIENTE')
            cm['facturas'].append({
                'inv_id': inv_id,
                'folio': inv.get('name') or f'INV-{inv_id}',
                'cliente': cliente_nom,
                'cliente_id': cliente_id,
                'vendedor': vend_nom,
                'vendedor_id': vend_val,
                'fecha_factura': f_fact_str,
                'fecha_vencimiento': f_venc_str,
                'dias_retraso': dias_retraso,
                'rango_cobranza': rango_cobranza,
                'estatus_cobro': f_estatus_cobro,
                'subtotal_factura': untaxed,
                'total_factura': total,
                'monto_abonado': abonado,
                'saldo_pendiente': saldo,
                'telefono': telefono,
                'email': email,
                'ciudad': ciudad
            })

        # -----------------------------------------------------------------
        # B) PROCESAR CARTERA VIVA DEUDORA (SALDO PENDIENTE > 0)
        # -----------------------------------------------------------------
        if saldo > 0.01:
            # Filter by seller if specific seller is selected
            if vendedor_valor and str(vendedor_valor).upper() != 'TODOS':
                match_val = (str(vend_val) == str(vendedor_valor)) or (v_val_cli and str(v_val_cli) == str(vendedor_valor))
                match_nom = normalizar_texto(vendedor_nombre) in normalizar_texto(vend_nom)
                if not match_val and not match_nom:
                    continue

            tot_cartera += saldo

            if dias_retraso <= 0:
                tot_al_dia += saldo
                count_al_dia += 1
            elif dias_retraso <= 60:
                tot_reciente_0_60 += saldo
                count_reciente_0_60 += 1
            elif dias_retraso <= 100:
                tot_pasada_60_100 += saldo
                count_pasada_60_100 += 1
            else:
                tot_atrasada_100_mas += saldo
                count_atrasada_100_mas += 1

            cuentas.append({
                'inv_id': inv_id,
                'folio': inv.get('name') or f'INV-{inv_id}',
                'cliente': cliente_nom,
                'cliente_id': cliente_id,
                'rfc': rfc,
                'telefono': telefono,
                'telefono_raw': telefono_raw,
                'email': email,
                'ciudad': ciudad,
                'direccion': direccion,
                'vendedor': vend_nom,
                'vendedor_id': vend_val,
                'fecha_factura': f_fact_str,
                'fecha_vencimiento': f_venc_str,
                'dias_retraso': dias_retraso,
                'rango_cobranza': rango_cobranza,
                'estatus_cartera': estatus_cartera,
                'subtotal_factura': untaxed,
                'total_factura': total,
                'monto_abonado': abonado,
                'saldo_pendiente': saldo,
                'payment_state': inv.get('payment_state', 'not_paid'),
                'lineas_producto': lines_map.get(inv_id, [])
            })

            # Agrupar cartera por cliente
            c_key = f"{cliente_id}_{cliente_nom}"
            if c_key not in clientes_agrupados:
                clientes_agrupados[c_key] = {
                    'cliente_id': cliente_id,
                    'cliente': cliente_nom,
                    'rfc': rfc,
                    'telefono': telefono,
                    'telefono_raw': telefono_raw,
                    'email': email,
                    'ciudad': ciudad,
                    'direccion': direccion,
                    'vendedor': vend_nom,
                    'vendedor_id': vend_val,
                    'total_facturado': 0.0,
                    'total_abonado': 0.0,
                    'saldo_total': 0.0,
                    'saldo_al_dia': 0.0,
                    'saldo_reciente_0_60': 0.0,
                    'saldo_pasada_60_100': 0.0,
                    'saldo_atrasada_100_mas': 0.0,
                    'max_dias_retraso': 0,
                    'facturas': []
                }
            
            c_entry = clientes_agrupados[c_key]
            c_entry['total_facturado'] += total
            c_entry['total_abonado'] += abonado
            c_entry['saldo_total'] += saldo
            if dias_retraso > c_entry['max_dias_retraso']:
                c_entry['max_dias_retraso'] = dias_retraso
            
            if dias_retraso <= 0:
                c_entry['saldo_al_dia'] += saldo
            elif dias_retraso <= 60:
                c_entry['saldo_reciente_0_60'] += saldo
            elif dias_retraso <= 100:
                c_entry['saldo_pasada_60_100'] += saldo
            else:
                c_entry['saldo_atrasada_100_mas'] += saldo
                
            c_entry['facturas'].append({
                'inv_id': inv_id,
                'folio': inv.get('name') or f'INV-{inv_id}',
                'fecha_factura': f_fact_str,
                'fecha_vencimiento': f_venc_str,
                'dias_retraso': dias_retraso,
                'rango_cobranza': rango_cobranza,
                'subtotal_factura': untaxed,
                'total_factura': total,
                'monto_abonado': abonado,
                'saldo_pendiente': saldo,
                'lineas_producto': lines_map.get(inv_id, [])
            })

    # Finalize grouped clients
    clientes_lista = []
    for c_key, c_val in clientes_agrupados.items():
        max_d = c_val['max_dias_retraso']
        if max_d > 100:
            c_val['rango_predominante'] = 'ATRASADA_100_MAS'
        elif max_d > 60:
            c_val['rango_predominante'] = 'PASADA_60_100'
        elif max_d > 0:
            c_val['rango_predominante'] = 'RECIENTE_0_60'
        else:
            c_val['rango_predominante'] = 'AL_DIA'
        c_val['num_facturas'] = len(c_val['facturas'])
        c_val['facturas'].sort(key=lambda x: x['dias_retraso'], reverse=True)
        clientes_lista.append(c_val)

    clientes_lista.sort(key=lambda x: (x['max_dias_retraso'], x['saldo_total']), reverse=True)
    # Vendedores únicos detectados (todos los oficiales + cualquier vendedor activo en cuentas)
    all_vends_set = set(vendedores_oficiales_map.values()) | set(c['vendedor'] for c in cuentas if c.get('vendedor') and c.get('vendedor') != 'Sin Vendedor Asignado')
    vendedores_unicos = sorted(list(all_vends_set))

    # Per-salesperson metrics breakdown (Cartera Deudora)
    vend_metricas = {}
    for c in cuentas:
        v_name = c['vendedor']
        if v_name not in vend_metricas:
            vend_metricas[v_name] = {
                'vendedor': v_name,
                'vendedor_id': c['vendedor_id'],
                'saldo_total': 0.0,
                'saldo_al_dia': 0.0,
                'saldo_reciente_0_60': 0.0,
                'saldo_pasada_60_100': 0.0,
                'saldo_atrasada_100_mas': 0.0,
                'facturas_count': 0,
                'clientes_set': set()
            }
        vm = vend_metricas[v_name]
        vm['saldo_total'] += c['saldo_pendiente']
        vm['facturas_count'] += 1
        vm['clientes_set'].add(c['cliente'])
        d = c['dias_retraso']
        if d <= 0:
            vm['saldo_al_dia'] += c['saldo_pendiente']
        elif d <= 60:
            vm['saldo_reciente_0_60'] += c['saldo_pendiente']
        elif d <= 100:
            vm['saldo_pasada_60_100'] += c['saldo_pendiente']
        else:
            vm['saldo_atrasada_100_mas'] += c['saldo_pendiente']

    vend_metricas_list = []
    for vm in vend_metricas.values():
        vm_copy = dict(vm)
        vm_copy['clientes_count'] = len(vm_copy.pop('clientes_set'))
        for k in ['saldo_total', 'saldo_al_dia', 'saldo_reciente_0_60', 'saldo_pasada_60_100', 'saldo_atrasada_100_mas']:
            vm_copy[k] = round(vm_copy[k], 2)
        vend_metricas_list.append(vm_copy)

    vend_metricas_list.sort(key=lambda x: x['saldo_total'], reverse=True)

    # Finalize monthly recovery cycles list
    ciclos_lista = []
    for m_k in sorted(ciclos_mensuales.keys(), reverse=True):
        m_data = ciclos_mensuales[m_k]
        m_data['clientes_count'] = len(m_data.pop('clientes_set'))
        v_list = list(m_data.pop('vendedores_map').values())
        for v in v_list:
            v['tasa_recuperacion'] = round((v['ya_recuperado'] / v['total_vendido'] * 100), 1) if v['total_vendido'] > 0 else 0.0
            v['total_vendido'] = round(v['total_vendido'], 2)
            v['subtotal_vendido'] = round(v.get('subtotal_vendido', 0.0), 2)
            v['a_recuperar_mes_sig'] = round(v['a_recuperar_mes_sig'], 2)
            v['ya_recuperado'] = round(v['ya_recuperado'], 2)
            v['saldo_pendiente'] = round(v['saldo_pendiente'], 2)
        v_list.sort(key=lambda x: x['total_vendido'], reverse=True)
        m_data['vendedores'] = v_list
        m_data['tasa_recuperacion'] = round((m_data['ya_recuperado'] / m_data['total_vendido'] * 100), 1) if m_data['total_vendido'] > 0 else 0.0
        m_data['total_vendido'] = round(m_data['total_vendido'], 2)
        m_data['subtotal_vendido'] = round(m_data.get('subtotal_vendido', 0.0), 2)
        m_data['a_recuperar_mes_sig'] = round(m_data['a_recuperar_mes_sig'], 2)
        m_data['ya_recuperado'] = round(m_data['ya_recuperado'], 2)
        m_data['saldo_pendiente'] = round(m_data['saldo_pendiente'], 2)
        ciclos_lista.append(m_data)

    resumen_global_ciclos = {
        'total_vendido': round(sum(c['total_vendido'] for c in ciclos_lista), 2),
        'subtotal_vendido': round(sum(c.get('subtotal_vendido', 0.0) for c in ciclos_lista), 2),
        'total_a_recuperar': round(sum(c['a_recuperar_mes_sig'] for c in ciclos_lista), 2),
        'total_ya_recuperado': round(sum(c['ya_recuperado'] for c in ciclos_lista), 2),
        'total_saldo_pendiente': round(sum(c['saldo_pendiente'] for c in ciclos_lista), 2),
        'tasa_recuperacion': round((sum(c['ya_recuperado'] for c in ciclos_lista) / sum(c['total_vendido'] for c in ciclos_lista) * 100), 1) if sum(c['total_vendido'] for c in ciclos_lista) > 0 else 0.0,
        'meses_disponibles': [{'key': c['mes_key'], 'nombre_venta': c['mes_venta'], 'nombre_recupera': c['mes_siguiente']} for c in ciclos_lista]
    }

    # ── PAGOS DEL CLIENTE (ACCOUNT.PAYMENT) AGRUPADOS POR MES Y POR CLIENTE ───
    p_domain = [
        ('payment_type', '=', 'inbound'),
        ('partner_type', '=', 'customer'),
        ('state', 'in', ['posted', 'in_process', 'paid']),
        ('date', '>=', '2026-01-01')
    ]
    if company_id:
        p_domain.append(('company_id', '=', company_id))

    p_fields = ['id', 'name', 'date', 'amount', 'partner_id', 'journal_id', 'memo', 'company_id', 'state', 'reconciled_invoice_ids']
    try:
        payments_raw = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'account.payment', 'search_read', [p_domain],
            {'fields': p_fields, 'order': 'date desc', 'limit': 15000}
        )
    except Exception as e_pay:
        print(f"[WARN account.payment search_read]: {e_pay}")
        payments_raw = []

    # Mapa de facturas conocidas en memoria para cruce instantáneo de vendedor
    inv_by_id = {inv['id']: inv for inv in invs}
    inv_by_name = {inv['name']: inv for inv in invs if inv.get('name')}

    # Pre-cargar facturas conciliadas que no estén en invs (ej. emitidas antes del rango)
    missing_inv_ids = list(set(
        inv_id for p in payments_raw for inv_id in (p.get('reconciled_invoice_ids') or [])
        if inv_id not in inv_by_id
    ))
    if missing_inv_ids:
        CHUNK_INV = 500
        for b_i in range(0, len(missing_inv_ids), CHUNK_INV):
            b_ids = missing_inv_ids[b_i:b_i+CHUNK_INV]
            try:
                extra_invs = models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    'account.move', 'search_read',
                    [[('id', 'in', b_ids)]],
                    {'fields': ['id', 'name', 'invoice_user_id', 'partner_id', 'amount_total']}
                )
                for ei in extra_invs:
                    inv_by_id[ei['id']] = ei
                    if ei.get('name'):
                        inv_by_name[ei['name']] = ei
            except Exception as e_extra:
                print(f"[WARN fetch missing reconciled invoices]: {e_extra}")

    # Pre-cargar properties y usuarios de clientes que tengan pagos pero no facturas en invs
    payment_pids = [
        p['partner_id'][0] for p in payments_raw
        if p.get('partner_id') and isinstance(p['partner_id'], (list, tuple))
    ]
    missing_pids = [pid for pid in set(payment_pids) if pid not in partner_vendor_map and pid not in partner_user_map]
    if missing_pids:
        CHUNK_P = 200
        for b_i in range(0, len(missing_pids), CHUNK_P):
            b_pids = missing_pids[b_i:b_i+CHUNK_P]
            try:
                p_records = models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    'res.partner', 'search_read',
                    [[('id', 'in', b_pids)]],
                    {'fields': ['id', 'name', 'properties', 'commercial_partner_id', 'user_id', 'vat', 'phone', 'phone_sanitized', 'email', 'city', 'contact_address_inline', 'invoice_emails']}
                )
                for pr in p_records:
                    pid = pr['id']
                    v_val = None
                    for prop in (pr.get('properties') or []):
                        if prop.get('name') == PROP_VENDEDOR_KEY:
                            val = prop.get('value')
                            v_val = val[0] if isinstance(val, (list, tuple)) and val else val
                            break
                    if v_val and v_val in vendedores_oficiales_map:
                        partner_vendor_map[pid] = v_val
                        comm_tuple = pr.get('commercial_partner_id')
                        if comm_tuple and isinstance(comm_tuple, (list, tuple)):
                            partner_vendor_map[comm_tuple[0]] = v_val
                    if pr.get('user_id') and isinstance(pr['user_id'], (list, tuple)):
                        partner_user_map[pid] = pr['user_id']
                    tel = pr.get('phone_sanitized') or pr.get('phone') or ''
                    mail = pr.get('email') or pr.get('invoice_emails') or ''
                    partner_contacts_map[pid] = {
                        'vat': pr.get('vat') or '',
                        'phone': str(tel).strip() if tel else '',
                        'phone_raw': str(pr.get('phone') or '').strip(),
                        'email': str(mail).strip() if mail else '',
                        'city': str(pr.get('city') or '').strip(),
                        'address': str(pr.get('contact_address_inline') or '').strip()
                    }
            except Exception as e_pm:
                print(f"[WARN fetch missing payment partners]: {e_pm}")

    # Map payments by month (date of payment)
    pagos_por_mes_dict = {}
    for p in payments_raw:
        p_tuple = p.get('partner_id')
        p_nom = p_tuple[1] if (p_tuple and isinstance(p_tuple, (list, tuple))) else 'Cliente Desconocido'
        p_id = p_tuple[0] if (p_tuple and isinstance(p_tuple, (list, tuple))) else 0

        if excluir_interempresa:
            p_norm = normalizar_texto(p_nom)
            if any(ex in p_norm for ex in CLIENTES_INTEREMPRESA):
                continue

        f_pago_str = p.get('date') or ''
        if not f_pago_str:
            continue

        try:
            dt_p = datetime.strptime(f_pago_str[:10], '%Y-%m-%d').date()
            m_key = dt_p.strftime('%Y-%m')
            m_label = f"{meses_nombres_es.get(dt_p.month, '')} {dt_p.year}"
            y_num = dt_p.year
            m_num = dt_p.month
        except Exception:
            continue

        monto = float(p.get('amount', 0) or 0)
        j_tuple = p.get('journal_id')
        diario_nom = j_tuple[1] if (j_tuple and isinstance(j_tuple, (list, tuple))) else 'Banco'

        # Determinar la factura y vendedor REAL que generó la venta
        rec_ids = p.get('reconciled_invoice_ids') or []
        matched_inv = None
        if rec_ids and rec_ids[0] in inv_by_id:
            matched_inv = inv_by_id[rec_ids[0]]
        elif p.get('memo'):
            m_match = re.search(r'INV/\d{4}/\d+', str(p.get('memo') or ''))
            if m_match and m_match.group(0) in inv_by_name:
                matched_inv = inv_by_name[m_match.group(0)]

        vend_nom = 'Sin Asignar'

        # Prioridad 1: Vendedor asignado al cliente en res.partner (properties -> PROP_VENDEDOR_KEY)
        v_val_cli = partner_vendor_map.get(p_id)
        if v_val_cli and v_val_cli in vendedores_oficiales_map:
            vend_nom = vendedores_oficiales_map[v_val_cli]

        # Prioridad 2: Si el cliente no tiene en properties, ver si la factura conciliada tiene un vendedor humano oficial
        if vend_nom in ('Sin Asignar', 'Sin Vendedor Asignado', ''):
            if matched_inv:
                inv_u = matched_inv.get('invoice_user_id')
                if inv_u and isinstance(inv_u, (list, tuple)):
                    raw_u_nom = inv_u[1]
                    norm_u = normalizar_texto(raw_u_nom)
                    if norm_u not in NO_VENDEDORES_SISTEMA:
                        for v_k, v_n in vendedores_oficiales_map.items():
                            if normalizar_texto(v_n) == norm_u or normalizar_texto(v_k) == norm_u:
                                vend_nom = v_n
                                break
                        if vend_nom in ('Sin Asignar', 'Sin Vendedor Asignado', '') and norm_u not in NO_VENDEDORES_SISTEMA:
                            vend_nom = raw_u_nom

        # Prioridad 3: Ver user_id del partner
        if vend_nom in ('Sin Asignar', 'Sin Vendedor Asignado', ''):
            u_tup = partner_user_map.get(p_id)
            if u_tup and isinstance(u_tup, (list, tuple)):
                p_u_nom = normalizar_texto(u_tup[1])
                if p_u_nom not in NO_VENDEDORES_SISTEMA:
                    for v_k, v_n in vendedores_oficiales_map.items():
                        if normalizar_texto(v_n) == p_u_nom:
                            vend_nom = v_n
                            break
                    if vend_nom in ('Sin Asignar', 'Sin Vendedor Asignado', ''):
                        vend_nom = u_tup[1]

        # Sanity check: Si de alguna forma quedó un usuario del sistema, forzar 'Sin Asignar'
        if normalizar_texto(vend_nom) in NO_VENDEDORES_SISTEMA:
            vend_nom = 'Sin Asignar'

        # Si se seleccionó un vendedor específico en el filtro superior, omitir pagos que no le pertenecen
        if vendedor_valor and str(vendedor_valor).upper() != 'TODOS':
            match_v_val = (v_val_cli and str(v_val_cli) == str(vendedor_valor))
            match_v_nom = (vendedor_nombre and str(vendedor_nombre).upper() != 'TODOS' and (normalizar_texto(vendedor_nombre) in normalizar_texto(vend_nom) or normalizar_texto(vend_nom) in normalizar_texto(vendedor_nombre))) or (str(vendedor_valor).lower() in normalizar_texto(vend_nom))
            if not match_v_val and not match_v_nom:
                continue

        c_info = partner_contacts_map.get(p_id, {})
        rfc = c_info.get('vat', '')
        tel = c_info.get('phone', '')
        mail = c_info.get('email', '')

        if m_key not in pagos_por_mes_dict:
            pagos_por_mes_dict[m_key] = {
                'mes_key': m_key,
                'mes_nombre': m_label,
                'anio': y_num,
                'mes_num': m_num,
                'total_cobrado': 0.0,
                'num_pagos': 0,
                'pagos': [],
                'clientes_map': {}
            }

        pm = pagos_por_mes_dict[m_key]
        pm['total_cobrado'] += monto
        pm['num_pagos'] += 1

        f_ref_folio = matched_inv.get('name') if matched_inv else (p.get('memo') or 'Pago directo')

        p_obj = {
            'id': p.get('id'),
            'folio': p.get('name') or f"PAG-{p.get('id')}",
            'fecha': f_pago_str,
            'monto': round(monto, 2),
            'cliente': p_nom,
            'cliente_id': p_id,
            'vendedor': vend_nom,
            'diario': diario_nom,
            'memo': p.get('memo') or '',
            'factura_folio': f_ref_folio
        }
        pm['pagos'].append(p_obj)

        if p_id not in pm['clientes_map']:
            saldo_actual_cli = clientes_agrupados[f"{p_id}_{p_nom}"]['saldo_total'] if f"{p_id}_{p_nom}" in clientes_agrupados else (clientes_agrupados.get(p_id, {}).get('saldo_total', 0.0))
            pm['clientes_map'][p_id] = {
                'cliente_id': p_id,
                'cliente_nombre': p_nom,
                'rfc': rfc,
                'vendedor': vend_nom,
                'telefono': tel,
                'email': mail,
                'total_cobrado': 0.0,
                'num_pagos': 0,
                'saldo_actual_cliente': round(saldo_actual_cli, 2),
                'pagos': []
            }

        c_entry = pm['clientes_map'][p_id]
        c_entry['total_cobrado'] += monto
        c_entry['num_pagos'] += 1
        c_entry['pagos'].append(p_obj)

    # ── MAPEAR FACTURAS POR MES DE VENCIMIENTO (COBRANZA ESTIMADA) ────────────
    vencimiento_meses_dict = {}
    for inv in invs:
        partner_tuple = inv.get('partner_id')
        cliente_nom = partner_tuple[1] if (partner_tuple and isinstance(partner_tuple, (list, tuple))) else 'Cliente Desconocido'
        cliente_id = partner_tuple[0] if (partner_tuple and isinstance(partner_tuple, (list, tuple))) else None

        if excluir_interempresa:
            c_norm = normalizar_texto(cliente_nom)
            if any(ex in c_norm for ex in CLIENTES_INTEREMPRESA):
                continue

        f_fact_str = inv.get('invoice_date') or ''
        f_venc_str = inv.get('invoice_date_due') or f_fact_str
        if not f_venc_str:
            continue

        try:
            dt_v = datetime.strptime(f_venc_str[:10], '%Y-%m-%d').date()
            m_v_key = dt_v.strftime('%Y-%m')
            m_v_label = f"{meses_nombres_es.get(dt_v.month, '')} {dt_v.year}"
            y_v_num = dt_v.year
            m_v_num = dt_v.month
        except Exception:
            continue

        is_refund = inv.get('move_type') == 'out_refund'
        total_raw = float(inv.get('amount_total', 0) or 0)
        saldo_raw = float(inv.get('amount_residual', 0) or 0)
        total = -abs(total_raw) if is_refund else total_raw
        saldo = -abs(saldo_raw) if is_refund else saldo_raw
        abonado = max(0.0, total - saldo)

        # Resolve salesperson
        v_val_cli = partner_vendor_map.get(cliente_id)
        vendedor_tuple = inv.get('invoice_user_id')
        vend_nom = 'Sin Asignar'
        if v_val_cli and v_val_cli in vendedores_oficiales_map:
            vend_nom = vendedores_oficiales_map[v_val_cli]
        elif vendedor_tuple and isinstance(vendedor_tuple, (list, tuple)):
            raw_v_nom = vendedor_tuple[1]
            norm_v = normalizar_texto(raw_v_nom)
            if norm_v not in NO_VENDEDORES_SISTEMA:
                for v_k, v_n in vendedores_oficiales_map.items():
                    if normalizar_texto(v_n) == norm_v or normalizar_texto(v_k) == norm_v:
                        vend_nom = v_n
                        break
                if vend_nom in ('Sin Asignar', 'Sin Vendedor Asignado', '') and norm_v not in NO_VENDEDORES_SISTEMA:
                    vend_nom = raw_v_nom
        if vend_nom in ('Sin Asignar', 'Sin Vendedor Asignado', ''):
            if cliente_id in partner_user_map:
                u_tup = partner_user_map[cliente_id]
                if u_tup and isinstance(u_tup, (list, tuple)):
                    if normalizar_texto(u_tup[1]) not in NO_VENDEDORES_SISTEMA:
                        vend_nom = u_tup[1]

        if normalizar_texto(vend_nom) in NO_VENDEDORES_SISTEMA:
            vend_nom = 'Sin Asignar'

        # Filtrar por vendedor si se especificó en el filtro
        if vendedor_valor and str(vendedor_valor).upper() != 'TODOS':
            match_v_val = (v_val_cli and str(v_val_cli) == str(vendedor_valor))
            match_v_nom = (vendedor_nombre and str(vendedor_nombre).upper() != 'TODOS' and (normalizar_texto(vendedor_nombre) in normalizar_texto(vend_nom) or normalizar_texto(vend_nom) in normalizar_texto(vendedor_nombre))) or (str(vendedor_valor).lower() in normalizar_texto(vend_nom))
            if not match_v_val and not match_v_nom:
                continue

        c_info = partner_contacts_map.get(cliente_id, {})
        rfc = c_info.get('vat', '')
        tel = c_info.get('phone', '')
        mail = c_info.get('email', '')

        if m_v_key not in vencimiento_meses_dict:
            vencimiento_meses_dict[m_v_key] = {
                'mes_key': m_v_key,
                'mes_nombre': m_v_label,
                'anio': y_v_num,
                'mes_num': m_v_num,
                'cobranza_estimada_vence': 0.0,
                'cobrado_de_vencidas': 0.0,
                'saldo_pendiente_vencidas': 0.0,
                'facturas_vencen_count': 0,
                'facturas_vencen': [],
                'clientes_map': {}
            }

        vm = vencimiento_meses_dict[m_v_key]
        vm['cobranza_estimada_vence'] += total
        vm['cobrado_de_vencidas'] += abonado
        vm['saldo_pendiente_vencidas'] += saldo
        vm['facturas_vencen_count'] += 1

        dias_retraso = 0
        if saldo > 0.01 and hoy > dt_v:
            dias_retraso = (hoy - dt_v).days

        est_fact = 'PAGADA' if saldo <= 0.01 else ('PARCIAL' if abonado > 0 else ('ATRASADA' if dias_retraso > 0 else 'POR_VENCER'))

        f_obj = {
            'id': inv['id'],
            'folio': inv.get('name') or f"INV-{inv['id']}",
            'cliente': cliente_nom,
            'cliente_id': cliente_id,
            'rfc': rfc,
            'telefono': tel,
            'email': mail,
            'vendedor': vend_nom,
            'fecha_emision': f_fact_str,
            'fecha_vencimiento': f_venc_str,
            'dias_retraso': dias_retraso,
            'total_factura': round(total, 2),
            'monto_abonado': round(abonado, 2),
            'saldo_pendiente': round(saldo, 2),
            'estatus_pago': est_fact
        }
        vm['facturas_vencen'].append(f_obj)

        if cliente_id not in vm['clientes_map']:
            saldo_act = clientes_agrupados.get(f"{cliente_id}_{cliente_nom}", {}).get('saldo_total', saldo)
            vm['clientes_map'][cliente_id] = {
                'cliente_id': cliente_id,
                'cliente_nombre': cliente_nom,
                'rfc': rfc,
                'vendedor': vend_nom,
                'telefono': tel,
                'email': mail,
                'total_estimado_vence': 0.0,
                'total_cobrado_vencidas': 0.0,
                'saldo_pendiente_vencidas': 0.0,
                'num_facturas_vence': 0,
                'saldo_actual_cliente': round(saldo_act, 2),
                'facturas': []
            }

        cv = vm['clientes_map'][cliente_id]
        cv['total_estimado_vence'] += total
        cv['total_cobrado_vencidas'] += abonado
        cv['saldo_pendiente_vencidas'] += saldo
        cv['num_facturas_vence'] += 1
        cv['facturas'].append(f_obj)

    # ── CONSOLIDAR MATRIZ MENSUAL (VENCIMIENTO + COBROS REALES + EMISIÓN) ─────
    all_months_keys = sorted(list(set(
        list(vencimiento_meses_dict.keys()) +
        list(pagos_por_mes_dict.keys()) +
        list(ciclos_mensuales.keys())
    )), reverse=True)

    cobrado_meses_lista = []

    for m_k in all_months_keys:
        v_data = vencimiento_meses_dict.get(m_k, {})
        p_data = pagos_por_mes_dict.get(m_k, {})
        i_data = ciclos_mensuales.get(m_k, {})

        try:
            y_n = int(m_k.split('-')[0])
            m_n = int(m_k.split('-')[1])
            m_nom = f"{meses_nombres_es.get(m_n, '')} {y_n}"
        except Exception:
            y_n, m_n, m_nom = 2026, 1, m_k

        est_vence = float(v_data.get('cobranza_estimada_vence', 0.0))
        cob_venc = float(v_data.get('cobrado_de_vencidas', 0.0))
        pend_venc = float(v_data.get('saldo_pendiente_vencidas', 0.0))
        n_facs_venc = int(v_data.get('facturas_vencen_count', 0))
        facs_venc_list = v_data.get('facturas_vencen', [])

        cob_real = float(p_data.get('total_cobrado', 0.0))
        n_pagos = int(p_data.get('num_pagos', 0))
        pagos_list = p_data.get('pagos', [])

        tot_fact_emi = float(i_data.get('total_vendido', 0.0))
        facs_emi_cnt = int(i_data.get('facturas_count', 0))

        pct_cumpl_venc = (cob_venc / est_vence * 100.0) if est_vence > 0 else (100.0 if pend_venc <= 0 and est_vence > 0 else 0.0)

        # Consolidar clientes de este mes
        clientes_mes_map = {}
        for cid, c_val in v_data.get('clientes_map', {}).items():
            if cid not in clientes_mes_map:
                clientes_mes_map[cid] = {
                    'cliente_id': cid,
                    'cliente_nombre': c_val['cliente_nombre'],
                    'rfc': c_val['rfc'],
                    'vendedor': c_val['vendedor'],
                    'telefono': c_val['telefono'],
                    'email': c_val['email'],
                    'total_estimado_vence': round(c_val['total_estimado_vence'], 2),
                    'total_cobrado_vencidas': round(c_val['total_cobrado_vencidas'], 2),
                    'saldo_pendiente_vencidas': round(c_val['saldo_pendiente_vencidas'], 2),
                    'num_facturas_vence': c_val['num_facturas_vence'],
                    'total_cobrado_real': 0.0,
                    'num_pagos_real': 0,
                    'saldo_actual_cliente': c_val['saldo_actual_cliente'],
                    'facturas': c_val['facturas'],
                    'pagos': []
                }

        for cid, p_c_val in p_data.get('clientes_map', {}).items():
            if cid not in clientes_mes_map:
                clientes_mes_map[cid] = {
                    'cliente_id': cid,
                    'cliente_nombre': p_c_val['cliente_nombre'],
                    'rfc': p_c_val['rfc'],
                    'vendedor': p_c_val['vendedor'],
                    'telefono': p_c_val['telefono'],
                    'email': p_c_val['email'],
                    'total_estimado_vence': 0.0,
                    'total_cobrado_vencidas': 0.0,
                    'saldo_pendiente_vencidas': 0.0,
                    'num_facturas_vence': 0,
                    'total_cobrado_real': round(p_c_val['total_cobrado'], 2),
                    'num_pagos_real': p_c_val['num_pagos'],
                    'saldo_actual_cliente': p_c_val['saldo_actual_cliente'],
                    'facturas': [],
                    'pagos': p_c_val['pagos']
                }
            else:
                clientes_mes_map[cid]['total_cobrado_real'] = round(p_c_val['total_cobrado'], 2)
                clientes_mes_map[cid]['num_pagos_real'] = p_c_val['num_pagos']
                clientes_mes_map[cid]['pagos'] = p_c_val['pagos']

        clis_list = sorted(list(clientes_mes_map.values()), key=lambda x: (x['total_estimado_vence'], x['total_cobrado_real']), reverse=True)

        cobrado_meses_lista.append({
            'mes_key': m_k,
            'mes_nombre': m_nom,
            'anio': y_n,
            'mes_num': m_n,
            # Estimación por Vencimiento
            'cobranza_estimada_vence': round(est_vence, 2),
            'cobrado_de_vencidas': round(cob_venc, 2),
            'saldo_pendiente_vencidas': round(pend_venc, 2),
            'pct_cumplimiento_vence': round(pct_cumpl_venc, 1),
            'facturas_vencen_count': n_facs_venc,
            'facturas_vencen': facs_venc_list,
            # Cobranza Real Recibida (Pagos del Mes)
            'cobrado_real_pagos': round(cob_real, 2),
            'total_cobrado': round(cob_real, 2),
            'num_pagos': n_pagos,
            'num_pagos_recibidos': n_pagos,
            'pagos_recibidos': pagos_list,
            # Emisión en el Mes
            'total_facturado': round(tot_fact_emi, 2),
            'facturado_emitido': round(tot_fact_emi, 2),
            'saldo_pendiente': round(pend_venc, 2),
            'facturas_count': facs_emi_cnt,
            # Clientes del Mes
            'num_clientes': len(clis_list),
            'clientes': clis_list
        })

    resumen_global_cobrado = {
        'total_estimado_vence_historico': round(sum(m['cobranza_estimada_vence'] for m in cobrado_meses_lista), 2),
        'total_cobrado_vencidas_historico': round(sum(m['cobrado_de_vencidas'] for m in cobrado_meses_lista), 2),
        'total_saldo_vencidas_historico': round(sum(m['saldo_pendiente_vencidas'] for m in cobrado_meses_lista), 2),
        'total_cobrado_real_historico': round(sum(m['cobrado_real_pagos'] for m in cobrado_meses_lista), 2),
        'total_num_pagos_historico': sum(m['num_pagos_recibidos'] for m in cobrado_meses_lista),
        'total_facturado_historico': round(sum(m['facturado_emitido'] for m in cobrado_meses_lista), 2),
        'total_facturas_vencen_historico': sum(m['facturas_vencen_count'] for m in cobrado_meses_lista),
        'meses_disponibles': [{'key': m['mes_key'], 'nombre': m['mes_nombre']} for m in cobrado_meses_lista]
    }

    res_final = {
        'cuentas': cuentas,
        'clientes_cartera': clientes_lista,
        'ciclos_recuperacion': {
            'meses': ciclos_lista,
            'resumen_global': resumen_global_ciclos
        },
        'cobrado_por_mes': {
            'meses': cobrado_meses_lista,
            'resumen_global': resumen_global_cobrado
        },
        'cobranza_estimada_mes': {
            'meses': cobrado_meses_lista,
            'resumen_global': resumen_global_cobrado
        },
        'totales': {
            'saldo_total': round(tot_cartera, 2),
            'saldo_al_dia': round(tot_al_dia, 2),
            'saldo_reciente_0_60': round(tot_reciente_0_60, 2),
            'saldo_pasada_60_100': round(tot_pasada_60_100, 2),
            'saldo_atrasada_100_mas': round(tot_atrasada_100_mas, 2),
            'saldo_vencido': round(tot_reciente_0_60 + tot_pasada_60_100 + tot_atrasada_100_mas, 2),
            'saldo_moroso_90': round(tot_atrasada_100_mas, 2),
            'facturas_count': len(cuentas),
            'clientes_count': len(clientes_lista),
            'count_reciente_0_60': count_reciente_0_60,
            'count_pasada_60_100': count_pasada_60_100,
            'count_atrasada_100_mas': count_atrasada_100_mas,
            'count_al_dia': count_al_dia,
            'clientes_con_telefono': sum(1 for c in clientes_lista if c['telefono']),
            'clientes_con_email': sum(1 for c in clientes_lista if c['email']),
            'vendedores_detectados': vendedores_unicos,
            'vendedores_metricas': vend_metricas_list
        }
    }
    return res_final


def _filtrar_cartera_por_vendedor(res_full, vendedor_valor="TODOS", vendedor_nombre="TODOS"):
    if not vendedor_valor or str(vendedor_valor).upper() == "TODOS":
        return res_full

    v_val_str = str(vendedor_valor).lower()
    v_nom_norm = normalizar_texto(vendedor_nombre) if vendedor_nombre and str(vendedor_nombre).upper() != 'TODOS' else ''

    v_id_to_name = {}
    for vm in res_full.get('totales', {}).get('vendedores_metricas', []):
        if vm.get('vendedor_id') and vm.get('vendedor'):
            v_id_to_name[str(vm['vendedor_id'])] = normalizar_texto(vm['vendedor'])

    target_name_norm = v_nom_norm or v_id_to_name.get(str(vendedor_valor), '')

    def matches_vend(item_v_val, item_v_nom):
        if item_v_val and str(item_v_val) == str(vendedor_valor):
            return True
        norm_item_nom = normalizar_texto(item_v_nom)
        if target_name_norm and (target_name_norm in norm_item_nom or norm_item_nom in target_name_norm):
            return True
        if v_val_str and v_val_str != 'todos' and (v_val_str == str(item_v_val).lower() or v_val_str in norm_item_nom):
            return True
        return False

    filtered_cuentas = [c for c in res_full.get('cuentas', []) if matches_vend(c.get('vendedor_id'), c.get('vendedor', ''))]
    filtered_clientes = [c for c in res_full.get('clientes_cartera', []) if matches_vend(c.get('vendedor_id'), c.get('vendedor', ''))]

    # Filter cobrado_por_mes
    cpm_orig = res_full.get('cobrado_por_mes', {})
    filtered_meses = []
    for m in cpm_orig.get('meses', []):
        m_copy = dict(m)
        m_facs = [f for f in m.get('facturas_vencen', []) if matches_vend(f.get('vendedor_id', ''), f.get('vendedor', ''))]
        m_pagos = [p for p in m.get('pagos_recibidos', []) if matches_vend(p.get('vendedor_id', ''), p.get('vendedor', ''))]
        m_clis = [c for c in m.get('clientes', []) if matches_vend(c.get('vendedor_id', ''), c.get('vendedor', '')) or any(matches_vend('', p.get('vendedor', '')) for p in c.get('pagos', []))]

        if not m_facs and not m_pagos and not m_clis:
            continue

        cob_venc = sum(f.get('monto_abonado', 0.0) for f in m_facs)
        est_vence = sum(f.get('total_factura', 0.0) for f in m_facs)
        pend_venc = sum(f.get('saldo_pendiente', 0.0) for f in m_facs)
        cob_real = sum(p.get('monto', 0.0) for p in m_pagos)

        m_copy['facturas_vencen'] = m_facs
        m_copy['facturas_vencen_count'] = len(m_facs)
        m_copy['pagos_recibidos'] = m_pagos
        m_copy['num_pagos_recibidos'] = len(m_pagos)
        m_copy['num_pagos'] = len(m_pagos)
        m_copy['cobranza_estimada_vence'] = round(est_vence, 2)
        m_copy['cobrado_de_vencidas'] = round(cob_venc, 2)
        m_copy['saldo_pendiente_vencidas'] = round(pend_venc, 2)
        m_copy['cobrado_real_pagos'] = round(cob_real, 2)
        m_copy['total_cobrado'] = round(cob_real, 2)
        m_copy['clientes'] = m_clis
        m_copy['num_clientes'] = len(m_clis)
        filtered_meses.append(m_copy)

    rg_cobrado = {
        'total_estimado_vence_historico': round(sum(m['cobranza_estimada_vence'] for m in filtered_meses), 2),
        'total_cobrado_vencidas_historico': round(sum(m['cobrado_de_vencidas'] for m in filtered_meses), 2),
        'total_saldo_vencidas_historico': round(sum(m['saldo_pendiente_vencidas'] for m in filtered_meses), 2),
        'total_cobrado_real_historico': round(sum(m['cobrado_real_pagos'] for m in filtered_meses), 2),
        'total_num_pagos_historico': sum(m['num_pagos_recibidos'] for m in filtered_meses),
        'total_facturado_historico': round(sum(m.get('facturado_emitido', 0.0) for m in filtered_meses), 2),
        'total_facturas_vencen_historico': sum(m['facturas_vencen_count'] for m in filtered_meses),
        'meses_disponibles': [{'key': m['mes_key'], 'nombre': m['mes_nombre']} for m in filtered_meses]
    }

    # Recalculate totals
    tot_cart = sum(c.get('saldo_pendiente', 0.0) for c in filtered_cuentas)
    tot_al_dia = sum(c.get('saldo_pendiente', 0.0) for c in filtered_cuentas if c.get('dias_retraso', 0) <= 0)
    tot_0_60 = sum(c.get('saldo_pendiente', 0.0) for c in filtered_cuentas if 0 < c.get('dias_retraso', 0) <= 60)
    tot_60_100 = sum(c.get('saldo_pendiente', 0.0) for c in filtered_cuentas if 60 < c.get('dias_retraso', 0) <= 100)
    tot_100_mas = sum(c.get('saldo_pendiente', 0.0) for c in filtered_cuentas if c.get('dias_retraso', 0) > 100)

    totales = dict(res_full.get('totales', {}))
    totales.update({
        'saldo_total': round(tot_cart, 2),
        'saldo_al_dia': round(tot_al_dia, 2),
        'saldo_reciente_0_60': round(tot_0_60, 2),
        'saldo_pasada_60_100': round(tot_60_100, 2),
        'saldo_atrasada_100_mas': round(tot_100_mas, 2),
        'saldo_vencido': round(tot_0_60 + tot_60_100 + tot_100_mas, 2),
        'saldo_moroso_90': round(tot_100_mas, 2),
        'facturas_count': len(filtered_cuentas),
        'clientes_count': len(filtered_clientes),
    })

    return {
        'cuentas': filtered_cuentas,
        'clientes_cartera': filtered_clientes,
        'ciclos_recuperacion': res_full.get('ciclos_recuperacion', {}),
        'cobrado_por_mes': {
            'meses': filtered_meses,
            'resumen_global': rg_cobrado
        },
        'cobranza_estimada_mes': {
            'meses': filtered_meses,
            'resumen_global': rg_cobrado
        },
        'totales': totales
    }


def obtener_cartera_cobranza_engine(empresa_nombre="TODAS (Consolidado)", vendedor_valor="TODOS", vendedor_nombre="TODOS", excluir_interempresa=True, force_reload=False):
    cache_key = f"{empresa_nombre}_{vendedor_valor}_{vendedor_nombre}_{excluir_interempresa}"
    now_t = time.time()
    if not force_reload and cache_key in _COBRANZA_MEM_CACHE:
        if (now_t - _COBRANZA_MEM_TIME.get(cache_key, 0)) < 180:
            return _COBRANZA_MEM_CACHE[cache_key]

    try:
        res = _obtener_cartera_cobranza_engine_impl(empresa_nombre, vendedor_valor, vendedor_nombre, excluir_interempresa)
        _COBRANZA_MEM_CACHE[cache_key] = res
        _COBRANZA_MEM_TIME[cache_key] = time.time()

        if empresa_nombre == "TODAS (Consolidado)" and str(vendedor_valor).upper() == "TODOS":
            try:
                with open(COBRANZA_DISK_CACHE_FILE, "w", encoding="utf-8") as f_c:
                    json.dump(res, f_c, ensure_ascii=False)
            except Exception as e_w:
                print(f"[WARN error guardando cache cobranza disco]: {e_w}")

        return res
    except Exception as e_err:
        print(f"[ERROR Odoo Cartera]: {e_err}")
        if os.path.exists(COBRANZA_DISK_CACHE_FILE):
            try:
                with open(COBRANZA_DISK_CACHE_FILE, "r", encoding="utf-8") as f_c:
                    cached = json.load(f_c)
                print("[INFO] Cartera servida desde respaldo de disco local.")
                if vendedor_valor and str(vendedor_valor).upper() != "TODOS":
                    return _filtrar_cartera_por_vendedor(cached, vendedor_valor, vendedor_nombre)
                return cached
            except Exception as e_fallback:
                print(f"[ERROR Fallback disco]: {e_fallback}")
        raise

def format_fecha_mx(d_str):
    if not d_str: return "—"
    try:
        parts = str(d_str).split("-")
        if len(parts) == 3:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
    except Exception:
        pass
    return str(d_str)


def generar_tabla_facturas_html(facturas):
    """
    Genera una tabla HTML ejecutiva y responsiva con las facturas vencidas,
    fecha de vencimiento destacada, total, saldo y días de antigüedad.
    """
    if not facturas or not isinstance(facturas, list):
        return ""
    
    total_monto = sum(float(f.get("total_factura", 0) or 0) for f in facturas)
    total_saldo = sum(float(f.get("saldo_pendiente", 0) or 0) for f in facturas)
    
    rows_html = []
    for idx, f in enumerate(facturas):
        bg = "#ffffff" if idx % 2 == 0 else "#f8fafc"
        folio = f.get("folio") or f.get("name") or f.get("inv_id") or "FAC"
        f_emision = format_fecha_mx(f.get("fecha_factura"))
        f_venc = format_fecha_mx(f.get("fecha_vencimiento"))
        dias = int(f.get("dias_retraso", 0) or 0)
        monto_tot = float(f.get("total_factura", 0) or 0)
        saldo_pend = float(f.get("saldo_pendiente", 0) or 0)
        
        if dias > 100:
            badge_dias = f'<span style="background-color: #fee2e2; color: #b91c1c; padding: 2px 7px; border-radius: 4px; font-weight: 800; font-size: 11px; border: 1px solid #fca5a5;">{dias}d (Crítico)</span>'
        elif dias > 60:
            badge_dias = f'<span style="background-color: #fef3c7; color: #b45309; padding: 2px 7px; border-radius: 4px; font-weight: 700; font-size: 11px; border: 1px solid #fde68a;">{dias}d (Atrasada)</span>'
        elif dias > 0:
            badge_dias = f'<span style="background-color: #dcfce7; color: #15803d; padding: 2px 7px; border-radius: 4px; font-weight: 700; font-size: 11px; border: 1px solid #86efac;">{dias}d (Reciente)</span>'
        else:
            badge_dias = f'<span style="background-color: #f1f5f9; color: #475569; padding: 2px 7px; border-radius: 4px; font-weight: 600; font-size: 11px;">Al día</span>'
            
        rows_html.append(f"""
        <tr style="background-color: {bg}; border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 10px 10px; font-family: monospace; font-weight: 700; color: #0f172a; font-size: 12px;">{folio}</td>
          <td style="padding: 10px 10px; text-align: center; color: #475569; font-size: 12px;">{f_emision}</td>
          <td style="padding: 10px 10px; text-align: center; font-weight: 700; color: #b45309; font-size: 12px; background-color: #fffbeb;">{f_venc}</td>
          <td style="padding: 10px 10px; text-align: center;">{badge_dias}</td>
          <td style="padding: 10px 10px; text-align: right; color: #475569; font-family: monospace; font-size: 12px;">${monto_tot:,.2f}</td>
          <td style="padding: 10px 10px; text-align: right; font-weight: 800; color: #dc2626; font-family: monospace; font-size: 12px;">${saldo_pend:,.2f}</td>
        </tr>""")
        
    tabla_facturas = f"""
    <div style="margin: 22px 0 18px 0;">
      <h3 style="margin: 0 0 10px 0; font-size: 13px; font-weight: 800; color: #0f172a; text-transform: uppercase; letter-spacing: 0.5px; border-left: 4px solid #10b981; padding-left: 8px;">
        Desglose de Facturas y Fechas de Vencimiento
      </h3>
      <table cellpadding="0" cellspacing="0" border="0" width="100%" style="border-collapse: collapse; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; background-color: #ffffff; width: 100%;">
        <thead>
          <tr style="background-color: #0f172a; color: #ffffff;">
            <th style="padding: 10px 10px; text-align: left; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Factura</th>
            <th style="padding: 10px 10px; text-align: center; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Emisión</th>
            <th style="padding: 10px 10px; text-align: center; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #fbbf24;">Vencimiento</th>
            <th style="padding: 10px 10px; text-align: center; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Antigüedad</th>
            <th style="padding: 10px 10px; text-align: right; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Total Factura</th>
            <th style="padding: 10px 10px; text-align: right; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #34d399;">Saldo Pendiente</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows_html)}
        </tbody>
        <tfoot>
          <tr style="background-color: #f1f5f9; border-top: 2px solid #94a3b8;">
            <td colspan="4" style="padding: 12px 10px; text-align: right; font-weight: 800; color: #0f172a; font-size: 12px; text-transform: uppercase;">Total a Liquidar:</td>
            <td style="padding: 12px 10px; text-align: right; font-weight: 700; color: #475569; font-family: monospace; font-size: 12px;">${total_monto:,.2f}</td>
            <td style="padding: 12px 10px; text-align: right; font-weight: 900; color: #b91c1c; font-family: monospace; font-size: 13px;">${total_saldo:,.2f} MXN</td>
          </tr>
        </tfoot>
      </table>
    </div>"""
    return tabla_facturas


def enviar_correo_cobranza_odoo(cliente_id=None, cliente_nombre="Cliente", email_destinatario="", asunto="", cuerpo_texto="", empresa_nombre="Challenger Automotive", facturas=None):
    """
    Envía un correo oficial de cobranza registrado en Odoo ERP con diseño HTML profesional:
    1. Diseña la plantilla HTML limpia y compatible con clientes de correo (Gmail, Outlook, Apple Mail).
    2. Inserta tabla desglosada de facturas vencidas con fecha de vencimiento, monto y saldo pendiente.
    3. Crea y despacha inmediatamente el correo a través de mail.mail.send() en Odoo ERP.
    4. Registra una Nota Interna (mail.mt_note) en el Chatter del cliente en Odoo para auditoría sin escapar etiquetas.
    """
    if not email_destinatario or "@" not in email_destinatario:
        raise Exception(f"El cliente '{cliente_nombre}' no tiene un correo electrónico válido registrado.")
    
    uid, models = conectar_odoo(1)
    
    # Formatear párrafos limpios
    lineas_html = "".join([f"<p style='margin: 0 0 12px 0; line-height: 1.6; color: #334155; font-size: 14px;'>{l.strip()}</p>" for l in (cuerpo_texto or "").split("\n") if l.strip()])
    
    # Formatear tabla de facturas si fue proporcionada
    tabla_facturas_html = generar_tabla_facturas_html(facturas)
    
    body_html = f"""<table cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: #f1f5f9; padding: 24px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <tr>
    <td align="center">
      <table cellpadding="0" cellspacing="0" border="0" width="650" style="max-width: 650px; width: 100%; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
        <!-- Header -->
        <tr>
          <td style="background-color: #0f172a; padding: 26px 30px; border-bottom: 4px solid #10b981;">
            <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase;">{empresa_nombre}</h1>
            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 12px; font-weight: 500;">Departamento de Crédito, Cartera y Cobranza</p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding: 30px 30px 20px 30px;">
            {lineas_html}
            {tabla_facturas_html}
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background-color: #f8fafc; padding: 18px 30px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 11px; line-height: 1.5;">
            <p style="margin: 0; font-weight: 600; color: #475569;">{empresa_nombre} &bull; Challenger Automotive</p>
            <p style="margin: 4px 0 0 0;">Notificación oficial emitida a través de Odoo ERP. Si ya realizó su pago o requiere alguna aclaración, puede responder directamente a este correo.</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>"""
    
    # 1. Crear el correo en mail.mail con body_html renderizable
    mail_vals = {
        'subject': asunto,
        'email_to': email_destinatario,
        'body_html': body_html,
        'state': 'outgoing',
        'auto_delete': False
    }
    
    mail_id = models.execute_kw(ODOO_DB, uid, ODOO_API_KEY, 'mail.mail', 'create', [mail_vals])
    
    # 2. Despachar el correo inmediatamente por Odoo
    try:
        models.execute_kw(ODOO_DB, uid, ODOO_API_KEY, 'mail.mail', 'send', [[mail_id]])
    except Exception as e_send:
        # En Odoo 19 el controlador XML-RPC genera una excepción de serialización con el retorno None de send(), pero el envío se completa con éxito.
        pass
        
    # 3. Registrar nota interna en el historial del cliente (chatter) sin disparar alertas escapadas
    if cliente_id:
        try:
            resumen_facs = ""
            if facturas:
                resumen_facs = "<br/><b>Facturas:</b> " + ", ".join([f"{f.get('folio')} (Vence: {f.get('fecha_vencimiento')}, Saldo: ${float(f.get('saldo_pendiente',0)):,.2f})" for f in facturas[:8]])
            note_content = f"<p><b>Notificación de Cobranza Enviada por Correo:</b></p><p>{(cuerpo_texto or '').replace(chr(10), '<br/>')}{resumen_facs}</p>"
            models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'res.partner', 'message_post',
                [[cliente_id]],
                {
                    'body': note_content,
                    'message_type': 'notification',
                    'subtype_xmlid': 'mail.mt_note'
                }
            )
        except Exception as e_note:
            print(f"[WARN chatter note]: {e_note}")
            
    return {
        "success": True,
        "message_id": mail_id,
        "email_to": email_destinatario,
        "cliente": cliente_nombre
    }


def obtener_historial_compras_cliente_engine(cliente_id=None, cliente_nombre="", empresa_nombre="TODAS (Consolidado)"):
    """
    Obtiene el historial completo de compras, facturas, productos desglosados y pagos de un cliente en Odoo ERP:
    - Retorna todas las facturas históricas (pagadas, parciales, impagadas, notas de crédito y canceladas).
    - Desglosa qué productos se vendieron en cada factura (SKU, nombre, cantidad, unidad, precio unitario, subtotal, total con IVA).
    - Extrae el historial de pagos y abonos registrados (fecha de pago, importe, método de pago, referencia).
    - Provee métricas agregadas (Total comprado, total pagado, saldo deudor, porcentaje cubierto y ticket promedio).
    """
    empresa_cfg = EMPRESAS.get(empresa_nombre)
    company_id = empresa_cfg["company_id"] if empresa_cfg else None
    uid, models = conectar_odoo(company_id or 1)
    
    partner_info = {}
    p_ids = []
    
    if cliente_id:
        try:
            cid = int(cliente_id)
            partners = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'res.partner', 'search_read',
                [[('id', '=', cid)]],
                {'fields': ['id', 'name', 'commercial_partner_id', 'vat', 'phone', 'phone_sanitized', 'email', 'city', 'contact_address_inline', 'user_id']}
            )
            if partners:
                p = partners[0]
                partner_info = p
                p_ids = [p['id']]
                comm_tuple = p.get('commercial_partner_id')
                if comm_tuple and isinstance(comm_tuple, (list, tuple)):
                    p_ids.append(comm_tuple[0])
        except Exception as e:
            print(f"[WARN search by id]: {e}")
            
    if not p_ids and cliente_nombre:
        partners = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner', 'search_read',
            [[('name', 'ilike', cliente_nombre.strip())]],
            {'fields': ['id', 'name', 'commercial_partner_id', 'vat', 'phone', 'phone_sanitized', 'email', 'city', 'contact_address_inline', 'user_id'], 'limit': 5}
        )
        if partners:
            p = partners[0]
            partner_info = p
            p_ids = [p['id']]
            comm_tuple = p.get('commercial_partner_id')
            if comm_tuple and isinstance(comm_tuple, (list, tuple)):
                p_ids.append(comm_tuple[0])
                
    p_ids = list(set(p_ids))
    if not p_ids:
        return {
            "success": False,
            "error": f"No se encontró información del cliente '{cliente_nombre or cliente_id}' en Odoo."
        }
        
    domain = [
        ('move_type', 'in', ['out_invoice', 'out_refund']),
        ('state', 'in', ['posted', 'draft', 'cancel']),
        '|', ('partner_id', 'in', p_ids), ('commercial_partner_id', 'in', p_ids)
    ]
    if company_id:
        domain.append(('company_id', '=', company_id))
        
    fields = [
        'id', 'name', 'invoice_date', 'invoice_date_due', 'amount_total', 'amount_untaxed',
        'amount_residual', 'payment_state', 'state', 'move_type', 'invoice_user_id',
        'invoice_line_ids', 'invoice_payments_widget', 'company_id', 'currency_id'
    ]
    
    invs = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'account.move', 'search_read', [domain],
        {'fields': fields, 'order': 'invoice_date desc, id desc', 'limit': 400}
    )
    
    # Batch query line items
    all_line_ids = []
    for inv in invs:
        all_line_ids.extend(inv.get('invoice_line_ids') or [])
        
    lines_map = {}
    if all_line_ids:
        CHUNK_L = 400
        for i in range(0, len(all_line_ids), CHUNK_L):
            b_lids = all_line_ids[i:i+CHUNK_L]
            try:
                line_records = models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    'account.move.line', 'search_read',
                    [[('id', 'in', b_lids), ('display_type', '=', 'product')]],
                    {'fields': ['move_id', 'product_id', 'name', 'quantity', 'product_uom_id', 'price_unit', 'price_subtotal', 'price_total', 'discount']}
                )
                for l in line_records:
                    m_tuple = l.get('move_id')
                    m_id = m_tuple[0] if (m_tuple and isinstance(m_tuple, (list, tuple))) else m_tuple
                    if m_id not in lines_map:
                        lines_map[m_id] = []
                    
                    p_nom = l.get('name') or ''
                    sku = ''
                    if '[' in p_nom and ']' in p_nom:
                        sku = p_nom[p_nom.find('[')+1 : p_nom.find(']')]
                    elif l.get('product_id') and isinstance(l['product_id'], (list, tuple)):
                        prod_full = l['product_id'][1]
                        if '[' in prod_full and ']' in prod_full:
                            sku = prod_full[prod_full.find('[')+1 : prod_full.find(']')]
                            
                    uom_tuple = l.get('product_uom_id')
                    uom = uom_tuple[1] if (uom_tuple and isinstance(uom_tuple, (list, tuple))) else 'Pz'
                    
                    lines_map[m_id].append({
                        'id': l.get('id'),
                        'sku': sku,
                        'producto': p_nom,
                        'cantidad': float(l.get('quantity', 0) or 0),
                        'uom': uom,
                        'precio_unit': float(l.get('price_unit', 0) or 0),
                        'descuento': float(l.get('discount', 0) or 0),
                        'subtotal': float(l.get('price_subtotal', 0) or 0),
                        'total': float(l.get('price_total', l.get('price_subtotal', 0)) or 0)
                    })
            except Exception as e_l:
                print(f"[WARN lines chunk]: {e_l}")

    hoy = date.today()
    facturas_procesadas = []
    
    tot_comprado = 0.0
    tot_pagado = 0.0
    tot_saldo = 0.0
    count_pagadas = 0
    count_pendientes = 0
    count_canceladas = 0
    
    for inv in invs:
        inv_id = inv.get('id')
        is_refund = inv.get('move_type') == 'out_refund'
        state = inv.get('state') or 'posted'
        payment_state = inv.get('payment_state') or 'not_paid'
        
        tot_raw = float(inv.get('amount_total', 0) or 0)
        untax_raw = float(inv.get('amount_untaxed', 0) or 0)
        res_raw = float(inv.get('amount_residual', 0) or 0)
        
        total = -abs(tot_raw) if is_refund else tot_raw
        subtotal = -abs(untax_raw) if is_refund else untax_raw
        saldo = -abs(res_raw) if is_refund else res_raw
        
        if state == 'cancel':
            estatus_pago = 'CANCELADA'
            monto_pagado = 0.0
            saldo = 0.0
            count_canceladas += 1
        else:
            if saldo <= 0.01 or payment_state in ['paid', 'in_payment']:
                estatus_pago = 'PAGADA'
                monto_pagado = total
                saldo = 0.0
                count_pagadas += 1
            elif (total - saldo) > 0.01:
                estatus_pago = 'PARCIAL'
                monto_pagado = total - saldo
                count_pendientes += 1
            else:
                estatus_pago = 'PENDIENTE'
                monto_pagado = 0.0
                count_pendientes += 1
                
            tot_comprado += total
            tot_pagado += monto_pagado
            tot_saldo += saldo

        pct_cubierto = (monto_pagado / total * 100.0) if total > 0 else (100.0 if saldo == 0 else 0.0)
        
        f_emision = inv.get('invoice_date') or ''
        f_vence = inv.get('invoice_date_due') or f_emision
        
        dias_retraso = 0
        dias_credito = 0
        if f_emision and f_vence:
            try:
                dt_emision = datetime.strptime(f_emision, '%Y-%m-%d').date()
                dt_vence = datetime.strptime(f_vence, '%Y-%m-%d').date()
                dias_credito = (dt_vence - dt_emision).days
                if saldo > 0.01 and hoy > dt_vence:
                    dias_retraso = (hoy - dt_vence).days
            except Exception:
                pass
                
        # Parse payments widget
        pagos_lista = []
        p_widget = inv.get('invoice_payments_widget')
        if p_widget and isinstance(p_widget, dict) and p_widget.get('content'):
            for p_item in p_widget['content']:
                pagos_lista.append({
                    'fecha': p_item.get('date') or '',
                    'monto': float(p_item.get('amount', 0) or 0),
                    'metodo': p_item.get('pos_payment_name') or p_item.get('journal_name') or 'Pago Registrado',
                    'referencia': p_item.get('ref') or '',
                    'moneda': p_item.get('amount_company_currency') or ''
                })
        elif isinstance(p_widget, str) and p_widget:
            try:
                import json
                pw_data = json.loads(p_widget)
                for p_item in pw_data.get('content', []):
                    pagos_lista.append({
                        'fecha': p_item.get('date') or '',
                        'monto': float(p_item.get('amount', 0) or 0),
                        'metodo': p_item.get('pos_payment_name') or p_item.get('journal_name') or 'Pago Registrado',
                        'referencia': p_item.get('ref') or '',
                        'moneda': p_item.get('amount_company_currency') or ''
                    })
            except Exception:
                pass

        vendedor_nom = inv.get('invoice_user_id')[1] if (inv.get('invoice_user_id') and isinstance(inv['invoice_user_id'], (list, tuple))) else 'Sin Vendedor'
        
        facturas_procesadas.append({
            'id': inv_id,
            'folio': inv.get('name') or f"INV-{inv_id}",
            'tipo': 'Nota de Crédito' if is_refund else 'Factura de Venta',
            'move_type': inv.get('move_type'),
            'fecha_emision': f_emision,
            'fecha_vencimiento': f_vence,
            'dias_credito': max(0, dias_credito),
            'dias_retraso': max(0, dias_retraso),
            'estatus_pago': estatus_pago,
            'payment_state': payment_state,
            'state': state,
            'vendedor': vendedor_nom,
            'subtotal': subtotal,
            'total': total,
            'monto_pagado': monto_pagado,
            'saldo_pendiente': saldo,
            'pct_cubierto': round(pct_cubierto, 1),
            'pagos': pagos_lista,
            'productos': lines_map.get(inv_id, [])
        })

    v_user = partner_info.get('user_id')
    vendedor_def = v_user[1] if (v_user and isinstance(v_user, (list, tuple))) else 'Sin Asignar'
    tel = partner_info.get('phone_sanitized') or partner_info.get('phone') or ''
    
    resultado = {
        "success": True,
        "cliente_id": partner_info.get('id'),
        "cliente_nombre": partner_info.get('name') or cliente_nombre,
        "rfc": partner_info.get('vat') or 'SIN RFC',
        "telefono": str(tel).strip() if tel else 'Sin teléfono',
        "email": partner_info.get('email') or 'Sin correo',
        "ciudad": partner_info.get('city') or '',
        "direccion": partner_info.get('contact_address_inline') or '',
        "vendedor": vendedor_def,
        "kpis": {
            "total_comprado": tot_comprado,
            "total_pagado": tot_pagado,
            "total_saldo_pendiente": tot_saldo,
            "pct_cumplimiento": round((tot_pagado / tot_comprado * 100.0), 1) if tot_comprado > 0 else 100.0,
            "total_facturas": len(facturas_procesadas),
            "facturas_pagadas": count_pagadas,
            "facturas_pendientes": count_pendientes,
            "facturas_canceladas": count_canceladas,
            "ticket_promedio": (tot_comprado / len(facturas_procesadas)) if facturas_procesadas else 0.0
        },
        "facturas": facturas_procesadas
    }
    return resultado


class BackgroundCronSyncEngine:
    def __init__(self, interval_seconds=600):
        self.interval = interval_seconds
        self.running = False
        self.last_sync_time = None
        self.sync_status = "Esperando inicialización..."
        self.cache_data = self._cargar_cache_disco()
        self.lock = threading.Lock()

    def _cargar_cache_disco(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_sync_time = data.get("last_sync_time")
                    self.sync_status = "Caché cargado desde disco."
                    return data
            except Exception:
                pass
        return {"vendedores": [], "stock": {}, "productos": {}, "comisiones": {}}

    def _guardar_cache_disco(self):
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cache_data, f, ensure_ascii=False, indent=2)

    def iniciar(self):
        if not self.running:
            self.running = True
            thread = threading.Thread(target=self._bucle_sync, daemon=True)
            thread.start()

    def _bucle_sync(self):
        while self.running:
            try:
                self.sincronizar_todo()
            except Exception as e:
                with self.lock:
                    self.sync_status = f"Error en Auto-Sync: {e}"
            time.sleep(self.interval)

    def sincronizar_todo(self):
        with self.lock:
            self.sync_status = "🔄 Sincronizando datos con Odoo 19..."

        t0 = time.time()
        try:
            vends = obtener_vendedores_odoo(company_id=1)
            stock_res = obtener_stock_engine(company_id=None, almacen_filtro="Todos los Almacenes", dias_analisis=30)

            anio_act = datetime.now().year
            mes_act = datetime.now().month
            _, max_d = calendar.monthrange(anio_act, mes_act)
            prods_res = obtener_productos_engine(f"{anio_act}-{mes_act:02d}-01", f"{anio_act}-{mes_act:02d}-{max_d:02d}")

            with self.lock:
                self.cache_data["vendedores"] = vends
                self.cache_data["stock"]["default"] = stock_res
                self.cache_data["productos"]["default"] = prods_res
                self.last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cache_data["last_sync_time"] = self.last_sync_time
                self.sync_status = f"✓ Sincronizado ({int(time.time() - t0)}s) — {datetime.now().strftime('%H:%M:%S')}"
                self._guardar_cache_disco()

            return True
        except Exception as e:
            with self.lock:
                self.sync_status = f"⚠️ Fallo al sincronizar: {e}"
            raise e

    def get_status(self):
        with self.lock:
            return {
                "status": self.sync_status,
                "last_sync": self.last_sync_time,
                "interval_min": self.interval // 60
            }


CRON_ENGINE = BackgroundCronSyncEngine(interval_seconds=600)
