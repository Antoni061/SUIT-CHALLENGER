import sys
from odoo_sync_engine import conectar_odoo, ODOO_DB, ODOO_API_KEY, EMPRESAS, CLIENTES_INTEREMPRESA_EXCLUIDOS, normalizar_texto, obtener_mapa_kits_odoo, _limpiar_nombre, clasificar_producto

uid, models = conectar_odoo(1)

domain = [
    ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
    ('move_id.state', '=', 'posted'),
    ('display_type', '=', 'product'),
    ('date', '>=', '2026-09-01'),
    ('date', '<=', '2026-09-30')
]
fields = ['id', 'product_id', 'name', 'quantity', 'price_unit', 'price_subtotal', 'move_id', 'date', 'partner_id', 'product_uom_id', 'company_id']
lines = models.execute_kw(ODOO_DB, uid, ODOO_API_KEY, 'account.move.line', 'search_read', [domain], {'fields': fields, 'limit': 10000})

move_ids = list(set([l['move_id'][0] for l in lines if l.get('move_id')]))
moves = models.execute_kw(ODOO_DB, uid, ODOO_API_KEY, 'account.move', 'search_read', [[('id', 'in', move_ids)]], {'fields': ['id', 'name', 'move_type', 'invoice_user_id', 'partner_id', 'amount_untaxed', 'amount_total', 'company_id']})
move_map = {m['id']: m for m in moves}

print(f"Total lineas: {len(lines)}, Total facturas/NCs: {len(moves)}")

inv_lines = [l for l in lines if move_map.get(l['move_id'][0], {}).get('move_type') == 'out_invoice']
ref_lines = [l for l in lines if move_map.get(l['move_id'][0], {}).get('move_type') == 'out_refund']

print(f"Lineas de Facturas (out_invoice): {len(inv_lines)}")
print(f"Lineas de Notas de Credito (out_refund): {len(ref_lines)}")

total_inv_subtotal = sum(l['price_subtotal'] for l in inv_lines)
total_ref_subtotal = sum(l['price_subtotal'] for l in ref_lines)

print(f"Subtotal Facturas brutas: {total_inv_subtotal:,.2f}")
print(f"Subtotal NCs / Devoluciones: {total_ref_subtotal:,.2f}")
print(f"Subtotal Neto (Facturas - NCs): {(total_inv_subtotal - total_ref_subtotal):,.2f}")

inv_clean = []
for l in inv_lines:
    pname = (l.get('partner_id') or [None, ''])[1]
    if any(c in normalizar_texto(pname) for c in CLIENTES_INTEREMPRESA_EXCLUIDOS):
        continue
    inv_clean.append(l)

ref_clean = []
for l in ref_lines:
    pname = (l.get('partner_id') or [None, ''])[1]
    if any(c in normalizar_texto(pname) for c in CLIENTES_INTEREMPRESA_EXCLUIDOS):
        continue
    ref_clean.append(l)

print("--- EXCLUYENDO INTEREMPRESA ---")
print(f"Facturas limpias subtotal: {sum(l['price_subtotal'] for l in inv_clean):,.2f}")
print(f"NCs limpias subtotal: {sum(l['price_subtotal'] for l in ref_clean):,.2f}")
print(f"Neto limpio: {(sum(l['price_subtotal'] for l in inv_clean) - sum(l['price_subtotal'] for l in ref_clean)):,.2f}")

# Now let's see what "DEVOLUCION DE MATERIAL" is in ref_lines or inv_lines
dev_lines = [l for l in lines if 'DEVOLUCION' in (l.get('name') or '').upper() or 'DEVOLUCION' in str(l.get('product_id')).upper()]
print(f"\nLineas con 'DEVOLUCION': {len(dev_lines)}")
for dl in dev_lines:
    mv = move_map.get(dl['move_id'][0], {})
    print(f"  Move: {mv.get('name')} (type: {mv.get('move_type')}), Prod: {dl.get('product_id')}, Desc: {dl.get('name')}, Qty: {dl.get('quantity')}, Subtotal: {dl.get('price_subtotal')}")
