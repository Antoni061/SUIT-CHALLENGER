import sys
from odoo_sync_engine import obtener_cartera_cobranza_engine

data = obtener_cartera_cobranza_engine('BALDOMERO MEDINA GARZA', 'TODOS', 'TODOS', True, True)
print("=== TOTALES CARTERA BALDOMERO ===")
tot = data['totales']
print(f"Saldo Total Cartera: ${tot['saldo_total']:,.2f}")
print(f"  - 0 a 60 días: ${tot['saldo_reciente_0_60']:,.2f} ({tot['count_reciente_0_60']} facs)")
print(f"  - 60 a 100 días: ${tot['saldo_pasada_60_100']:,.2f} ({tot['count_pasada_60_100']} facs)")
print(f"  - Más de 100 días: ${tot['saldo_atrasada_100_mas']:,.2f} ({tot['count_atrasada_100_mas']} facs)")
print(f"  - Al día (no vencidas): ${tot['saldo_al_dia']:,.2f} ({tot['count_al_dia']} facs)")
print(f"Suma de buckets: ${(tot['saldo_reciente_0_60'] + tot['saldo_pasada_60_100'] + tot['saldo_atrasada_100_mas'] + tot['saldo_al_dia']):,.2f}")

print("\n=== MATRIZ DE MESES ===")
meses_cob = data['cobrado_por_mes']['meses']
for m in meses_cob:
    print(f"Mes: {m['mes_nombre']:15s} | Vencen: ${m['cobranza_estimada_vence']:12,.2f} ({m['facturas_vencen_count']:3d} facs) | Cobrado Vencidas: ${m['cobrado_de_vencidas']:12,.2f} | Pendiente Vencidas: ${m['saldo_pendiente_vencidas']:12,.2f} | Pagos Banco: ${m['cobrado_real_pagos']:12,.2f} ({m['num_pagos_recibidos']:3d} pagos) | Clientes: {m['num_clientes']}")

print("\n=== DETALLE CLIENTES AGOSTO 2026 ===")
ago = next((m for m in meses_cob if m['mes_key'] == '2026-08'), None)
if ago:
    print(f"Total clientes con vencimiento o pagos en Agosto: {len(ago['clientes'])}")
    clis_vencen = [c for c in ago['clientes'] if c['total_estimado_vence'] > 0]
    print(f"Clientes con facturas que vencieron en Agosto: {len(clis_vencen)}")
    for i, c in enumerate(clis_vencen[:10], 1):
        print(f"  {i:2d}. {c['cliente_nombre'][:30]:30s} | Vence: ${c['total_estimado_vence']:10,.2f} | Cobrado: ${c['total_cobrado_vencidas']:10,.2f} | Pendiente: ${c['saldo_pendiente_vencidas']:10,.2f} | Facs: {c['num_facturas_vence']}")
