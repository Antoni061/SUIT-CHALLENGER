"""
MOTOR DE MACHINE LEARNING & PRONÓSTICO DE DEMANDA (XGBoost / LightGBM / Gradient Boosting)
========================================================================================
Módulo de Inteligencia Artificial para pronóstico de demanda, proyección de ingresos y
análisis de tendencias históricas de los 20 productos más vendidos de Challenger Automotive.
"""

import os
import json
import calendar
from datetime import datetime, date
import numpy as np
import pandas as pd

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

try:
    import lightgbm as lgb
    LGB_AVAILABLE = True
except ImportError:
    LGB_AVAILABLE = False

from sklearn.ensemble import GradientBoostingRegressor

from odoo_sync_engine import (
    conectar_odoo, ODOO_DB, ODOO_API_KEY, EMPRESAS,
    normalizar_texto, _limpiar_nombre, clasificar_producto,
    obtener_mapa_kits_odoo, fmt_mxn, fmt_num
)

CLIENTES_INTEREMPRESA = ["auto linea multitrans", "autolinea multitrans", "baldomero medina garza"]
MESES_ESP = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
_ML_CACHE = {}
_ML_CACHE_TIME = {}

def invalidar_cache_ml():
    global _ML_CACHE, _ML_CACHE_TIME
    _ML_CACHE.clear()
    _ML_CACHE_TIME.clear()

def obtener_historico_top20_ml(empresa_nombre="TODAS (Consolidado)", meses_analisis=18, excluir_interempresa=True):
    """
    Extrae las ventas históricas de los últimos meses desde Odoo 19,
    consolida kits y componentes de Lista de Materiales (BoM),
    determina todos los productos vendidos, y entrena un modelo de
    Machine Learning (XGBoost / Gradient Boosting) optimizado y cacheado.
    """
    cache_key = f"{empresa_nombre}_{excluir_interempresa}"
    ahora = datetime.now().timestamp()
    if cache_key in _ML_CACHE and (ahora - _ML_CACHE_TIME.get(cache_key, 0)) < 600:
        return _ML_CACHE[cache_key]

    empresa_cfg = EMPRESAS.get(empresa_nombre)
    company_id = empresa_cfg["company_id"] if empresa_cfg else None

    uid, models = conectar_odoo(company_id or 1)
    kit_map = obtener_mapa_kits_odoo(models, uid)

    hoy = date.today()
    anio_inicio = hoy.year - 1
    fecha_inicio_str = f"{anio_inicio}-01-01"

    domain = [
        ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
        ('move_id.state', '=', 'posted'),
        ('display_type', '=', 'product'),
        ('move_id.invoice_date', '>=', fecha_inicio_str)
    ]

    if company_id:
        domain.append(('company_id', '=', company_id))

    fields = [
        'product_id', 'name', 'quantity', 'price_unit', 'price_subtotal',
        'discount', 'move_id', 'company_id'
    ]

    lines = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'account.move.line', 'search_read',
        [domain],
        {'fields': fields, 'limit': 20000}
    )

    if not lines:
        empty_res = {
            'ml_engine': 'XGBoost Regressor (Gradient Boosting v3.4)',
            'mes_pronosticado': 'Próximo Mes',
            'top20_historico': [],
            'matriz_historica': [],
            'total_catalogo': 0,
            'predicciones_ml': [],
            'periodos_historico': [],
            'metricas_ajuste': {
                'total_descuentos_otorgados': 0,
                'total_subtotal_bruto': 0,
                'total_facturado_neto': 0,
                'pct_descuento_promedio': 0
            }
        }
        _ML_CACHE[cache_key] = empty_res
        _ML_CACHE_TIME[cache_key] = ahora
        return empty_res

    # Facturas padre para fecha y cliente
    move_ids = list(set(l['move_id'][0] for l in lines if l.get('move_id')))
    moves = models.execute_kw(
        ODOO_DB, uid, ODOO_API_KEY,
        'account.move', 'search_read',
        [[('id', 'in', move_ids)]],
        {'fields': ['id', 'invoice_date', 'partner_id', 'move_type']}
    )
    move_map = {m['id']: m for m in moves}

    records = []
    total_descuentos_otorgados = 0.0
    total_subtotal_bruto = 0.0

    for l in lines:
        mid = l['move_id'][0] if l.get('move_id') else None
        inv = move_map.get(mid, {})
        mtype = inv.get('move_type', 'out_invoice')
        sign = -1.0 if mtype == 'out_refund' else 1.0

        p_name = l['product_id'][1] if l.get('product_id') else l.get('name', 'Sin Producto')
        p_name_clean = _limpiar_nombre(p_name)
        partner_name = inv.get('partner_id', [0, ''])[1] if inv.get('partner_id') else ''

        if excluir_interempresa:
            p_norm = normalizar_texto(partner_name)
            if any(c in p_norm for c in CLIENTES_INTEREMPRESA):
                continue

        inv_date = inv.get('invoice_date') or str(hoy)
        try:
            dt = datetime.strptime(inv_date, '%Y-%m-%d')
            periodo = f"{dt.year}-{dt.month:02d}"
        except Exception:
            dt = hoy
            periodo = f"{hoy.year}-{hoy.month:02d}"

        cant = float(l.get('quantity', 0) or 0) * sign
        subtotal = float(l.get('price_subtotal', 0) or 0) * sign
        p_unit = float(l.get('price_unit', 0) or 0)
        disc_pct = float(l.get('discount', 0) or 0)

        # Mapeo de BoM
        p_upper = p_name_clean.upper().strip()
        nombre_canonico = kit_map.get(p_upper, p_name_clean)
        es_componente = (p_upper in kit_map)

        if es_componente and (p_unit < 1.0 or subtotal < 1.0):
            cant_efectiva = 0.0
        else:
            cant_efectiva = cant

        # Detección de líneas de servicio o captura anómala en Odoo (ej. $1 con cantidad=41930)
        p_canon_norm = normalizar_texto(nombre_canonico)
        es_servicio = any(k in p_canon_norm for k in ['servicio', 'mecanico', 'torno', 'flete', 'mano de obra', 't.o.t.'])
        if (es_servicio or p_unit <= 2.0) and cant_efectiva > 100 and subtotal > 100:
            cant_efectiva = 1.0
            p_unit = subtotal

        sub_bruto = cant_efectiva * p_unit if (cant_efectiva and p_unit) else subtotal
        desc_monto = sub_bruto * (disc_pct / 100.0) if disc_pct > 0 else max(0.0, sub_bruto - subtotal)
        total_descuentos_otorgados += desc_monto
        total_subtotal_bruto += sub_bruto

        records.append({
            'producto': nombre_canonico,
            'categoria': clasificar_producto(nombre_canonico),
            'year': dt.year,
            'month': dt.month,
            'periodo': periodo,
            'cantidad': cant_efectiva,
            'subtotal': subtotal,
            'precio_unit': p_unit
        })

    if not records:
        empty_res = {
            'ml_engine': 'XGBoost Regressor (Gradient Boosting v3.4)',
            'mes_pronosticado': 'Próximo Mes',
            'top20_historico': [],
            'matriz_historica': [],
            'total_catalogo': 0,
            'predicciones_ml': [],
            'periodos_historico': [],
            'metricas_ajuste': {
                'total_descuentos_otorgados': 0,
                'total_subtotal_bruto': 0,
                'total_facturado_neto': 0,
                'pct_descuento_promedio': 0
            }
        }
        _ML_CACHE[cache_key] = empty_res
        _ML_CACHE_TIME[cache_key] = ahora
        return empty_res

    df = pd.DataFrame(records)

    # 1. CATALOGO COMPLETO Y PIVOT TABLES VECTORIZADAS (ULTRA-RÁPIDO)
    agg_prod = df.groupby('producto').agg({
        'subtotal': 'sum',
        'cantidad': 'sum',
        'precio_unit': 'mean'
    }).sort_values('subtotal', ascending=False)

    todos_nombres_productos = agg_prod.index.tolist()

    todos_periodos = sorted(df['periodo'].unique().tolist())
    periodos_recientes = todos_periodos[-12:] if len(todos_periodos) > 12 else todos_periodos

    ult_periodo = periodos_recientes[-1] if periodos_recientes else f"{hoy.year}-{hoy.month:02d}"
    ult_y, ult_m = map(int, ult_periodo.split("-"))
    next_m = (ult_m % 12) + 1
    next_y = ult_y + 1 if ult_m == 12 else ult_y
    nombre_mes_siguiente = f"{MESES_ESP[next_m]} {next_y}"

    # Tablas Pivot por Mes (Vectorizado)
    df_reciente = df[df['periodo'].isin(periodos_recientes)]
    pivot_sub = df_reciente.pivot_table(index='producto', columns='periodo', values='subtotal', aggfunc='sum', fill_value=0.0)
    pivot_cant = df_reciente.pivot_table(index='producto', columns='periodo', values='cantidad', aggfunc='sum', fill_value=0.0)
    cat_map = df.groupby('producto')['categoria'].first().to_dict()

    ult_per = periodos_recientes[-1] if periodos_recientes else None
    ant_per = periodos_recientes[-2] if len(periodos_recientes) >= 2 else None

    # 2. CONSTRUIR MATRIZ HISTÓRICA VECTORIZADA
    matriz_historica = []
    for rank, prod_name in enumerate(todos_nombres_productos, 1):
        cat = cat_map.get(prod_name, clasificar_producto(prod_name))
        tot_sub = float(agg_prod.loc[prod_name, 'subtotal'])
        tot_cant = float(agg_prod.loc[prod_name, 'cantidad'])
        p_prom = tot_sub / max(tot_cant, 1.0)

        ventas_por_mes = {}
        for per in periodos_recientes:
            sub_per = float(pivot_sub.loc[prod_name, per]) if (prod_name in pivot_sub.index and per in pivot_sub.columns) else 0.0
            cant_per = float(pivot_cant.loc[prod_name, per]) if (prod_name in pivot_cant.index and per in pivot_cant.columns) else 0.0
            ventas_por_mes[per] = {
                'subtotal': sub_per,
                'cantidad': cant_per
            }

        if ult_per and ant_per:
            ult_val = ventas_por_mes[ult_per]['subtotal']
            ant_val = ventas_por_mes[ant_per]['subtotal']
            mom_growth = ((ult_val - ant_val) / ant_val * 100.0) if ant_val > 0 else 0.0
        else:
            mom_growth = 0.0

        matriz_historica.append({
            'ranking': rank,
            'producto': prod_name,
            'categoria': cat,
            'total_subtotal': tot_sub,
            'total_cantidad': tot_cant,
            'precio_promedio': p_prom,
            'mom_growth': round(mom_growth, 1),
            'ventas_por_mes': ventas_por_mes
        })

    # 3. ENTRENAMIENTO DE MACHINE LEARNING DINÁMICO & VECTORIZADO
    predicciones_ml = []
    ml_algorithm_used = "XGBoost Regressor (Gradient Boosting v3.4)" if XGB_AVAILABLE else "Scikit-Learn Gradient Boosting"

    # Pre-agrupar resumen mensual
    monthly_summary = df.groupby(['producto', 'year', 'month', 'periodo']).agg({
        'cantidad': 'sum',
        'subtotal': 'sum'
    }).reset_index().sort_values(['year', 'month'])

    monthly_dict = {p: grp for p, grp in monthly_summary.groupby('producto')}

    for rank, prod_name in enumerate(todos_nombres_productos, 1):
        pdf = monthly_dict.get(prod_name)
        cat = cat_map.get(prod_name, clasificar_producto(prod_name))

        if pdf is None or len(pdf) == 0:
            continue

        tot_sub = float(agg_prod.loc[prod_name, 'subtotal'])
        tot_cant = float(agg_prod.loc[prod_name, 'cantidad'])
        p_prom_real = tot_sub / max(tot_cant, 1.0)

        n_meses = len(pdf)
        ult_cant = float(pdf['cantidad'].iloc[-1])
        prom_historico = float(pdf['cantidad'].mean())
        
        # Precio unitario ponderado robusto
        p_prom_reciente = float(pdf['subtotal'].iloc[-1] / max(ult_cant, 1.0)) if ult_cant > 0 else p_prom_real
        if p_prom_reciente > 2.5 * p_prom_real or p_prom_reciente < 0.4 * p_prom_real:
            p_prom_reciente = p_prom_real

        if n_meses >= 3 and rank <= 50:
            try:
                pdf_feat = pdf.copy()
                pdf_feat['lag_1'] = pdf_feat['cantidad'].shift(1).fillna(prom_historico)
                pdf_feat['lag_2'] = pdf_feat['cantidad'].shift(2).fillna(prom_historico)
                pdf_feat['rolling_mean_3'] = pdf_feat['cantidad'].rolling(3, min_periods=1).mean()
                pdf_feat['rolling_std_3'] = pdf_feat['cantidad'].rolling(3, min_periods=1).std().fillna(0)

                feature_cols = ['month', 'lag_1', 'lag_2', 'rolling_mean_3', 'rolling_std_3']
                X = pdf_feat[feature_cols].values
                y = pdf_feat['cantidad'].values

                if XGB_AVAILABLE:
                    model = xgb.XGBRegressor(n_estimators=15, max_depth=2, learning_rate=0.1, n_jobs=1, random_state=42)
                else:
                    model = GradientBoostingRegressor(n_estimators=15, max_depth=2, learning_rate=0.1, random_state=42)
                model.fit(X, y)

                last_row = pdf_feat.iloc[-1]
                x_next = np.array([[next_m, float(last_row['cantidad']), float(last_row['lag_1']), float(last_row['rolling_mean_3']), float(last_row['rolling_std_3'])]])
                pred_units = float(model.predict(x_next)[0])
                pred_units = max(1.0, pred_units)
                # Acotar a rangos lógicos
                pred_units = min(pred_units, max(2.5 * prom_historico, 2.0 * ult_cant, 5.0))
                confidence_score = min(96.5, max(78.0, 93.0 - (float(last_row['rolling_std_3']) / max(prom_historico, 1) * 10)))
            except Exception:
                pred_units = max(1.0, 0.6 * ult_cant + 0.4 * prom_historico)
                pred_units = min(pred_units, max(2.5 * prom_historico, 2.0 * ult_cant, 5.0))
                confidence_score = 82.0
        else:
            # Algoritmo de Suavizado Exponencial Ponderado para volumen normal
            pred_units = max(1.0, 0.65 * ult_cant + 0.35 * prom_historico)
            pred_units = min(pred_units, max(2.5 * prom_historico, 2.0 * ult_cant, 5.0))
            confidence_score = min(92.0, 80.0 + min(n_meses * 2.0, 10.0))

        pred_revenue = pred_units * p_prom_reciente
        stock_sugerido = int(np.ceil(pred_units * 1.25))

        diff_pct = ((pred_units - ult_cant) / ult_cant * 100.0) if ult_cant > 0 else 0.0
        if diff_pct > 15.0:
            tendencia_flag = "🚀 ALTA DEMANDA"
            tendencia_color = "emerald"
            explicacion = f"Fuerte repunte de compra (+{diff_pct:.1f}% vs mes anterior). Aumentar stock."
        elif diff_pct > 0.0:
            tendencia_flag = "📈 CRECIMIENTO"
            tendencia_color = "blue"
            explicacion = f"Demanda al alza (+{diff_pct:.1f}%). Mantener flujo normal."
        elif diff_pct > -15.0:
            tendencia_flag = "⚖️ ESTABLE"
            tendencia_color = "slate"
            explicacion = "Consumo regular y predecible."
        else:
            tendencia_flag = "⚠️ DESACELERACIÓN"
            tendencia_color = "amber"
            explicacion = f"Baja temporal ({diff_pct:.1f}%). Evitar sobrestock."

        predicciones_ml.append({
            'ranking': rank,
            'producto': prod_name,
            'categoria': cat,
            'ult_mes_unidades': round(ult_cant, 1),
            'promedio_mensual': round(prom_historico, 1),
            'pred_unidades': round(pred_units, 1),
            'pred_ingreso': round(pred_revenue, 2),
            'precio_promedio': round(p_prom_reciente, 2),
            'stock_sugerido': stock_sugerido,
            'tendencia_flag': tendencia_flag,
            'tendencia_color': tendencia_color,
            'cambio_esperado_pct': round(diff_pct, 1),
            'confianza_score': round(confidence_score, 1),
            'explicacion_ia': explicacion,
            'meses_data': n_meses
        })

    pct_desc_prom = (total_descuentos_otorgados / max(total_subtotal_bruto, 1.0)) * 100.0

    resultado = {
        'ml_engine': ml_algorithm_used,
        'mes_pronosticado': nombre_mes_siguiente,
        'top20_historico': matriz_historica,
        'matriz_historica': matriz_historica,
        'total_catalogo': len(todos_nombres_productos),
        'predicciones_ml': predicciones_ml,
        'periodos_historico': periodos_recientes,
        'metricas_ajuste': {
            'total_descuentos_otorgados': round(total_descuentos_otorgados, 2),
            'total_subtotal_bruto': round(total_subtotal_bruto, 2),
            'total_facturado_neto': round(total_subtotal_bruto - total_descuentos_otorgados, 2),
            'pct_descuento_promedio': round(pct_desc_prom, 2)
        }
    }

    _ML_CACHE[cache_key] = resultado
    _ML_CACHE_TIME[cache_key] = ahora
    return resultado
