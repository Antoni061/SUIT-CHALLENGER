import sys
from odoo_sync_engine import conectar_odoo, ODOO_DB, ODOO_API_KEY, EMPRESAS, CLIENTES_INTEREMPRESA_EXCLUIDOS, normalizar_texto, obtener_mapa_kits_odoo, _limpiar_nombre, clasificar_producto

uid, models = conectar_odoo(1)

# Fetch all moves in Sept 2026
move_domain = [
    ('move_type', 'in', ['out_invoice', 'out_refund']),
    ('state', '=', 'posted'),
    ('date', '>=', '2026-09-01'),
    ('date', '<=', '2026-09-30')
]
moves = models.execute_kw(
    ODOO_DB, uid, ODOO_API_KEY,
    'account.move', 'search_read', [move_domain],
    {'fields': ['id', 'name', 'move_type', 'invoice_user_id', 'partner_id', 'amount_untaxed', 'amount_total', 'company_id', 'date', 'invoice_date']}
)
print(f"Total Moves: {len(moves)}")

move_dict = {m['id']: m for m in moves}

# Fetch all move lines
line_domain = [
    ('move_id', 'in', [m['id'] for m in moves]),
    ('display_type', '=', 'product')
]
lines = models.execute_kw(
    ODOO_DB, uid, ODOO_API_KEY,
    'account.move.line', 'search_read', [line_domain],
    {'fields': ['id', 'move_id', 'product_id', 'name', 'quantity', 'price_unit', 'price_subtotal', 'date', 'partner_id', 'product_uom_id', 'company_id']}
)
print(f"Total Lines: {len(lines)}")

kit_map = obtener_mapa_kits_odoo(models, uid)

# Analyze products
prod_summary = {}
sales_by_product = {}

CONCEPTOS_AJUSTES = {'DEVOLUCION DE MATERIAL', 'DESCUENTO', 'AJUSTE', 'ANTICIPO', 'REDONDEO'}

for lin in lines:
    mid = lin['move_id'][0] if lin.get('move_id') else None
    mv = move_dict.get(mid, {})
    mtype = mv.get('move_type', 'out_invoice')
    mname = mv.get('name', '')
    pname = (lin.get('partner_id') or mv.get('partner_id') or [None, 'Sin Cliente'])[1]
    vname = (mv.get('invoice_user_id') or [None, 'Venta Directa'])[1]
    cname = (lin.get('company_id') or mv.get('company_id') or [None, 'Empresa'])[1]
    fecha = lin.get('date') or mv.get('invoice_date') or ''

    # Intercompany check
    if any(c in normalizar_texto(pname) for c in CLIENTES_INTEREMPRESA_EXCLUIDOS):
        continue

    prod_info = lin.get('product_id')
    if not prod_info:
        continue

    raw_pname = prod_info[1]
    nombre_limpio = _limpiar_nombre(raw_pname)
    nombre_canonico = kit_map.get(nombre_limpio, nombre_limpio)
    
    cant = float(lin.get('quantity', 0.0) or 0)
    subtotal = float(lin.get('price_subtotal', 0.0) or 0)
    precio_u = float(lin.get('price_unit', 0.0) or 0)
    uom = (lin.get('product_uom_id') or [None, 'Pza'])[1]

    # If it is a credit note (out_refund), the subtotal and cant are negative (or refund)
    sign = -1.0 if mtype == 'out_refund' else 1.0
    subtotal_neto = subtotal * sign
    cant_neta = cant * sign

    is_nc_adjustment = any(adj in nombre_canonico.upper() for adj in CONCEPTOS_AJUSTES)

    if nombre_canonico not in prod_summary:
        prod_summary[nombre_canonico] = {
            'nombre': nombre_canonico,
            'clasificacion': clasificar_producto(nombre_canonico),
            'cant_bruta': 0.0,
            'subtotal_bruto': 0.0,
            'cant_devuelta': 0.0,
            'subtotal_nc': 0.0,
            'subtotal_neto': 0.0,
            'facturas': set(),
            'ncs': set(),
            'clientes': set(),
            'vendedores': set(),
            'is_adjustment': is_nc_adjustment,
            'uom': uom
        }

    if mtype == 'out_invoice':
        prod_summary[nombre_canonico]['cant_bruta'] += cant
        prod_summary[nombre_canonico]['subtotal_bruto'] += subtotal
        prod_summary[nombre_canonico]['facturas'].add(mname)
    else:
        prod_summary[nombre_canonico]['cant_devuelta'] += cant
        prod_summary[nombre_canonico]['subtotal_nc'] += subtotal
        prod_summary[nombre_canonico]['ncs'].add(mname)

    prod_summary[nombre_canonico]['subtotal_neto'] += subtotal_neto
    prod_summary[nombre_canonico]['clientes'].add(pname)
    prod_summary[nombre_canonico]['vendedores'].add(vname)

# Sort by subtotal bruto (or neto)
sorted_prods = sorted(prod_summary.values(), key=lambda x: x['subtotal_bruto'], reverse=True)

print("\n=== TOP 15 PRODUCTOS (SEPTIEMBRE 2026 - BRUTO Y NETO) ===")
for i, p in enumerate(sorted_prods[:15], 1):
    print(f"{i:2d}. {p['nombre'][:35]:35s} | Bruto: ${p['subtotal_bruto']:10,.2f} ({p['cant_bruta']:6.1f} {p['uom']}) | NC: -${p['subtotal_nc']:8,.2f} | Neto: ${p['subtotal_neto']:10,.2f} | Clientes: {len(p['clientes'])} | Facturas: {len(p['facturas'])}")
