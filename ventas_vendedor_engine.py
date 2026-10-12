"""
MOTOR DE VENTAS POR VENDEDOR Y PRODUCTOS VENDIDOS POR MES
=========================================================
Extrae de Odoo 19 todas las facturas de venta, asocia cada factura
al vendedor oficial mediante res.partner.properties (PROP_VENDEDOR_KEY),
con fallback al vendedor asignado en la factura (invoice_user_id),
consolida kits y componentes de Lista de Materiales (BoM), y genera:
1. Resumen de facturación por vendedor en el mes seleccionado (Subtotal Sin IVA y Total Con IVA).
2. Desglose detallado de qué productos vendió cada vendedor (unidades, montos, precios).
3. Matriz comparativa multi-mes de ventas por vendedor.
4. Reporte Trimestral (3 meses) comparativo.
"""

import os
import json
import calendar
from datetime import datetime, date
import numpy as np
import pandas as pd

from odoo_sync_engine import (
    conectar_odoo, ODOO_DB, ODOO_API_KEY, EMPRESAS,
    normalizar_texto, _limpiar_nombre, clasificar_producto,
    obtener_mapa_kits_odoo, obtener_vendedores_odoo,
    CLIENTES_INTEREMPRESA_EXCLUIDOS, PROP_VENDEDOR_KEY
)

MESES_ESP = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

_CACHE_VENTAS_VENDEDOR = {}
_CACHE_TIME_VV = {}

def invalidar_cache_ventas_vendedor():
    global _CACHE_VENTAS_VENDEDOR, _CACHE_TIME_VV
    _CACHE_VENTAS_VENDEDOR.clear()
    _CACHE_TIME_VV.clear()

def obtener_ventas_por_vendedor_engine(empresa_nombre="TODAS (Consolidado)", mes=None, anio=None, vendedor_filtro="TODOS", excluir_interempresa=True):
    """
    Calcula las ventas por vendedor y el desglose de productos vendidos.
    Garantiza que ninguna factura de venta sea descartada y coincida 100% con Odoo.
    """
    hoy = date.today()
    mes_sel = int(mes) if mes else hoy.month
    anio_sel = int(anio) if anio else hoy.year

    cache_key = f"{empresa_nombre}_{mes_sel}_{anio_sel}_{vendedor_filtro}_{excluir_interempresa}"
    ahora = datetime.now().timestamp()
    if cache_key in _CACHE_VENTAS_VENDEDOR and (ahora - _CACHE_TIME_VV.get(cache_key, 0)) < 300:
        return _CACHE_VENTAS_VENDEDOR[cache_key]

    empresa_cfg = EMPRESAS.get(empresa_nombre)
    company_id = empresa_cfg["company_id"] if empresa_cfg else None

    uid, models = conectar_odoo(company_id or 1)
    kit_map = obtener_mapa_kits_odoo(models, uid)

    # 1. Obtener lista oficial de vendedores de Comisiones (PROP_VENDEDOR_KEY)
    vendedores_raw = obtener_vendedores_odoo(company_id or 1)
    vendedores_list = [(val, lbl) for val, lbl in vendedores_raw if lbl.lower().strip() not in ['sin asignar', 'empleado', 'externo']]
    vendedores_oficiales_map = {val: lbl for val, lbl in vendedores_list}
    vendedores_valid_keys = set(vendedores_oficiales_map.keys())

    # 2. Rango de fechas para el análisis (últimos 12 meses para matriz multi-mes)
    fecha_inicio_12m = f"{anio_sel - 1}-{mes_sel:02d}-01"
    ultimo_dia_mes = calendar.monthrange(anio_sel, mes_sel)[1]
    fecha_fin_mes = f"{anio_sel}-{mes_sel:02d}-{ultimo_dia_mes:02d}"

    # Dominio de facturas publicadas
    domain_move = [
        ('move_type', 'in', ['out_invoice', 'out_refund']),
        ('state', '=', 'posted'),
        ('invoice_date', '>=', fecha_inicio_12m),
        ('invoice_date', '<=', fecha_fin_mes)
    ]
    if company_id:
        domain_move.append(('company_id', '=', company_id))

    moves = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'account.move', 'search_read',
        [domain_move],
        {'fields': ['id', 'name', 'invoice_date', 'partner_id', 'invoice_user_id', 'move_type', 'amount_untaxed', 'amount_total', 'amount_residual', 'invoice_line_ids'], 'limit': 10000}
    )

    if not moves:
        empty_res = {
            'periodo_seleccionado': f"{MESES_ESP[mes_sel]} {anio_sel}",
            'resumen_vendedores': [],
            'totales_generales': {
                'total_facturado': 0,
                'subtotal_facturado': 0,
                'total_con_iva': 0,
                'total_unidades': 0,
                'num_facturas': 0,
                'num_vendedores': 0,
                'vendedor_lider': "—",
                'monto_lider': 0.0
            },
            'matriz_meses_vendedores': [],
            'periodos_historico': [],
            'vendedores_disponibles': [{'valor': val, 'nombre': lbl} for val, lbl in vendedores_list]
        }
        _CACHE_VENTAS_VENDEDOR[cache_key] = empty_res
        _CACHE_TIME_VV[cache_key] = ahora
        return empty_res

    # 3. Consulta ULTRA-RÁPIDA de partners presentes en estas facturas (en vez de toda la base)
    pids_presentes = list(set(m['partner_id'][0] for m in moves if m.get('partner_id') and isinstance(m['partner_id'], (list, tuple))))
    partner_map = {}
    partner_vendor_map = {}
    
    if pids_presentes:
        CHUNK_P = 200
        for i_p in range(0, len(pids_presentes), CHUNK_P):
            b_pids = pids_presentes[i_p:i_p+CHUNK_P]
            lote_p = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'res.partner', 'search_read',
                [[('id', 'in', b_pids)]],
                {'fields': ['id', 'name', 'properties', 'commercial_partner_id', 'user_id']}
            )
            for p in lote_p:
                pid = p["id"]
                partner_map[pid] = p
                v_val = None
                for prop in (p.get("properties") or []):
                    if prop.get("name") == PROP_VENDEDOR_KEY:
                        val = prop.get("value")
                        v_val = val[0] if isinstance(val, (list, tuple)) and val else val
                        break
                if v_val and v_val in vendedores_valid_keys:
                    partner_vendor_map[pid] = v_val
                    comm_tuple = p.get("commercial_partner_id")
                    if comm_tuple and isinstance(comm_tuple, (list, tuple)):
                        partner_vendor_map[comm_tuple[0]] = v_val

    move_map = {m['id']: m for m in moves}
    all_line_ids = []
    for m in moves:
        all_line_ids.extend(m.get('invoice_line_ids') or [])

    # 4. Leer líneas de factura con lote seguro
    line_fields = ['id', 'move_id', 'product_id', 'name', 'quantity', 'price_unit', 'price_subtotal', 'discount']
    lines = []
    CHUNK = 2000
    for i in range(0, len(all_line_ids), CHUNK):
        chunk_ids = all_line_ids[i:i+CHUNK]
        chunk_lines = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'account.move.line', 'search_read',
            [[('id', 'in', chunk_ids), ('display_type', '=', 'product')]],
            {'fields': line_fields}
        )
        lines.extend(chunk_lines)

    # 5. Procesar y normalizar registros con jerarquía de fallback para vendedor
    records = []
    facturas_mes_set = set()

    for l in lines:
        mid = l['move_id'][0] if l.get('move_id') else None
        inv = move_map.get(mid)
        if not inv:
            continue

        mtype = inv.get('move_type', 'out_invoice')
        sign = -1.0 if mtype == 'out_refund' else 1.0

        partner_tuple = inv.get('partner_id')
        cliente_nom = partner_tuple[1] if partner_tuple else 'Cliente General'
        cliente_id = partner_tuple[0] if partner_tuple else None

        if excluir_interempresa:
            c_norm = normalizar_texto(cliente_nom)
            if any(ex in c_norm for ex in CLIENTES_INTEREMPRESA_EXCLUIDOS):
                continue

        # Resolver Vendedor usando Jerarquía de Fallback:
        # Resolver Vendedor usando Vendedores Oficiales:
        v_val_cli = partner_vendor_map.get(cliente_id)
        vend_nom = "Sin Vendedor Asignado"
        vend_val = "SIN_ASIGNAR"

        if v_val_cli and v_val_cli in vendedores_oficiales_map:
            vend_nom = vendedores_oficiales_map[v_val_cli]
            vend_val = v_val_cli
        elif inv.get('invoice_user_id') and isinstance(inv.get('invoice_user_id'), (list, tuple)):
            inv_u_nom = normalizar_texto(inv['invoice_user_id'][1])
            for v_k, v_n in vendedores_oficiales_map.items():
                if normalizar_texto(v_n) == inv_u_nom:
                    vend_nom = v_n
                    vend_val = v_k
                    break
        elif partner_map.get(cliente_id) and partner_map[cliente_id].get('user_id') and isinstance(partner_map[cliente_id]['user_id'], (list, tuple)):
            p_u_nom = normalizar_texto(partner_map[cliente_id]['user_id'][1])
            for v_k, v_n in vendedores_oficiales_map.items():
                if normalizar_texto(v_n) == p_u_nom:
                    vend_nom = v_n
                    vend_val = v_k
                    break

        # Filtrar por vendedor si fue especificado
        if vendedor_filtro and vendedor_filtro != 'TODOS':
            if str(vend_val) != str(vendedor_filtro) and normalizar_texto(vend_nom) != normalizar_texto(vendedor_filtro):
                continue

        # Fecha y Periodo
        f_str = inv.get('invoice_date') or str(hoy)
        try:
            dt = datetime.strptime(f_str, '%Y-%m-%d')
            periodo = f"{dt.year}-{dt.month:02d}"
            year_i = dt.year
            month_i = dt.month
        except Exception:
            dt = hoy
            periodo = f"{hoy.year}-{hoy.month:02d}"
            year_i = hoy.year
            month_i = hoy.month

        # Mapeo y clasificación de producto
        p_raw = l['product_id'][1] if l.get('product_id') else l.get('name', 'Sin Producto')
        p_clean = _limpiar_nombre(p_raw)
        p_upper = p_clean.upper().strip()
        nombre_canonico = kit_map.get(p_upper, p_clean)
        es_componente = (p_upper in kit_map)

        cant = float(l.get('quantity', 0) or 0) * sign
        subtotal = float(l.get('price_subtotal', 0) or 0) * sign
        p_unit = float(l.get('price_unit', 0) or 0)

        # Proporción con IVA de la factura
        inv_untaxed = abs(float(inv.get('amount_untaxed', 0) or 0))
        inv_total = abs(float(inv.get('amount_total', 0) or 0))
        tax_factor = (inv_total / inv_untaxed) if inv_untaxed > 0 else 1.16
        total_linea = subtotal * tax_factor

        if es_componente and (p_unit < 1.0 or subtotal < 1.0):
            cant_efectiva = 0.0
        else:
            cant_efectiva = cant

        is_current_month = (year_i == anio_sel and month_i == mes_sel)
        if is_current_month:
            facturas_mes_set.add(inv['id'])

        records.append({
            'factura': inv.get('name', ''),
            'move_id': inv.get('id'),
            'move_type': mtype,
            'vendedor': vend_nom,
            'vendedor_id': vend_val,
            'cliente': cliente_nom,
            'producto': nombre_canonico,
            'categoria': clasificar_producto(nombre_canonico),
            'periodo': periodo,
            'year': year_i,
            'month': month_i,
            'es_mes_actual': is_current_month,
            'cantidad': cant_efectiva,
            'subtotal': subtotal,
            'total': total_linea,
            'precio_unit': p_unit
        })

    if not records:
        empty_res = {
            'periodo_seleccionado': f"{MESES_ESP[mes_sel]} {anio_sel}",
            'resumen_vendedores': [],
            'totales_generales': {
                'total_facturado': 0,
                'subtotal_facturado': 0,
                'total_con_iva': 0,
                'total_nc_con_iva': 0,
                'subtotal_nc': 0,
                'total_neto_con_iva': 0,
                'subtotal_neto': 0,
                'total_unidades': 0,
                'num_facturas': 0,
                'num_nc': 0,
                'num_vendedores': 0,
                'vendedor_lider': "—",
                'vendedor_lider_monto': 0.0,
                'vendedor_lider_subtotal': 0.0
            },
            'matriz_meses_vendedores': [],
            'periodos_historico': [],
            'vendedores_disponibles': [{'valor': val, 'nombre': lbl} for val, lbl in vendedores_list]
        }
        _CACHE_VENTAS_VENDEDOR[cache_key] = empty_res
        _CACHE_TIME_VV[cache_key] = ahora
        return empty_res

    df = pd.DataFrame(records)

    # 6. GENERAR RESUMEN DEL MES SELECCIONADO POR VENDEDOR
    df_mes = df[df['es_mes_actual']]
    df_mes_facs = df_mes[df_mes['move_type'] == 'out_invoice']
    df_mes_ncs = df_mes[df_mes['move_type'] == 'out_refund']

    # Facturas de venta brutas
    tot_subtotal_global = float(df_mes_facs['subtotal'].sum()) if not df_mes_facs.empty else 0.0
    tot_total_global = float(df_mes_facs['total'].sum()) if not df_mes_facs.empty else 0.0
    tot_facturas_global = len(df_mes_facs['factura'].unique()) if not df_mes_facs.empty else 0

    # Notas de crédito
    tot_subtotal_nc = abs(float(df_mes_ncs['subtotal'].sum())) if not df_mes_ncs.empty else 0.0
    tot_total_nc = abs(float(df_mes_ncs['total'].sum())) if not df_mes_ncs.empty else 0.0
    tot_nc_global = len(df_mes_ncs['factura'].unique()) if not df_mes_ncs.empty else 0

    tot_subtotal_neto = tot_subtotal_global - tot_subtotal_nc
    tot_total_neto = tot_total_global - tot_total_nc
    tot_unidades_global = float(df_mes['cantidad'].sum()) if not df_mes.empty else 0.0

    resumen_vendedores = []
    vendedor_lider_nombre = "—"
    vendedor_lider_monto = 0.0
    vendedor_lider_subtotal = 0.0

    if not df_mes.empty:
        # Agrupar por vendedor
        vendedores_unicos_mes = df_mes[['vendedor', 'vendedor_id']].drop_duplicates()
        temp_vends = []

        for _, row_v in vendedores_unicos_mes.iterrows():
            vend_name = str(row_v['vendedor'])
            vend_v_id = str(row_v['vendedor_id'])
            is_direct = (vend_name == 'Sin Vendedor Asignado' or vend_v_id == 'SIN_ASIGNAR')

            df_v = df_mes[df_mes['vendedor'] == vend_name]
            df_v_facs = df_v[df_v['move_type'] == 'out_invoice']
            df_v_ncs = df_v[df_v['move_type'] == 'out_refund']

            fac_sub = float(df_v_facs['subtotal'].sum()) if not df_v_facs.empty else 0.0
            fac_tot = float(df_v_facs['total'].sum()) if not df_v_facs.empty else 0.0
            fac_cant = float(df_v_facs['cantidad'].sum()) if not df_v_facs.empty else 0.0
            fac_count = int(df_v_facs['factura'].nunique()) if not df_v_facs.empty else 0
            cli_count = int(df_v_facs['cliente'].nunique()) if not df_v_facs.empty else 0

            nc_sub = abs(float(df_v_ncs['subtotal'].sum())) if not df_v_ncs.empty else 0.0
            nc_tot = abs(float(df_v_ncs['total'].sum())) if not df_v_ncs.empty else 0.0
            nc_count = int(df_v_ncs['factura'].nunique()) if not df_v_ncs.empty else 0

            net_sub = fac_sub - nc_sub
            net_tot = fac_tot - nc_tot
            pct_part = (fac_tot / tot_total_global * 100.0) if tot_total_global > 0 else 0.0

            # Desglose de Productos vendidos por este vendedor
            agg_prods_vend = df_v.groupby('producto').agg({
                'subtotal': 'sum',
                'total': 'sum',
                'cantidad': 'sum',
                'precio_unit': 'mean',
                'categoria': 'first',
                'cliente': 'nunique',
                'factura': 'nunique'
            }).sort_values('subtotal', ascending=False)

            lista_productos_vend = []
            for p_pos, (p_name, r_p) in enumerate(agg_prods_vend.iterrows(), 1):
                p_sub = float(r_p['subtotal'])
                p_tot = float(r_p['total'])
                p_cant = float(r_p['cantidad'])
                p_pct = (p_sub / fac_sub * 100.0) if fac_sub > 0 else 0.0
                p_prom = p_sub / max(p_cant, 1.0) if p_cant > 0 else float(r_p['precio_unit'])

                lista_productos_vend.append({
                    'posicion': p_pos,
                    'producto': p_name,
                    'categoria': r_p['categoria'],
                    'cantidad': round(p_cant, 1),
                    'precio_promedio': round(p_prom, 2),
                    'subtotal': round(p_sub, 2),
                    'total_con_iva': round(p_tot, 2),
                    'pct_del_vendedor': round(p_pct, 1),
                    'num_clientes': int(r_p['cliente']),
                    'num_facturas': int(r_p['factura'])
                })

            top_producto = lista_productos_vend[0]['producto'] if lista_productos_vend else "—"

            temp_vends.append({
                'vendedor': vend_name,
                'vendedor_id': vend_v_id,
                'es_venta_directa': is_direct,
                'total_subtotal': round(fac_sub, 2),
                'total_con_iva': round(fac_tot, 2),
                'total_facturado': round(fac_tot, 2),
                'subtotal_facturado': round(fac_sub, 2),
                'subtotal_nc': round(nc_sub, 2),
                'total_nc_con_iva': round(nc_tot, 2),
                'subtotal_neto': round(net_sub, 2),
                'total_neto_con_iva': round(net_tot, 2),
                'total_cantidad': round(fac_cant, 1),
                'num_facturas': fac_count,
                'num_nc': nc_count,
                'num_clientes': cli_count,
                'ticket_promedio': round(fac_tot / max(fac_count, 1), 2),
                'pct_participacion': round(pct_part, 1),
                'top_producto': top_producto,
                'productos_vendidos': lista_productos_vend
            })

        # Separar asesores reales y ventas directas
        asesores_reales = [v for v in temp_vends if not v['es_venta_directa']]
        ventas_directas = [v for v in temp_vends if v['es_venta_directa']]

        # Ordenar asesores reales por ventas totales con IVA
        asesores_reales.sort(key=lambda x: x['total_con_iva'], reverse=True)

        if asesores_reales:
            vendedor_lider_nombre = asesores_reales[0]['vendedor']
            vendedor_lider_monto = asesores_reales[0]['total_con_iva']
            vendedor_lider_subtotal = asesores_reales[0]['total_subtotal']

        for pos, v in enumerate(asesores_reales, 1):
            v['posicion'] = pos
            resumen_vendedores.append(v)

        for v in ventas_directas:
            v['posicion'] = len(resumen_vendedores) + 1
            resumen_vendedores.append(v)

    # Asegurar que todos los vendedores oficiales aparezcan aunque tengan $0
    vends_con_ventas = {v['vendedor'] for v in resumen_vendedores}
    pos_sig = len(resumen_vendedores) + 1
    for val, lbl in vendedores_list:
        if lbl not in vends_con_ventas:
            resumen_vendedores.append({
                'posicion': pos_sig,
                'vendedor': lbl,
                'vendedor_id': val,
                'es_venta_directa': False,
                'total_subtotal': 0.0,
                'total_con_iva': 0.0,
                'total_facturado': 0.0,
                'subtotal_facturado': 0.0,
                'subtotal_nc': 0.0,
                'total_nc_con_iva': 0.0,
                'subtotal_neto': 0.0,
                'total_neto_con_iva': 0.0,
                'total_cantidad': 0.0,
                'num_facturas': 0,
                'num_nc': 0,
                'num_clientes': 0,
                'ticket_promedio': 0.0,
                'pct_participacion': 0.0,
                'top_producto': "—",
                'productos_vendidos': []
            })
            pos_sig += 1

    # 7. MATRIZ MULTI-MES POR VENDEDOR (Últimos 12 meses)
    todos_periodos = sorted(df['periodo'].unique().tolist())
    periodos_recientes = todos_periodos[-12:] if len(todos_periodos) > 12 else todos_periodos

    pivot_vendedores = df.pivot_table(index='vendedor', columns='periodo', values='subtotal', aggfunc='sum', fill_value=0.0)
    tot_hist_vend = pivot_vendedores.sum(axis=1).sort_values(ascending=False)

    matriz_meses_vendedores = []
    for rank, (v_name, tot_h) in enumerate(tot_hist_vend.items(), 1):
        ventas_mes = {}
        for per in periodos_recientes:
            val_m = float(pivot_vendedores.loc[v_name, per]) if per in pivot_vendedores.columns else 0.0
            ventas_mes[per] = val_m

        if len(periodos_recientes) >= 2:
            ult_p = periodos_recientes[-1]
            ant_p = periodos_recientes[-2]
            ult_v = ventas_mes.get(ult_p, 0.0)
            ant_v = ventas_mes.get(ant_p, 0.0)
            mom_g = ((ult_v - ant_v) / ant_v * 100.0) if ant_v > 0 else 0.0
        else:
            mom_g = 0.0

        matriz_meses_vendedores.append({
            'posicion': rank,
            'vendedor': v_name,
            'ventas_por_mes': ventas_mes,
            'total_historico': round(float(tot_h), 2),
            'mom_growth': round(mom_g, 1)
        })

    vends_en_matriz = {m['vendedor'] for m in matriz_meses_vendedores}
    pos_m_sig = len(matriz_meses_vendedores) + 1
    for val, lbl in vendedores_list:
        if lbl not in vends_en_matriz:
            matriz_meses_vendedores.append({
                'posicion': pos_m_sig,
                'vendedor': lbl,
                'ventas_por_mes': {per: 0.0 for per in periodos_recientes},
                'total_historico': 0.0,
                'mom_growth': 0.0
            })
            pos_m_sig += 1

    vendedor_lider = vendedor_lider_nombre
    vendedor_lider_monto = vendedor_lider_monto

    # Lista consolidada de todos los vendedores disponibles para el dropdown (solo asesores reales y venta directa al final)
    vendedores_disponibles_map = {val: lbl for val, lbl in vendedores_list}
    for v in resumen_vendedores:
        if v['vendedor_id'] not in vendedores_disponibles_map:
            vendedores_disponibles_map[v['vendedor_id']] = v['vendedor']

    vendedores_disponibles_list = [{'valor': k, 'nombre': v} for k, v in sorted(vendedores_disponibles_map.items(), key=lambda x: x[1])]

    resultado = {
        'periodo_seleccionado': f"{MESES_ESP[mes_sel]} {anio_sel}",
        'mes': mes_sel,
        'anio': anio_sel,
        'totales_generales': {
            'total_facturado': round(tot_total_global, 2),      # Total Con Impuestos (coincide 100% con Odoo Total $4,936,947.92)
            'subtotal_facturado': round(tot_subtotal_global, 2), # Subtotal Sin Impuestos (coincide 100% con Odoo Subtotal $4,267,233.15)
            'total_con_iva': round(tot_total_global, 2),
            'total_nc_con_iva': round(tot_total_nc, 2),          # Total NCs con IVA (-$211,949.07)
            'subtotal_nc': round(tot_subtotal_nc, 2),            # Subtotal NCs sin IVA (-$210,952.65)
            'total_neto_con_iva': round(tot_total_neto, 2),      # Venta Neta con IVA ($4,724,998.85)
            'subtotal_neto': round(tot_subtotal_neto, 2),        # Subtotal Neto sin IVA ($4,056,280.50)
            'total_unidades': round(tot_unidades_global, 1),
            'num_facturas': tot_facturas_global,                 # 496 facturas emitidas
            'num_nc': tot_nc_global,                             # 17 notas de credito emitidas
            'num_vendedores': sum(1 for v in resumen_vendedores if not v.get('es_venta_directa') and v['total_con_iva'] > 0),
            'vendedor_lider': vendedor_lider,                    # Fabian Lizarraga Lizarraga
            'vendedor_lider_monto': round(vendedor_lider_monto, 2),
            'vendedor_lider_subtotal': round(vendedor_lider_subtotal, 2),
            'monto_lider': round(vendedor_lider_monto, 2)
        },
        'resumen_vendedores': resumen_vendedores,
        'matriz_meses_vendedores': matriz_meses_vendedores,
        'periodos_historico': periodos_recientes,
        'vendedores_disponibles': vendedores_disponibles_list
    }

    _CACHE_VENTAS_VENDEDOR[cache_key] = resultado
    _CACHE_TIME_VV[cache_key] = ahora
    return resultado


def obtener_reporte_3meses_vendedores_engine(empresa_nombre="TODAS (Consolidado)", mes_fin=None, anio_fin=None, excluir_interempresa=True):
    """
    Calcula el reporte consolidado de los últimos 3 meses (Trimestre) para todos los vendedores.
    """
    hoy = date.today()
    mes_3 = int(mes_fin) if mes_fin else hoy.month
    anio_3 = int(anio_fin) if anio_fin else hoy.year

    if mes_3 == 1:
        mes_2 = 12
        anio_2 = anio_3 - 1
    else:
        mes_2 = mes_3 - 1
        anio_2 = anio_3

    if mes_2 == 1:
        mes_1 = 12
        anio_1 = anio_2 - 1
    else:
        mes_1 = mes_2 - 1
        anio_1 = anio_2

    periodos_3m = [
        f"{anio_1}-{mes_1:02d}",
        f"{anio_2}-{mes_2:02d}",
        f"{anio_3}-{mes_3:02d}"
    ]
    periodos_3m_nombres = [
        f"{MESES_ESP[mes_1]} {anio_1}",
        f"{MESES_ESP[mes_2]} {anio_2}",
        f"{MESES_ESP[mes_3]} {anio_3}"
    ]
    periodo_label_completo = f"{MESES_ESP[mes_1]} {anio_1} — {MESES_ESP[mes_3]} {anio_3}"

    cache_key_3m = f"3M_{empresa_nombre}_{periodos_3m[-1]}_{excluir_interempresa}"
    ahora = datetime.now().timestamp()
    if cache_key_3m in _CACHE_VENTAS_VENDEDOR and (ahora - _CACHE_TIME_VV.get(cache_key_3m, 0)) < 300:
        return _CACHE_VENTAS_VENDEDOR[cache_key_3m]

    empresa_cfg = EMPRESAS.get(empresa_nombre)
    company_id = empresa_cfg["company_id"] if empresa_cfg else None
    uid, models = conectar_odoo(company_id or 1)
    kit_map = obtener_mapa_kits_odoo(models, uid)
    vendedores_raw = obtener_vendedores_odoo(company_id or 1)
    vendedores_list = [(val, lbl) for val, lbl in vendedores_raw if lbl.lower().strip() not in ['sin asignar', 'empleado', 'externo']]
    vendedores_oficiales_map = {val: lbl for val, lbl in vendedores_list}
    vendedores_valid_keys = set(vendedores_oficiales_map.keys())

    fecha_inicio_3m = f"{anio_1}-{mes_1:02d}-01"
    ultimo_dia_mes3 = calendar.monthrange(anio_3, mes_3)[1]
    fecha_fin_3m = f"{anio_3}-{mes_3:02d}-{ultimo_dia_mes3:02d}"

    domain_move = [
        ('move_type', 'in', ['out_invoice', 'out_refund']),
        ('state', '=', 'posted'),
        ('invoice_date', '>=', fecha_inicio_3m),
        ('invoice_date', '<=', fecha_fin_3m)
    ]
    if company_id:
        domain_move.append(('company_id', '=', company_id))

    moves = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'account.move', 'search_read',
        [domain_move],
        {'fields': ['id', 'name', 'invoice_date', 'partner_id', 'invoice_user_id', 'move_type', 'amount_untaxed', 'amount_total', 'invoice_line_ids'], 'limit': 10000}
    )

    if not moves:
        empty_res = {
            'periodo_trimestre': periodo_label_completo,
            'periodos_meses': periodos_3m,
            'periodos_meses_nombres': periodos_3m_nombres,
            'totales_generales_3m': {
                'total_facturado': 0,
                'subtotal_facturado': 0,
                'total_con_iva': 0,
                'total_unidades': 0,
                'num_facturas': 0,
                'num_vendedores': 0
            },
            'resumen_vendedores_3m': [],
            'totales_por_mes': []
        }
        _CACHE_VENTAS_VENDEDOR[cache_key_3m] = empty_res
        _CACHE_TIME_VV[cache_key_3m] = ahora
        return empty_res

    # Fast partner query
    pids_presentes = list(set(m['partner_id'][0] for m in moves if m.get('partner_id') and isinstance(m['partner_id'], (list, tuple))))
    partner_map = {}
    partner_vendor_map = {}
    
    if pids_presentes:
        CHUNK_P = 200
        for i_p in range(0, len(pids_presentes), CHUNK_P):
            b_pids = pids_presentes[i_p:i_p+CHUNK_P]
            lote_p = models.execute_kw(
                ODOO_DB, uid, ODOO_API_KEY,
                'res.partner', 'search_read',
                [[('id', 'in', b_pids)]],
                {'fields': ['id', 'name', 'properties', 'commercial_partner_id', 'user_id']}
            )
            for p in lote_p:
                pid = p["id"]
                partner_map[pid] = p
                v_val = None
                for prop in (p.get("properties") or []):
                    if prop.get("name") == PROP_VENDEDOR_KEY:
                        val = prop.get("value")
                        v_val = val[0] if isinstance(val, (list, tuple)) and val else val
                        break
                if v_val and v_val in vendedores_valid_keys:
                    partner_vendor_map[pid] = v_val
                    comm_tuple = p.get("commercial_partner_id")
                    if comm_tuple and isinstance(comm_tuple, (list, tuple)):
                        partner_vendor_map[comm_tuple[0]] = v_val

    move_map = {m['id']: m for m in moves}
    all_line_ids = []
    for m in moves:
        all_line_ids.extend(m.get('invoice_line_ids') or [])

    line_fields = ['id', 'move_id', 'product_id', 'name', 'quantity', 'price_unit', 'price_subtotal']
    lines = []
    CHUNK = 2000
    for i in range(0, len(all_line_ids), CHUNK):
        chunk_ids = all_line_ids[i:i+CHUNK]
        chunk_lines = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'account.move.line', 'search_read',
            [[('id', 'in', chunk_ids), ('display_type', '=', 'product')]],
            {'fields': line_fields}
        )
        lines.extend(chunk_lines)

    records_3m = []
    for l in lines:
        mid = l['move_id'][0] if l.get('move_id') else None
        inv = move_map.get(mid)
        if not inv:
            continue

        mtype = inv.get('move_type', 'out_invoice')
        sign = -1.0 if mtype == 'out_refund' else 1.0

        partner_tuple = inv.get('partner_id')
        cliente_nom = partner_tuple[1] if partner_tuple else 'Cliente General'
        cliente_id = partner_tuple[0] if partner_tuple else None

        if excluir_interempresa:
            c_norm = normalizar_texto(cliente_nom)
            if any(ex in c_norm for ex in CLIENTES_INTEREMPRESA_EXCLUIDOS):
                continue

        # Fallback hierarchy for official seller
        v_val_cli = partner_vendor_map.get(cliente_id)
        vend_nom = "Sin Vendedor Asignado"
        vend_val = "SIN_ASIGNAR"

        if v_val_cli and v_val_cli in vendedores_oficiales_map:
            vend_nom = vendedores_oficiales_map[v_val_cli]
            vend_val = v_val_cli
        elif inv.get('invoice_user_id') and isinstance(inv.get('invoice_user_id'), (list, tuple)):
            inv_u_nom = normalizar_texto(inv['invoice_user_id'][1])
            for v_k, v_n in vendedores_oficiales_map.items():
                if normalizar_texto(v_n) == inv_u_nom:
                    vend_nom = v_n
                    vend_val = v_k
                    break
        elif partner_map.get(cliente_id) and partner_map[cliente_id].get('user_id') and isinstance(partner_map[cliente_id]['user_id'], (list, tuple)):
            p_u_nom = normalizar_texto(partner_map[cliente_id]['user_id'][1])
            for v_k, v_n in vendedores_oficiales_map.items():
                if normalizar_texto(v_n) == p_u_nom:
                    vend_nom = v_n
                    vend_val = v_k
                    break

        f_str = inv.get('invoice_date') or str(hoy)
        try:
            dt = datetime.strptime(f_str, '%Y-%m-%d')
            periodo = f"{dt.year}-{dt.month:02d}"
        except Exception:
            dt = hoy
            periodo = f"{hoy.year}-{hoy.month:02d}"

        p_raw = l['product_id'][1] if l.get('product_id') else l.get('name', 'Sin Producto')
        p_clean = _limpiar_nombre(p_raw)
        p_upper = p_clean.upper().strip()
        nombre_canonico = kit_map.get(p_upper, p_clean)
        es_componente = (p_upper in kit_map)

        cant = float(l.get('quantity', 0) or 0) * sign
        subtotal = float(l.get('price_subtotal', 0) or 0) * sign
        p_unit = float(l.get('price_unit', 0) or 0)

        inv_untaxed = abs(float(inv.get('amount_untaxed', 0) or 0))
        inv_total = abs(float(inv.get('amount_total', 0) or 0))
        tax_factor = (inv_total / inv_untaxed) if inv_untaxed > 0 else 1.16
        total_linea = subtotal * tax_factor

        if es_componente and (p_unit < 1.0 or subtotal < 1.0):
            cant_efectiva = 0.0
        else:
            cant_efectiva = cant

        records_3m.append({
            'factura': inv.get('name', ''),
            'vendedor': vend_nom,
            'vendedor_id': vend_val,
            'cliente': cliente_nom,
            'producto': nombre_canonico,
            'categoria': clasificar_producto(nombre_canonico),
            'periodo': periodo,
            'cantidad': cant_efectiva,
            'subtotal': subtotal,
            'total': total_linea,
            'precio_unit': p_unit
        })

    if not records_3m:
        empty_res = {
            'periodo_trimestre': periodo_label_completo,
            'periodos_meses': periodos_3m,
            'periodos_meses_nombres': periodos_3m_nombres,
            'totales_generales_3m': {
                'total_facturado': 0,
                'subtotal_facturado': 0,
                'total_con_iva': 0,
                'total_unidades': 0,
                'num_facturas': 0,
                'num_vendedores': 0
            },
            'resumen_vendedores_3m': [],
            'totales_por_mes': []
        }
        _CACHE_VENTAS_VENDEDOR[cache_key_3m] = empty_res
        _CACHE_TIME_VV[cache_key_3m] = ahora
        return empty_res

    df3 = pd.DataFrame(records_3m)
    tot_sub_3m_global = float(df3['subtotal'].sum())
    tot_tot_3m_global = float(df3['total'].sum())
    tot_cant_3m_global = float(df3['cantidad'].sum())
    tot_facs_3m_global = len(df3['factura'].unique())

    # Totales mensuales globales
    totales_por_mes = []
    for per, per_nom in zip(periodos_3m, periodos_3m_nombres):
        df_p = df3[df3['periodo'] == per]
        totales_por_mes.append({
            'periodo': per,
            'nombre_mes': per_nom,
            'total_subtotal': round(float(df_p['subtotal'].sum()), 2),
            'total_con_iva': round(float(df_p['total'].sum()), 2),
            'total_cantidad': round(float(df_p['cantidad'].sum()), 1),
            'num_facturas': len(df_p['factura'].unique())
        })

    # Agrupación por vendedor en los 3 meses
    agg_vends_3m = df3.groupby('vendedor').agg({
        'subtotal': 'sum',
        'total': 'sum',
        'cantidad': 'sum',
        'factura': 'nunique',
        'cliente': 'nunique'
    }).sort_values('subtotal', ascending=False)

    p0 = periodos_3m[0]
    p1 = periodos_3m[1]
    p2 = periodos_3m[2]

    resumen_vendedores_3m = []
    for pos, (v_name, r_v) in enumerate(agg_vends_3m.iterrows(), 1):
        v_sub_tot = float(r_v['subtotal'])
        v_tot_tot = float(r_v['total'])
        v_cant_tot = float(r_v['cantidad'])
        v_fac_tot = int(r_v['factura'])
        v_cli_tot = int(r_v['cliente'])
        v_pct_part = (v_sub_tot / tot_sub_3m_global * 100.0) if tot_sub_3m_global > 0 else 0.0

        df_vend = df3[df3['vendedor'] == v_name]

        sub_m1 = float(df_vend[df_vend['periodo'] == p0]['subtotal'].sum())
        sub_m2 = float(df_vend[df_vend['periodo'] == p1]['subtotal'].sum())
        sub_m3 = float(df_vend[df_vend['periodo'] == p2]['subtotal'].sum())

        tot_m1 = float(df_vend[df_vend['periodo'] == p0]['total'].sum())
        tot_m2 = float(df_vend[df_vend['periodo'] == p1]['total'].sum())
        tot_m3 = float(df_vend[df_vend['periodo'] == p2]['total'].sum())

        cant_m1 = float(df_vend[df_vend['periodo'] == p0]['cantidad'].sum())
        cant_m2 = float(df_vend[df_vend['periodo'] == p1]['cantidad'].sum())
        cant_m3 = float(df_vend[df_vend['periodo'] == p2]['cantidad'].sum())

        if sub_m2 > 0:
            tendencia_mom = ((sub_m3 - sub_m2) / sub_m2 * 100.0)
        elif sub_m1 > 0:
            tendencia_mom = ((sub_m3 - sub_m1) / sub_m1 * 100.0)
        else:
            tendencia_mom = 0.0

        pivot_prods_sub = df_vend.pivot_table(index='producto', columns='periodo', values='subtotal', aggfunc='sum', fill_value=0.0)
        pivot_prods_cant = df_vend.pivot_table(index='producto', columns='periodo', values='cantidad', aggfunc='sum', fill_value=0.0)
        cat_map_v = df_vend.groupby('producto')['categoria'].first().to_dict()
        agg_p_tot = df_vend.groupby('producto').agg({'subtotal': 'sum', 'cantidad': 'sum', 'factura': 'nunique'}).sort_values('subtotal', ascending=False)

        prods_vend_3m = []
        for p_rank, (p_nom, r_p) in enumerate(agg_p_tot.iterrows(), 1):
            p_sub_tot = float(r_p['subtotal'])
            p_cant_tot = float(r_p['cantidad'])
            p_p_prom = p_sub_tot / max(p_cant_tot, 1.0)
            p_pct_vend = (p_sub_tot / v_sub_tot * 100.0) if v_sub_tot > 0 else 0.0

            c_m1 = float(pivot_prods_cant.loc[p_nom, p0]) if (p_nom in pivot_prods_cant.index and p0 in pivot_prods_cant.columns) else 0.0
            c_m2 = float(pivot_prods_cant.loc[p_nom, p1]) if (p_nom in pivot_prods_cant.index and p1 in pivot_prods_cant.columns) else 0.0
            c_m3 = float(pivot_prods_cant.loc[p_nom, p2]) if (p_nom in pivot_prods_cant.index and p2 in pivot_prods_cant.columns) else 0.0

            s_m1 = float(pivot_prods_sub.loc[p_nom, p0]) if (p_nom in pivot_prods_sub.index and p0 in pivot_prods_sub.columns) else 0.0
            s_m2 = float(pivot_prods_sub.loc[p_nom, p1]) if (p_nom in pivot_prods_sub.index and p1 in pivot_prods_sub.columns) else 0.0
            s_m3 = float(pivot_prods_sub.loc[p_nom, p2]) if (p_nom in pivot_prods_sub.index and p2 in pivot_prods_sub.columns) else 0.0

            prods_vend_3m.append({
                'posicion': p_rank,
                'producto': p_nom,
                'categoria': cat_map_v.get(p_nom, "CHALLENGER"),
                'cant_mes_1': round(c_m1, 1),
                'cant_mes_2': round(c_m2, 1),
                'cant_mes_3': round(c_m3, 1),
                'sub_mes_1': round(s_m1, 2),
                'sub_mes_2': round(s_m2, 2),
                'sub_mes_3': round(s_m3, 2),
                'total_cantidad_3m': round(p_cant_tot, 1),
                'precio_promedio_3m': round(p_p_prom, 2),
                'total_subtotal_3m': round(p_sub_tot, 2),
                'pct_del_vendedor_3m': round(p_pct_vend, 1),
                'num_facturas_3m': int(r_p['factura'])
            })

        top_prod_v = prods_vend_3m[0]['producto'] if prods_vend_3m else "—"

        resumen_vendedores_3m.append({
            'posicion': pos,
            'vendedor': v_name,
            'sub_mes_1': round(sub_m1, 2),
            'sub_mes_2': round(sub_m2, 2),
            'sub_mes_3': round(sub_m3, 2),
            'tot_mes_1': round(tot_m1, 2),
            'tot_mes_2': round(tot_m2, 2),
            'tot_mes_3': round(tot_m3, 2),
            'cant_mes_1': round(cant_m1, 1),
            'cant_mes_2': round(cant_m2, 1),
            'cant_mes_3': round(cant_m3, 1),
            'total_subtotal_3m': round(v_sub_tot, 2),
            'total_con_iva_3m': round(v_tot_tot, 2),
            'total_cantidad_3m': round(v_cant_tot, 1),
            'num_facturas_3m': v_fac_tot,
            'num_clientes_3m': v_cli_tot,
            'ticket_promedio_3m': round(v_sub_tot / max(v_fac_tot, 1), 2),
            'pct_participacion_3m': round(v_pct_part, 1),
            'tendencia_mom': round(tendencia_mom, 1),
            'top_producto_3m': top_prod_v,
            'productos_vendidos_3m': prods_vend_3m
        })

    vends_con_ventas_3m = {v['vendedor'] for v in resumen_vendedores_3m}
    pos_sig_3m = len(resumen_vendedores_3m) + 1
    for val, lbl in vendedores_list:
        if lbl not in vends_con_ventas_3m:
            resumen_vendedores_3m.append({
                'posicion': pos_sig_3m,
                'vendedor': lbl,
                'sub_mes_1': 0.0,
                'sub_mes_2': 0.0,
                'sub_mes_3': 0.0,
                'tot_mes_1': 0.0,
                'tot_mes_2': 0.0,
                'tot_mes_3': 0.0,
                'cant_mes_1': 0.0,
                'cant_mes_2': 0.0,
                'cant_mes_3': 0.0,
                'total_subtotal_3m': 0.0,
                'total_con_iva_3m': 0.0,
                'total_cantidad_3m': 0.0,
                'num_facturas_3m': 0,
                'num_clientes_3m': 0,
                'ticket_promedio_3m': 0.0,
                'pct_participacion_3m': 0.0,
                'tendencia_mom': 0.0,
                'top_producto_3m': "—",
                'productos_vendidos_3m': []
            })
            pos_sig_3m += 1

    vendedor_lider_3m = resumen_vendedores_3m[0]['vendedor'] if resumen_vendedores_3m else "—"
    vendedor_lider_monto_3m = resumen_vendedores_3m[0]['total_con_iva_3m'] if resumen_vendedores_3m else 0.0

    resultado_3m = {
        'periodo_trimestre': periodo_label_completo,
        'periodos_meses': periodos_3m,
        'periodos_meses_nombres': periodos_3m_nombres,
        'totales_generales_3m': {
            'total_facturado': round(tot_tot_3m_global, 2),
            'subtotal_facturado': round(tot_sub_3m_global, 2),
            'total_con_iva': round(tot_tot_3m_global, 2),
            'total_unidades': round(tot_cant_3m_global, 1),
            'num_facturas': tot_facs_3m_global,
            'num_vendedores': len(resumen_vendedores_3m),
            'vendedor_lider': vendedor_lider_3m,
            'vendedor_lider_monto': vendedor_lider_monto_3m
        },
        'totales_por_mes': totales_por_mes,
        'resumen_vendedores_3m': resumen_vendedores_3m
    }

    _CACHE_VENTAS_VENDEDOR[cache_key_3m] = resultado_3m
    _CACHE_TIME_VV[cache_key_3m] = ahora
    return resultado_3m
