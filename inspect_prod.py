from test_engine_refactor import test_engine_refactor
from odoo_sync_engine import conectar_odoo, ODOO_DB, ODOO_API_KEY, EMPRESAS, CLIENTES_INTEREMPRESA_EXCLUIDOS, normalizar_texto, obtener_mapa_kits_odoo, _limpiar_nombre, clasificar_producto

uid, models = conectar_odoo(1)
kit_map = obtener_mapa_kits_odoo(models, uid)

domain = [
    ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
    ("move_id.state", "=", "posted"),
    ("display_type", "=", "product"),
    ("date", ">=", "2026-09-01"),
    ("date", "<=", "2026-09-30"),
]
fields = ["id", "product_id", "name", "quantity", "price_unit", "price_subtotal", "move_id", "date", "partner_id", "product_uom_id", "company_id"]
lineas_raw = models.execute_kw(ODOO_DB, uid, ODOO_API_KEY, "account.move.line", "search_read", [domain], {"fields": fields, "limit": 10000})

move_ids = list(set([l["move_id"][0] for l in lineas_raw if l.get("move_id")]))
moves_raw = models.execute_kw(
    ODOO_DB, uid, ODOO_API_KEY, "account.move", "search_read",
    [[("id", "in", move_ids)]],
    {"fields": ["id", "name", "move_type", "invoice_user_id", "partner_id", "company_id", "date", "invoice_date"]}
)
move_map = {m["id"]: m for m in moves_raw}

def print_prod_sales(target_name):
    print(f"\n==========================================")
    print(f"DETALLE DE VENTAS: {target_name}")
    print(f"==========================================")
    found_lines = []
    for lin in lineas_raw:
        prod_info = lin.get("product_id")
        if not prod_info: continue
        raw_pname = prod_info[1]
        n_limpio = _limpiar_nombre(raw_pname)
        n_canonico = kit_map.get(n_limpio, n_limpio)
        if target_name.upper() in n_canonico.upper():
            mid = lin["move_id"][0]
            mv = move_map.get(mid, {})
            pname = (lin.get("partner_id") or mv.get("partner_id") or [None, "Sin Cliente"])[1]
            vname = (mv.get("invoice_user_id") or [None, "Venta Directa"])[1]
            cname = (lin.get("company_id") or mv.get("company_id") or [None, "Empresa"])[1]
            found_lines.append({
                "fecha": lin.get("date"),
                "factura": mv.get("name"),
                "tipo": mv.get("move_type"),
                "cliente": pname,
                "vendedor": vname,
                "empresa": cname,
                "cant": lin.get("quantity"),
                "pu": lin.get("price_unit"),
                "subtotal": lin.get("price_subtotal")
            })
    print(f"Total registros encontrados: {len(found_lines)}")
    tot_sub = sum(l['subtotal'] for l in found_lines)
    tot_cant = sum(l['cant'] for l in found_lines)
    print(f"Total Importe: ${tot_sub:,.2f} | Total Cantidad: {tot_cant:,.1f}")
    print("\nPrimeras 10 ventas:")
    for l in found_lines[:10]:
        print(f"  {l['fecha']} | {l['factura']:18s} | {l['tipo']} | Cliente: {l['cliente'][:25]:25s} | Vend: {l['vendedor'][:20]:20s} | Cant: {l['cant']:5.1f} | PU: ${l['pu']:7.2f} | Sub: ${l['subtotal']:9.2f}")

print_prod_sales("KIT GLOSS LT")
print_prod_sales("KIT TPP 5000 LT")
