import sys
from odoo_sync_engine import conectar_odoo, ODOO_DB, ODOO_API_KEY, EMPRESAS, CLIENTES_INTEREMPRESA_EXCLUIDOS, normalizar_texto, obtener_mapa_kits_odoo, _limpiar_nombre, clasificar_producto

def test_engine_refactor(fecha_ini, fecha_fin, empresa="TODAS (Consolidado)", excluir_inter=True):
    empresa_cfg = EMPRESAS.get(empresa)
    cid = empresa_cfg["company_id"] if empresa_cfg else None
    prefijos_excluir = empresa_cfg["prefijos_excluir"] if empresa_cfg else []

    uid, models = conectar_odoo(cid or 1)
    kit_map = obtener_mapa_kits_odoo(models, uid)

    domain = [
        ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
        ("move_id.state", "=", "posted"),
        ("display_type", "=", "product"),
        ("date", ">=", fecha_ini),
        ("date", "<=", fecha_fin),
    ]
    if cid: domain.append(("company_id", "=", cid))

    fields = ["id", "product_id", "name", "quantity", "price_unit", "price_subtotal", "move_id", "date", "partner_id", "product_uom_id", "company_id"]
    lineas_raw = models.execute_kw(ODOO_DB, uid, ODOO_API_KEY, "account.move.line", "search_read", [domain], {"fields": fields, "limit": 10000})

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
    monto_neto = 0.0
    cantidad_bruta = 0.0
    cantidad_devuelta = 0.0
    cantidad_neta = 0.0
    n_excluidos = 0

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

        if excluir_inter and any(c_ex in partner_norm for c_ex in CLIENTES_INTEREMPRESA_EXCLUIDOS):
            n_excluidos += 1
            continue

        prod_info = lin.get("product_id")
        if not prod_info:
            continue

        vendedor_name = (mv.get("invoice_user_id") or [None, "Venta Directa / Sin Asignar"])[1]
        empresa_lin = (lin.get("company_id") or mv.get("company_id") or [None, "Empresa"])[1]
        fecha_lin = lin.get("date") or mv.get("invoice_date") or ""

        raw_pname = prod_info[1]
        nombre_limpio = _limpiar_nombre(raw_pname)
        nombre_canonico = kit_map.get(nombre_limpio, nombre_limpio)
        clave_prod = normalizar_texto(nombre_canonico)

        cant = float(lin.get("quantity", 0.0) or 0)
        subtotal = float(lin.get("price_subtotal", 0.0) or 0)
        precio_u = float(lin.get("price_unit", 0.0) or 0)
        uom_name = (lin.get("product_uom_id") or [None, "Pza"])[1]

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
        else:
            facturas_unicas.add(mname)
            monto_bruto += subtotal
            cantidad_bruta += cant_efectiva

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
            subtotal_signed = -subtotal
            cant_signed = -cant_efectiva
        else:
            pdata["cantidad_bruta"] += cant_efectiva
            pdata["subtotal_bruto"] += subtotal
            pdata["facturas"].add(mname)
            if precio_u >= 1.0:
                pdata["precios"].append(precio_u)
            subtotal_signed = subtotal
            cant_signed = cant_efectiva

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

        # Sales line record
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
    for clave, data in productos_dict.items():
        precios = data["precios"]
        precio_prom = (sum(precios) / len(precios)) if precios else 0.0
        pct_monto = (data["subtotal_bruto"] / monto_bruto * 100) if monto_bruto > 0 else 0.0

        # Top clients list
        clientes_lista = sorted(
            [{"cliente": k, "cantidad": v["cantidad"], "subtotal": v["subtotal"], "num_facturas": len(v["facturas"])} for k, v in data["clientes_map"].items()],
            key=lambda x: x["subtotal"], reverse=True
        )

        # Top sellers list
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

    # Sort catalog products first, then adjustments
    productos_catalogo = [p for p in lista_productos if not p["es_ajuste"]]
    ajustes_lista = [p for p in lista_productos if p["es_ajuste"]]

    productos_catalogo.sort(key=lambda x: x["subtotal"], reverse=True)
    for i, p in enumerate(productos_catalogo, 1):
        p["posicion"] = i

    for i, p in enumerate(ajustes_lista, len(productos_catalogo) + 1):
        p["posicion"] = i

    productos_final = productos_catalogo + ajustes_lista

    print("=== RESULTADO ENGINE REFACTOR ===")
    print(f"Monto Bruto Facturado: ${monto_bruto:,.2f}")
    print(f"Monto Notas de Credito: -${monto_nc:,.2f}")
    print(f"Monto Neto Real: ${monto_neto:,.2f}")
    print(f"Total Facturas: {len(facturas_unicas)}, Total NCs: {len(ncs_unicas)}")
    print(f"Productos Catalogo: {len(productos_catalogo)}, Ajustes: {len(ajustes_lista)}")
    print("\nTop 5 Catalogo:")
    for p in productos_catalogo[:5]:
        print(f"  #{p['posicion']} {p['nombre']} | Subtotal: ${p['subtotal']:,.2f} | Clientes: {p['num_clientes']} | Facturas: {p['num_facturas']} | Líneas detalle: {len(p['lineas'])}")

test_engine_refactor("2026-09-01", "2026-09-30", "TODAS (Consolidado)", False)
