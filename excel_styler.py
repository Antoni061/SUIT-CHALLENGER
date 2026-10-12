"""
EXCEL STYLER ENGINE — MASTER SUITE ERP (Challenger Automotive)
=============================================================
Motor de diseño ejecutivo para hojas de cálculo Excel (openpyxl).
Genera reportes con estética visual corporativa moderna:
- Banners ejecutivos y encabezados de marca
- Tarjetas de KPIs visuales con métricas clave
- Tablas con bandas de color (Zebra striping)
- Insignias de colores para marcas y estados (Verde, Azul, Ámbar, Púrpura)
- Formato contable para monedas ($#,##0.00), números (#,##0) y porcentajes (0.0%)
- Auto-ajuste de anchos de columna y cuadrículas activas
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
def fmt_mxn(val):
    try: return f"${val:,.2f}"
    except: return "$0.00"

def fmt_num(val):
    try: return f"{int(val):,}" if isinstance(val, (int, float)) and float(val).is_integer() else f"{val:,.1f}"
    except: return "0"

# ── PALETA DE COLORES CORPORATIVA ──────────────────────────────────────────
COLOR_SLATE_DARK    = "0F172A"  # Navy / Slate profundo
COLOR_SLATE_HEADER  = "1E293B"  # Encabezados principales
COLOR_PURPLE_HEADER = "581C87"  # Machine Learning
COLOR_BLUE_HEADER   = "1E3A8A"  # Históricos
COLOR_AMBER_HEADER  = "92400E"  # Ajustes / Advertencias
COLOR_EMERALD_HEADER= "065F46"  # Cobranza / Éxito

COLOR_ZEBRA_LIGHT   = "F8FAFC"  # Fila par
COLOR_WHITE         = "FFFFFF"  # Fila impar
COLOR_TOTAL_ROW     = "E2E8F0"  # Fila de totales

# Insignias / Badges
BADGE_STYLES = {
    "CHALLENGER":        {"fill": "DBEAFE", "font": "1E40AF"}, # Azul suave
    "MULTIMARCA":        {"fill": "E2E8F0", "font": "334155"}, # Gris slate
    "PASTA":             {"fill": "F3E8FF", "font": "6B21A8"}, # Púrpura suave
    "MATERIA PRIMA":     {"fill": "FEF3C7", "font": "92400E"}, # Ámbar suave
    "🚀 ALTA DEMANDA":   {"fill": "D1FAE5", "font": "065F46"}, # Verde esmeralda
    "📈 CRECIMIENTO":    {"fill": "DBEAFE", "font": "1E40AF"}, # Azul
    "⚖️ ESTABLE":        {"fill": "F1F5F9", "font": "475569"}, # Gris
    "⚠️ DESACELERACIÓN": {"fill": "FEF3C7", "font": "92400E"}, # Ámbar
    "🟢 Al Día":         {"fill": "D1FAE5", "font": "065F46"},
    "🟡 1-30d tarde":    {"fill": "FEF3C7", "font": "92400E"},
    "🟠 31-60d vencido": {"fill": "FFEDD5", "font": "9A3412"},
    "🔴 61-90d vencido": {"fill": "FEE2E2", "font": "991B1B"},
    "🚨 Moroso >90d":    {"fill": "FEE2E2", "font": "991B1B"}
}

# Bordes
THIN_SIDE = Side(style="thin", color="CBD5E1")
DOUBLE_BOTTOM_SIDE = Side(style="double", color="0F172A")
BORDER_CELL = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)
BORDER_TOTAL = Border(top=THIN_SIDE, bottom=DOUBLE_BOTTOM_SIDE, left=THIN_SIDE, right=THIN_SIDE)


def aplicar_estilo_banner(ws, titulo, subtitulo, num_columnas=9, tema_color=COLOR_SLATE_DARK):
    """Crea un banner ejecutivo superior estilizado."""
    ws.views.sheetView[0].showGridLines = True
    
    col_fin = get_column_letter(max(num_columnas, 6))
    
    # Fila 1: Título Principal
    ws.merge_cells(f"A1:{col_fin}1")
    cell_t = ws["A1"]
    cell_t.value = f"  {titulo.upper()}"
    cell_t.font = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    cell_t.fill = PatternFill("solid", fgColor=tema_color)
    cell_t.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 32

    # Fila 2: Subtítulo y Metadatos
    ws.merge_cells(f"A2:{col_fin}2")
    cell_s = ws["A2"]
    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    cell_s.value = f"  {subtitulo} | Generado: {fecha_hoy} | Challenger ERP Suite"
    cell_s.font = Font(name="Segoe UI", size=9, italic=True, color="CBD5E1")
    cell_s.fill = PatternFill("solid", fgColor="1E293B")
    cell_s.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[2].height = 20

    # Fila 3 en blanco
    ws.row_dimensions[3].height = 10


def agregar_seccion_kpis(ws, kpis, start_row=4):
    """
    Agrega tarjetas de KPIs en una fila horizontal estilizada.
    kpis: list of dicts [{'label': 'Total Facturado', 'value': '$1,200,000.00', 'color': '065F46'}, ...]
    """
    if not kpis:
        return start_row

    n = len(kpis)
    col_idx = 1
    for kpi in kpis:
        c_let1 = get_column_letter(col_idx)
        c_let2 = get_column_letter(col_idx + 1)
        
        ws.merge_cells(f"{c_let1}{start_row}:{c_let2}{start_row}")
        c_lbl = ws[f"{c_let1}{start_row}"]
        c_lbl.value = kpi.get("label", "").upper()
        c_lbl.font = Font(name="Segoe UI", size=8, bold=True, color="64748B")
        c_lbl.fill = PatternFill("solid", fgColor="F1F5F9")
        c_lbl.alignment = Alignment(horizontal="center", vertical="center")

        ws.merge_cells(f"{c_let1}{start_row+1}:{c_let2}{start_row+1}")
        c_val = ws[f"{c_let1}{start_row+1}"]
        c_val.value = kpi.get("value", "")
        fg_col = kpi.get("text_color", "0F172A")
        c_val.font = Font(name="Segoe UI", size=13, bold=True, color=fg_col)
        c_val.fill = PatternFill("solid", fgColor="F8FAFC")
        c_val.alignment = Alignment(horizontal="center", vertical="center")

        # Bordes de tarjeta
        for r in range(start_row, start_row + 2):
            for c in range(col_idx, col_idx + 2):
                cell = ws.cell(row=r, column=c)
                cell.border = BORDER_CELL

        col_idx += 2

    ws.row_dimensions[start_row].height = 18
    ws.row_dimensions[start_row + 1].height = 28
    ws.row_dimensions[start_row + 2].height = 12

    return start_row + 3


def agregar_tabla_ejecutiva(ws, start_row, headers, rows, formatos=None, tema_color=COLOR_SLATE_HEADER, totales_row=None):
    """
    Agrega una tabla estilizada con encabezados, filas zebra y totales.
    formatos: dict {col_idx (1-based): 'currency' | 'number' | 'percent' | 'badge' | 'center' | 'left' | 'right'}
    """
    formatos = formatos or {}
    
    # 1. Encabezados
    ws.row_dimensions[start_row].height = 26
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=col_idx, value=h)
        cell.font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=tema_color)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER_CELL

    # 2. Filas de Datos
    curr_row = start_row + 1
    for r_idx, row_data in enumerate(rows):
        ws.row_dimensions[curr_row].height = 20
        is_even = (r_idx % 2 == 0)
        bg_color = COLOR_WHITE if is_even else COLOR_ZEBRA_LIGHT
        
        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=curr_row, column=col_idx)
            cell.border = BORDER_CELL
            
            fmt_type = formatos.get(col_idx, "left")
            cell_fill = PatternFill("solid", fgColor=bg_color)
            cell_font = Font(name="Segoe UI", size=9, color="1E293B")
            align_h = "left"

            # Formato Badge
            str_val = str(val).strip() if val is not None else ""
            if str_val in BADGE_STYLES:
                badge_info = BADGE_STYLES[str_val]
                cell_fill = PatternFill("solid", fgColor=badge_info["fill"])
                cell_font = Font(name="Segoe UI", size=9, bold=True, color=badge_info["font"])
                align_h = "center"
                cell.value = val
            elif fmt_type == "currency":
                try:
                    cell.value = float(val) if val is not None else 0.0
                    cell.number_format = '"$"#,##0.00'
                    align_h = "right"
                    cell_font = Font(name="Segoe UI", size=9, bold=True, color="0F172A")
                except (ValueError, TypeError):
                    cell.value = val
                    align_h = "right"
            elif fmt_type == "number":
                try:
                    cell.value = float(val) if val is not None else 0
                    cell.number_format = '#,##0'
                    align_h = "right"
                except (ValueError, TypeError):
                    cell.value = val
                    align_h = "right"
            elif fmt_type == "percent":
                try:
                    num_val = float(str(val).replace("%", "").replace("+", "").strip())
                    cell.value = num_val / 100.0 if abs(num_val) > 1.0 else num_val
                    cell.number_format = '0.0%'
                    align_h = "center"
                    if num_val > 0:
                        cell_font = Font(name="Segoe UI", size=9, bold=True, color="065F46")
                    elif num_val < 0:
                        cell_font = Font(name="Segoe UI", size=9, bold=True, color="991B1B")
                except (ValueError, TypeError):
                    cell.value = val
                    align_h = "center"
            elif fmt_type == "center":
                cell.value = val
                align_h = "center"
            elif fmt_type == "right":
                cell.value = val
                align_h = "right"
            else:
                cell.value = val
                align_h = "left"

            cell.fill = cell_fill
            cell.font = cell_font
            cell.alignment = Alignment(horizontal=align_h, vertical="center")

        curr_row += 1

    # 3. Fila de Totales si se provee
    if totales_row:
        ws.row_dimensions[curr_row].height = 24
        for col_idx, val in enumerate(totales_row, 1):
            cell = ws.cell(row=curr_row, column=col_idx)
            cell.fill = PatternFill("solid", fgColor=COLOR_TOTAL_ROW)
            cell.border = BORDER_TOTAL
            fmt_type = formatos.get(col_idx, "left")
            align_h = "left"

            if fmt_type == "currency":
                try:
                    cell.value = float(val) if val is not None else 0.0
                    cell.number_format = '"$"#,##0.00'
                    align_h = "right"
                except (ValueError, TypeError):
                    cell.value = val
                    align_h = "right"
            elif fmt_type == "number":
                try:
                    cell.value = float(val) if val is not None else 0
                    cell.number_format = '#,##0'
                    align_h = "right"
                except (ValueError, TypeError):
                    cell.value = val
                    align_h = "right"
            elif fmt_type == "center":
                cell.value = val
                align_h = "center"
            else:
                cell.value = val
                align_h = "left"

            cell.font = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
            cell.alignment = Alignment(horizontal=align_h, vertical="center")

        curr_row += 1

    # Autoajustar columnas
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_l = 0
        for cell in col:
            val_s = str(cell.value or "")
            if cell.number_format and '"$"#' in cell.number_format:
                val_s = f"${val_s}.00"
            max_l = max(max_l, len(val_s))
        ws.column_dimensions[col_letter].width = max(max_l + 4, 12)

    return curr_row
