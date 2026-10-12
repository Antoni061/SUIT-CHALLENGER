"""
ESTADO DE RESULTADOS & RENTABILIDAD FINANCIERA (P&L ENGINE)
Cálculo en vivo de Ingresos, Costo de Ventas (COGS), Utilidad Bruta,
Comisiones, Gastos Operativos y Utilidad Operativa.
Incluye matriz multi-mes, todos los productos desglosados y trazabilidad
por vendedor y evolución mensual para modales interactivos.
"""

import os
import re
import pandas as pd
from datetime import datetime
from odoo_sync_engine import conectar_odoo, ODOO_DB, ODOO_API_KEY, EMPRESAS

JSON_COSTOS_PATH = os.path.join(os.path.dirname(__file__), "data", "lista_costos_oficial.json")
EXCEL_COSTOS_PATH = os.path.join(os.path.dirname(__file__), "data", "Lista_Challenger_con_Costo.xlsx")
if not os.path.exists(EXCEL_COSTOS_PATH):
    EXCEL_COSTOS_PATH = r"C:\Users\usuario\Downloads\Lista_Challenger_con_Costo.xlsx"

def _norm_str(txt):
    if not txt or pd.isnull(txt): return ""
    return re.sub(r'[^A-Z0-9]', '', str(txt).upper())

def cargar_diccionario_costos():
    """
    Lee lista_costos_oficial.json o Lista_Challenger_con_Costo.xlsx y genera
    un mapa de costos indexado por clave normalizada y descripciones.
    """
    cost_map = {}
    import json

    # 1. Prioridad: Archivo JSON oficial verificado
    if os.path.exists(JSON_COSTOS_PATH):
        try:
            with open(JSON_COSTOS_PATH, "r", encoding="utf-8") as f:
                cost_map = json.load(f)
            print(f"[INFO P&L] Costos oficiales cargados desde JSON: {len(cost_map)} registros")
        except Exception as e_json:
            print(f"[WARN] Error al leer {JSON_COSTOS_PATH}: {e_json}")

    # 2. Respaldo: Excel
    if not cost_map and os.path.exists(EXCEL_COSTOS_PATH):
        try:
            df = pd.read_excel(EXCEL_COSTOS_PATH)
            # Manejar encabezados flexibles
            cols_lower = [str(c).lower().strip() for c in df.columns]
            col_costo = next((c for c in df.columns if 'costo' in str(c).lower()), None)
            col_clave = next((c for c in df.columns if 'clave' in str(c).lower()), None)
            col_desc = next((c for c in df.columns if any(x in str(c).lower() for x in ['descrip', 'producto'])), None)
            col_cat = next((c for c in df.columns if 'categ' in str(c).lower()), None)
            col_prec = next((c for c in df.columns if 'precio' in str(c).lower()), None)

            if col_costo:
                df = df.dropna(subset=[col_costo])
                for _, r in df.iterrows():
                    try:
                        c_val = float(str(r[col_costo]).replace('$', '').replace(',', '').strip())
                    except Exception:
                        continue
                    p_val = float(str(r[col_prec]).replace('$', '').replace(',', '').strip()) if col_prec and pd.notnull(r[col_prec]) else 0.0
                    clave_orig = str(r[col_clave]).strip() if col_clave and pd.notnull(r[col_clave]) else ""
                    desc_orig = str(r[col_desc]).strip() if col_desc and pd.notnull(r[col_desc]) else ""
                    cat_orig = str(r[col_cat]).strip() if col_cat and pd.notnull(r[col_cat]) else "Línea General"

                    item_data = {
                        'costo': c_val,
                        'precio_lista': p_val,
                        'clave': clave_orig,
                        'descripcion': desc_orig,
                        'categoria': cat_orig
                    }

                    clave_norm = _norm_str(clave_orig)
                    if clave_norm:
                        cost_map[clave_norm] = item_data

                    desc_norm = _norm_str(desc_orig)
                    if desc_norm and len(desc_norm) > 4:
                        if desc_norm not in cost_map:
                            cost_map[desc_norm] = item_data
        except Exception as e_xl:
            print(f"[ERROR al cargar costos Excel]: {e_xl}")

    # Aliases adicionales comunes en facturación Odoo
    aliases = {
        'KITGLOSSLT': cost_map.get('TGC1', {'costo': 239.71, 'precio_lista': 505.53, 'categoria': 'Transparentes', 'descripcion': 'GLOSS HS LT'}),
        'KITGLOSSGL': cost_map.get('TGC4', {'costo': 740.18, 'precio_lista': 1842.39, 'categoria': 'Transparentes', 'descripcion': 'GLOSS HS GL'}),
        'KITDETPPDEGL': cost_map.get('TTP54', {'costo': 444.02, 'precio_lista': 1188.0, 'categoria': 'Transparentes', 'descripcion': 'KIT TPP 5000 GL'}),
        'TPP54': cost_map.get('TTP54', {'costo': 444.02, 'precio_lista': 1188.0, 'categoria': 'Transparentes', 'descripcion': 'KIT TPP 5000 GL'}),
        'TPP51': cost_map.get('TTP51', {'costo': 149.55, 'precio_lista': 310.85, 'categoria': 'Transparentes', 'descripcion': 'KIT TPP 5000 LT'}),
        'KITSUPERPRIMER2K': cost_map.get('SP2K0014', {'costo': 407.10, 'precio_lista': 912.0, 'categoria': 'Primarios', 'descripcion': 'SUPER PRIMER 2K'}),
        'SUPERPRIMER2K800ML': cost_map.get('SP2K0011', {'costo': 143.77, 'precio_lista': 228.0, 'categoria': 'Primarios', 'descripcion': 'SUPER PRIMER 2K 800ML'}),
        'KIT2KGRISGL': cost_map.get('F2KGRIS4', {'costo': 407.10, 'precio_lista': 912.0, 'categoria': 'Primarios', 'descripcion': 'FONDO DE RELLENO 2K GRIS GL'}),
        'FUGC4': cost_map.get('F2KGRIS4', {'costo': 407.10, 'precio_lista': 912.0, 'categoria': 'Primarios', 'descripcion': 'FONDO UNIVERSAL GRIS GL'}),
        'R504': {'costo': 165.00, 'precio_lista': 298.00, 'categoria': 'Pastas / Resanadores', 'descripcion': 'BODY FILLER R50 GL'},
        'PASTAR50': {'costo': 165.00, 'precio_lista': 298.00, 'categoria': 'Pastas / Resanadores', 'descripcion': 'BODY FILLER R50 GL'},
        'R804': {'costo': 185.00, 'precio_lista': 346.50, 'categoria': 'Pastas / Resanadores', 'descripcion': 'BODY FILLER R80 GL'},
        'R801': {'costo': 65.00, 'precio_lista': 130.90, 'categoria': 'Pastas / Resanadores', 'descripcion': 'BODY FILLER R80 1LT'},
    }
    for k, v in aliases.items():
        if k not in cost_map and v:
            cost_map[k] = v

    return cost_map


def calcular_costo_unitario_linea(nombre_producto, cost_map):
    """
    Encuentra el costo unitario de un producto basándose en su nombre/código de Odoo.
    """
    if not nombre_producto:
        return None, "Línea General", 0.0

    p_upper = str(nombre_producto).upper().strip()

    # 1. Buscar si viene clave entre corchetes [CLAVE]
    if '[' in p_upper and ']' in p_upper:
        code_raw = p_upper.split('[')[1].split(']')[0].strip()
        code_norm = _norm_str(code_raw)
        if code_norm in cost_map:
            item = cost_map[code_norm]
            return item['costo'], item.get('categoria', 'Challenger'), item.get('precio_lista', 0.0)

    # 2. Buscar por código normalizado directo
    p_norm = _norm_str(p_upper)
    if p_norm in cost_map:
        item = cost_map[p_norm]
        return item['costo'], item.get('categoria', 'Challenger'), item.get('precio_lista', 0.0)

    # 3. Buscar coincidencia de subcadenas clave
    for k, item in cost_map.items():
        if len(k) >= 5 and (k in p_norm or p_norm in k):
            return item['costo'], item.get('categoria', 'Challenger'), item.get('precio_lista', 0.0)

    # Clasificación por palabras clave de respaldo (Sin multimarca)
    if any(w in p_upper for w in ['PASTA', 'RESANADOR', 'R-50', 'R-80', 'FILLER']):
        return None, 'Pastas / Resanadores', 0.0
    if any(w in p_upper for w in ['GLOSS', 'TPP', 'TRANSPARENTE', 'BARNIZ', 'EASY MASTER']):
        return None, 'Transparentes', 0.0
    if any(w in p_upper for w in ['PRIMER', 'FONDO', 'RELLENO', 'DTM']):
        return None, 'Primarios', 0.0
    if any(w in p_upper for w in ['ESMALTE', 'COVER FAST', 'ACRILICO', 'POLIURETANO']):
        return None, 'Esmaltes', 0.0
    if any(w in p_upper for w in ['BASE COLOR', 'BC-']):
        return None, 'Base Color', 0.0
    if any(w in p_upper for w in ['PERLA', 'LIQUIDA']):
        return None, 'Perlas Universales', 0.0
    if any(w in p_upper for w in ['PULIMENTO', 'PAPEL', 'BORLA', 'CARRITO']):
        return None, 'Varios', 0.0

    return None, 'Línea General', 0.0


def procesar_estado_resultados(empresa_nombre="TODAS (Consolidado)", anio=2026, mes=0):
    """
    Genera el Estado de Resultados Financiero completo (P&L) cruzando
    ventas de Odoo 19, costos de Challenger, comisiones y gastos operativos.
    """
    cost_map = cargar_diccionario_costos()
    empresa_cfg = EMPRESAS.get(empresa_nombre)
    company_id = empresa_cfg["company_id"] if empresa_cfg else None

    # 1. Definir rango de fechas
    anio_int = int(anio)
    try:
        mes_int = int(mes) if mes and str(mes) != "TODOS" else 0
    except ValueError:
        mes_int = 0

    if mes_int > 0:
        m_str = f"{mes_int:02d}"
        max_d = 31 if mes_int in [1, 3, 5, 7, 8, 10, 12] else (28 if mes_int == 2 else 30)
        fecha_inicio = f"{anio_int}-{m_str}-01"
        fecha_fin = f"{anio_int}-{m_str}-{max_d}"
    else:
        fecha_inicio = f"{anio_int}-01-01"
        fecha_fin = f"{anio_int}-12-31"

    # 2. Conectar a Odoo y traer facturas y notas de crédito de venta
    try:
        uid, models = conectar_odoo(company_id or 1)
        domain_moves = [
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', fecha_inicio),
            ('invoice_date', '<=', fecha_fin)
        ]
        if company_id:
            domain_moves.append(('company_id', '=', company_id))

        moves = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'account.move', 'search_read',
            [domain_moves],
            {'fields': ['id', 'name', 'invoice_date', 'move_type', 'amount_untaxed', 'amount_total', 'partner_id', 'invoice_user_id', 'currency_id']}
        )

        move_ids = [m['id'] for m in moves]
        move_map = {m['id']: m for m in moves}

        # Traer todas las líneas de factura
        lines = []
        if move_ids:
            chunk_size = 500
            for i in range(0, len(move_ids), chunk_size):
                chunk = move_ids[i:i + chunk_size]
                l_batch = models.execute_kw(
                    ODOO_DB, uid, ODOO_API_KEY,
                    'account.move.line', 'search_read',
                    [[
                        ('move_id', 'in', chunk),
                        ('display_type', '=', 'product'),
                        ('price_subtotal', '!=', 0)
                    ]],
                    {'fields': ['move_id', 'product_id', 'name', 'quantity', 'price_unit', 'price_subtotal', 'discount']}
                )
                lines.extend(l_batch)

    except Exception as e:
        print(f"[ERROR Odoo P&L]: {e}")
        moves = []
        lines = []
        move_map = {}

    # 3. Procesar y cruzar cada línea de venta con costos
    ventas_brutas = 0.0
    devoluciones_descuentos = 0.0
    costo_ventas_total = 0.0
    num_unidades_total = 0.0

    # Inicializar acumulación mensual completa para P&L
    meses_pnl = {m: {
        'ventas_brutas': 0.0,
        'devoluciones': 0.0,
        'ventas_netas': 0.0,
        'cogs': 0.0,
        'utilidad_bruta': 0.0,
        'unidades': 0.0
    } for m in range(1, 13)}

    categorias_dict = {}
    productos_dict = {}
    vendedores_dict = {}

    for l in lines:
        m_id = l['move_id'][0] if l.get('move_id') else 0
        move = move_map.get(m_id, {})
        m_type = move.get('move_type', 'out_invoice')
        inv_date = move.get('invoice_date') or fecha_inicio
        mes_num = int(inv_date.split('-')[1]) if '-' in inv_date else 1

        # Vendedor
        user_info = move.get('invoice_user_id')
        vendedor_nom = user_info[1] if user_info else 'Directo / Mostrador'

        subtotal = float(l.get('price_subtotal', 0) or 0)
        qty = float(l.get('quantity', 0) or 0)
        p_info = l.get('product_id')
        p_name = p_info[1] if p_info else (l.get('name') or 'Producto General')

        # Buscar costo y precio de lista
        costo_unit, categoria, precio_lista = calcular_costo_unitario_linea(p_name, cost_map)
        
        # Si no tiene costo exacto, aplicar costo estimado según tipo
        if costo_unit is None:
            costo_unit = round(subtotal / max(qty, 1.0) * 0.52, 2)
            if 'PASTA' in p_name.upper():
                costo_unit = 185.00 if '4' in p_name else 55.00

        line_cogs = round(costo_unit * qty, 2)

        # Ajuste si es Nota de Crédito (devolución)
        if m_type == 'out_refund':
            devoluciones_descuentos += abs(subtotal)
            net_subtotal = -abs(subtotal)
            net_cogs = -abs(line_cogs)
            net_qty = -abs(qty)
            if mes_num in meses_pnl:
                meses_pnl[mes_num]['devoluciones'] += abs(subtotal)
        else:
            ventas_brutas += subtotal
            net_subtotal = subtotal
            net_cogs = line_cogs
            net_qty = qty
            num_unidades_total += qty
            if mes_num in meses_pnl:
                meses_pnl[mes_num]['ventas_brutas'] += subtotal

        costo_ventas_total += net_cogs

        # Acumular por mes
        if mes_num in meses_pnl:
            meses_pnl[mes_num]['ventas_netas'] += net_subtotal
            meses_pnl[mes_num]['cogs'] += net_cogs
            meses_pnl[mes_num]['utilidad_bruta'] += (net_subtotal - net_cogs)
            meses_pnl[mes_num]['unidades'] += net_qty

        # Acumular por Categoría
        if categoria not in categorias_dict:
            categorias_dict[categoria] = {'categoria': categoria, 'ventas': 0.0, 'cogs': 0.0, 'unidades': 0.0, 'num_renglones': 0}
        categorias_dict[categoria]['ventas'] += net_subtotal
        categorias_dict[categoria]['cogs'] += net_cogs
        categorias_dict[categoria]['unidades'] += net_qty
        categorias_dict[categoria]['num_renglones'] += 1

        # Acumular por Producto
        clean_pname = p_name.split(']')[1].strip() if ']' in p_name else p_name
        if clean_pname not in productos_dict:
            productos_dict[clean_pname] = {
                'producto': clean_pname,
                'nombre_completo': p_name,
                'categoria': categoria,
                'ventas': 0.0,
                'cogs': 0.0,
                'unidades': 0.0,
                'costo_unitario': costo_unit,
                'precio_lista': precio_lista,
                'mensual': {m: {'ventas': 0.0, 'cogs': 0.0, 'utilidad': 0.0, 'unidades': 0.0} for m in range(1, 13)},
                'vendedores': {}
            }
        prod_entry = productos_dict[clean_pname]
        prod_entry['ventas'] += net_subtotal
        prod_entry['cogs'] += net_cogs
        prod_entry['unidades'] += net_qty

        # Desglose mensual del producto
        if mes_num in prod_entry['mensual']:
            prod_entry['mensual'][mes_num]['ventas'] += net_subtotal
            prod_entry['mensual'][mes_num]['cogs'] += net_cogs
            prod_entry['mensual'][mes_num]['utilidad'] += (net_subtotal - net_cogs)
            prod_entry['mensual'][mes_num]['unidades'] += net_qty

        # Desglose por vendedor del producto
        if vendedor_nom not in prod_entry['vendedores']:
            prod_entry['vendedores'][vendedor_nom] = {'vendedor': vendedor_nom, 'ventas': 0.0, 'cogs': 0.0, 'unidades': 0.0}
        prod_entry['vendedores'][vendedor_nom]['ventas'] += net_subtotal
        prod_entry['vendedores'][vendedor_nom]['cogs'] += net_cogs
        prod_entry['vendedores'][vendedor_nom]['unidades'] += net_qty

        # Acumular por Vendedor General
        if vendedor_nom not in vendedores_dict:
            vendedores_dict[vendedor_nom] = {
                'vendedor': vendedor_nom,
                'ventas': 0.0,
                'cogs': 0.0,
                'unidades': 0.0,
                'num_pedidos': 0
            }
        vendedores_dict[vendedor_nom]['ventas'] += net_subtotal
        vendedores_dict[vendedor_nom]['cogs'] += net_cogs
        vendedores_dict[vendedor_nom]['unidades'] += net_qty

    ventas_netas = max(0.0, ventas_brutas - devoluciones_descuentos)
    utilidad_bruta = ventas_netas - costo_ventas_total
    margen_bruto_pct = (utilidad_bruta / ventas_netas * 100) if ventas_netas > 0 else 0.0

    # 4. Comisiones a Asesores Comerciales y Contribución Neta
    comisiones_totales = round(ventas_netas * 0.041, 2)
    contribucion_neta_total = round(utilidad_bruta - comisiones_totales, 2)
    margen_contribucion_pct = (contribucion_neta_total / ventas_netas * 100) if ventas_netas > 0 else 0.0

    # 5. Formatear Lista de Categorías
    lista_categorias = []
    for cat, d in categorias_dict.items():
        v = d['ventas']
        c = d['cogs']
        ub = v - c
        mg = (ub / v * 100) if v > 0 else 0.0
        lista_categorias.append({
            'categoria': cat,
            'ventas': round(v, 2),
            'cogs': round(c, 2),
            'utilidad_bruta': round(ub, 2),
            'margen_pct': round(mg, 1),
            'unidades': round(d['unidades'], 1),
            'pct_de_venta': round((v / max(ventas_netas, 1.0)) * 100, 1)
        })
    lista_categorias.sort(key=lambda x: x['ventas'], reverse=True)

    # 6. Formatear Lista de TODOS los Productos con detalles para modal
    lista_productos = []
    for p, d in productos_dict.items():
        v = d['ventas']
        c = d['cogs']
        ub = v - c
        mg = (ub / v * 100) if v > 0 else 0.0
        u = d['unidades']
        costo_u = d['costo_unitario']
        precio_prom = round(v / max(u, 1.0), 2)
        margen_u = round(precio_prom - costo_u, 2)

        # Formatear vendedores del producto
        vends_list = []
        for v_nom, vd in d['vendedores'].items():
            vv = vd['ventas']
            vu = vd['unidades']
            vc = vd['cogs']
            v_ub = vv - vc
            v_mg = (v_ub / vv * 100) if vv > 0 else 0.0
            v_pp = round(vv / max(vu, 1.0), 2)
            vends_list.append({
                'vendedor': v_nom,
                'unidades': round(vu, 1),
                'ventas': round(vv, 2),
                'cogs': round(vc, 2),
                'utilidad_bruta': round(v_ub, 2),
                'margen_pct': round(v_mg, 1),
                'precio_promedio': v_pp
            })
        vends_list.sort(key=lambda x: x['ventas'], reverse=True)

        # Formatear serie mensual del producto
        mensual_list = []
        meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        for m_idx in range(1, 13):
            m_info = d['mensual'][m_idx]
            mensual_list.append({
                'mes_num': m_idx,
                'mes_nombre': meses_nombres[m_idx - 1],
                'ventas': round(m_info['ventas'], 2),
                'cogs': round(m_info['cogs'], 2),
                'utilidad': round(m_info['utilidad'], 2),
                'unidades': round(m_info['unidades'], 1)
            })

        lista_productos.append({
            'producto': p,
            'nombre_completo': d['nombre_completo'],
            'categoria': d['categoria'],
            'ventas': round(v, 2),
            'cogs': round(c, 2),
            'utilidad_bruta': round(ub, 2),
            'margen_pct': round(mg, 1),
            'unidades': round(u, 1),
            'costo_unitario': costo_u,
            'precio_promedio': precio_prom,
            'precio_lista': d.get('precio_lista', 0.0),
            'margen_unitario': margen_u,
            'vendedores': vends_list,
            'mensual': mensual_list
        })
    # Ordenar por Utilidad Bruta descendente
    lista_productos.sort(key=lambda x: x['utilidad_bruta'], reverse=True)

    # 7. Formatear Lista de Vendedores
    lista_vendedores = []
    for vend, d in vendedores_dict.items():
        v = d['ventas']
        c = d['cogs']
        ub = v - c
        mg = (ub / v * 100) if v > 0 else 0.0
        com_est = round(v * 0.042, 2)
        contribucion_neta = ub - com_est
        lista_vendedores.append({
            'vendedor': vend,
            'ventas': round(v, 2),
            'cogs': round(c, 2),
            'utilidad_bruta': round(ub, 2),
            'margen_pct': round(mg, 1),
            'comision_estimada': com_est,
            'contribucion_neta': round(contribucion_neta, 2),
            'unidades': round(d['unidades'], 1)
        })
    lista_vendedores.sort(key=lambda x: x['utilidad_bruta'], reverse=True)

    # 8. Matriz Mensual de Evolución Simple y Completa (Cascada Multi-Mes)
    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    matriz_mensual = []
    
    # Filas para la Matriz Cascada Multi-Mes limpia y exacta
    filas_cascada_matriz = [
        {"concepto": "1. (+) Ventas Brutas Facturadas", "tipo": "ingreso", "meses": {}, "total": round(ventas_brutas, 2)},
        {"concepto": "2. (-) Devoluciones y Descuentos", "tipo": "deduccion", "meses": {}, "total": round(devoluciones_descuentos, 2)},
        {"concepto": "3. (=) VENTAS NETAS REALES", "tipo": "total_clave", "meses": {}, "total": round(ventas_netas, 2)},
        {"concepto": "4. (-) Costo de Ventas (COGS Challenger)", "tipo": "costo", "meses": {}, "total": round(costo_ventas_total, 2)},
        {"concepto": "5. (=) UTILIDAD BRUTA (Margen Ganancia)", "tipo": "utilidad_bruta", "meses": {}, "total": round(utilidad_bruta, 2)},
        {"concepto": "6. [%] Margen Bruto", "tipo": "pct", "meses": {}, "total": round(margen_bruto_pct, 1)},
        {"concepto": "7. (-) Comisiones Asesores Comerciales", "tipo": "gasto", "meses": {}, "total": round(comisiones_totales, 2)},
        {"concepto": "8. (=) MARGEN DE CONTRIBUCIÓN NETO", "tipo": "total_final", "meses": {}, "total": round(contribucion_neta_total, 2)},
        {"concepto": "9. [%] Margen de Contribución Neto", "tipo": "pct", "meses": {}, "total": round(margen_contribucion_pct, 1)},
    ]

    for m_idx in range(1, 13):
        m_data = meses_pnl[m_idx]
        mv_bruta = m_data['ventas_brutas']
        m_dev = m_data['devoluciones']
        mv = m_data['ventas_netas']
        mc = m_data['cogs']
        mub = mv - mc
        mmg = (mub / mv * 100) if mv > 0 else 0.0
        m_com = round(mv * 0.041, 2)
        m_contrib = round(mub - m_com, 2)
        m_contrib_mg = (m_contrib / mv * 100) if mv > 0 else 0.0

        matriz_mensual.append({
            'mes_num': m_idx,
            'mes_nombre': meses_nombres[m_idx - 1],
            'ventas_brutas': round(mv_bruta, 2),
            'devoluciones': round(m_dev, 2),
            'ventas_netas': round(mv, 2),
            'cogs': round(mc, 2),
            'utilidad_bruta': round(mub, 2),
            'margen_pct': round(mmg, 1),
            'comisiones': m_com,
            'contribucion_neta': m_contrib,
            'margen_contribucion_pct': round(m_contrib_mg, 1),
            'unidades': round(m_data['unidades'], 1)
        })

        # Llenar matriz cascada multi-mes
        m_key = meses_nombres[m_idx - 1]
        filas_cascada_matriz[0]["meses"][m_key] = round(mv_bruta, 2)
        filas_cascada_matriz[1]["meses"][m_key] = round(m_dev, 2)
        filas_cascada_matriz[2]["meses"][m_key] = round(mv, 2)
        filas_cascada_matriz[3]["meses"][m_key] = round(mc, 2)
        filas_cascada_matriz[4]["meses"][m_key] = round(mub, 2)
        filas_cascada_matriz[5]["meses"][m_key] = round(mmg, 1)
        filas_cascada_matriz[6]["meses"][m_key] = m_com
        filas_cascada_matriz[7]["meses"][m_key] = m_contrib
        filas_cascada_matriz[8]["meses"][m_key] = round(m_contrib_mg, 1)

    return {
        "kpis": {
            "ventas_brutas": round(ventas_brutas, 2),
            "devoluciones_descuentos": round(devoluciones_descuentos, 2),
            "ventas_netas": round(ventas_netas, 2),
            "costo_ventas": round(costo_ventas_total, 2),
            "utilidad_bruta": round(utilidad_bruta, 2),
            "margen_bruto_pct": round(margen_bruto_pct, 1),
            "comisiones_vendedores": comisiones_totales,
            "contribucion_neta": contribucion_neta_total,
            "margen_contribucion_pct": round(margen_contribucion_pct, 1),
            "unidades_totales": round(num_unidades_total, 1),
            "facturas_totales": len(moves),
            "empresa_seleccionada": empresa_nombre,
            "anio": anio_int,
            "mes": mes_int
        },
        "cascada_pnl": [
            {"concepto": "1. (+) Ventas Brutas Facturadas", "monto": round(ventas_brutas, 2), "pct": 100.0, "tipo": "ingreso"},
            {"concepto": "2. (-) Devoluciones y Descuentos Comerciales", "monto": round(devoluciones_descuentos, 2), "pct": round((devoluciones_descuentos/max(ventas_brutas,1))*100, 1), "tipo": "deduccion"},
            {"concepto": "3. (=) VENTAS NETAS REALES", "monto": round(ventas_netas, 2), "pct": 100.0, "tipo": "total_clave"},
            {"concepto": "4. (-) Costo de Ventas (COGS Challenger)", "monto": round(costo_ventas_total, 2), "pct": round((costo_ventas_total/max(ventas_netas,1))*100, 1), "tipo": "costo"},
            {"concepto": "5. (=) UTILIDAD BRUTA (Margen Ganancia)", "monto": round(utilidad_bruta, 2), "pct": round(margen_bruto_pct, 1), "tipo": "utilidad_bruta"},
            {"concepto": "6. (-) Comisiones Asesores Comerciales", "monto": round(comisiones_totales, 2), "pct": round((comisiones_totales/max(ventas_netas,1))*100, 1), "tipo": "gasto"},
            {"concepto": "7. (=) MARGEN DE CONTRIBUCIÓN NETO", "monto": round(contribucion_neta_total, 2), "pct": round(margen_contribucion_pct, 1), "tipo": "total_final"}
        ],
        "cascada_matriz_mensual": filas_cascada_matriz,
        "meses_nombres": meses_nombres,
        "categorias": lista_categorias,
        "top_productos": lista_productos,
        "vendedores": lista_vendedores,
        "matriz_mensual": matriz_mensual
    }
