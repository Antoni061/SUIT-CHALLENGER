"""
PDF STYLER ENGINE — MASTER SUITE ERP (Challenger Automotive)
===========================================================
Motor de generación de reportes ejecutivos en PDF de alta calidad con ReportLab.
Diseño moderno para juntas directivas:
- Encabezados y banners corporativos de marca
- Tarjetas visuales de KPIs y métricas clave
- Tablas con bandas de color (Zebra), semáforos y badges
- Formato contable para importes ($#,##0.00) y unidades
- Paginación dinámica (Página X de Y) y pie de página confidencial
"""

import os
import tempfile
from datetime import datetime

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# ── COLORES CORPORATIVOS ────────────────────────────────────────────────────
C_SLATE_DARK    = colors.HexColor("#0F172A")
C_SLATE_HEADER  = colors.HexColor("#1E293B")
C_PURPLE_HEADER = colors.HexColor("#581C87")
C_BLUE_HEADER   = colors.HexColor("#1E3A8A")
C_AMBER_HEADER  = colors.HexColor("#92400E")
C_EMERALD_HEADER= colors.HexColor("#065F46")
C_RED_HEADER    = colors.HexColor("#991B1B")

C_ZEBRA_LIGHT   = colors.HexColor("#F8FAFC")
C_WHITE         = colors.HexColor("#FFFFFF")
C_BORDER        = colors.HexColor("#CBD5E1")
C_TOTAL_BG      = colors.HexColor("#E2E8F0")

# Badges
BADGE_BG_COLORS = {
    "CHALLENGER":        colors.HexColor("#DBEAFE"),
    "MULTIMARCA":        colors.HexColor("#E2E8F0"),
    "PASTA":             colors.HexColor("#F3E8FF"),
    "MATERIA PRIMA":     colors.HexColor("#FEF3C7"),
    "🚀 ALTA DEMANDA":   colors.HexColor("#D1FAE5"),
    "📈 CRECIMIENTO":    colors.HexColor("#DBEAFE"),
    "⚖️ ESTABLE":        colors.HexColor("#F1F5F9"),
    "⚠️ DESACELERACIÓN": colors.HexColor("#FEF3C7"),
    "🟢 Al Día":         colors.HexColor("#D1FAE5"),
    "🟡 1-30d tarde":    colors.HexColor("#FEF3C7"),
    "🟠 31-60d vencido": colors.HexColor("#FFEDD5"),
    "🔴 61-90d vencido": colors.HexColor("#FEE2E2"),
    "🚨 Moroso >90d":    colors.HexColor("#FEE2E2")
}


class NumberedCanvas(canvas.Canvas):
    """Canvas de dos pasadas para calcular e imprimir 'Página X de Y'."""
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Línea separadora de pie de página
        page_w, page_h = self._pagesize
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 30, page_w - 36, 30)

        # Texto del pie
        texto_izq = "CHALLENGER AUTOMOTIVE ERP SUITE | Documento Oficial y Confidencial"
        texto_der = f"Página {self._pageNumber} de {page_count}"
        
        self.drawString(36, 18, texto_izq)
        self.drawRightString(page_w - 36, 18, texto_der)
        self.restoreState()


def _get_pdf_styles():
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='ExecTitle',
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.white
    ))
    styles.add(ParagraphStyle(
        name='ExecSubtitle',
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#CBD5E1")
    ))
    styles.add(ParagraphStyle(
        name='KPILabel',
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#64748B"),
        alignment=1
    ))
    styles.add(ParagraphStyle(
        name='KPIValue',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
        alignment=1
    ))
    styles.add(ParagraphStyle(
        name='TableCell',
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1E293B")
    ))
    styles.add(ParagraphStyle(
        name='TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A")
    ))
    styles.add(ParagraphStyle(
        name='TableCellCenter',
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1E293B"),
        alignment=1
    ))
    styles.add(ParagraphStyle(
        name='TableCellCenterBold',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A"),
        alignment=1
    ))
    styles.add(ParagraphStyle(
        name='TableCellRight',
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1E293B"),
        alignment=2
    ))
    styles.add(ParagraphStyle(
        name='TableHdr',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0F172A")
    ))
    return styles


def _crear_banner_flujo(titulo, subtitulo, ancho_total=720, color_fondo=C_SLATE_DARK, styles=None):
    """Genera un banner ejecutivo superior en formato tabla Flowable."""
    styles = styles or _get_pdf_styles()
    fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    p_tit = Paragraph(titulo.upper(), styles['ExecTitle'])
    p_sub = Paragraph(f"{subtitulo}  |  Generado: {fecha_str}  |  Challenger ERP Suite", styles['ExecSubtitle'])
    
    t_data = [[p_tit], [p_sub]]
    t = Table(t_data, colWidths=[ancho_total])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), color_fondo),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#1E293B")),
        ('PADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('PADDING', (0, 1), (-1, 1), 4),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


def _crear_tarjetas_kpi_flujo(kpis, ancho_total=720, styles=None):
    """Genera una fila horizontal de tarjetas KPI."""
    if not kpis: return None
    styles = styles or _get_pdf_styles()
    n = len(kpis)
    w_col = ancho_total / n
    
    row_labels = []
    row_vals = []
    
    for kpi in kpis:
        p_lbl = Paragraph(kpi.get('label', '').upper(), styles['KPILabel'])
        
        fg_col = kpi.get('text_color', '#0F172A')
        val_style = ParagraphStyle(
            name=f'KPI_{fg_col}',
            parent=styles['KPIValue'],
            textColor=colors.HexColor(fg_col if fg_col.startswith('#') else f"#{fg_col}")
        )
        p_val = Paragraph(kpi.get('value', ''), val_style)
        
        row_labels.append(p_lbl)
        row_vals.append(p_val)
        
    t = Table([row_labels, row_vals], colWidths=[w_col] * n)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
        ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
        ('PADDING', (0, 0), (-1, 0), 4),
        ('PADDING', (0, 1), (-1, 1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


def generar_pdf_reporte(tipo, items=None, ml_data=None, hist_data=None, cobrado_mes_data=None, periodo_filtro=None, vendedor_filtro=None, empresa_nombre="TODAS (Consolidado)"):
    """
    Genera un archivo PDF ejecutivo de alta calidad según el tipo de reporte.
    Retorna la ruta absoluta al archivo temporal generado.
    """
    styles = _get_pdf_styles()
    
    # Orientación Landscape para reportes con muchas columnas
    page_size = landscape(letter)
    ancho_doc = 792 - 72  # 720 pt ancho útil
    
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()
    
    doc = SimpleDocTemplate(
        tmp.name,
        pagesize=page_size,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    story = []
    
    if tipo == "productos":
        # ── SECCIÓN 1: RANKING DE PRODUCTOS ───────────────────────────────
        tot_monto = sum(float(i.get("subtotal", 0) or 0) for i in items)
        tot_cant = sum(float(i.get("cantidad", 0) or 0) for i in items)
        
        banner = _crear_banner_flujo(
            titulo="CHALLENGER AUTOMOTIVE — TOP PRODUCTOS MÁS VENDIDOS",
            subtitulo=f"Empresa: {empresa_nombre}  |  Ranking consolidado de ventas y volumen",
            ancho_total=ancho_doc,
            color_fondo=C_SLATE_DARK,
            styles=styles
        )
        story.append(banner)
        story.append(Spacer(1, 10))
        
        kpis = [
            {"label": "Total Facturado", "value": f"${tot_monto:,.2f}", "text_color": "#065F46"},
            {"label": "Unidades Vendidas", "value": f"{int(tot_cant):,} uds", "text_color": "#1E40AF"},
            {"label": "Variedad de Códigos", "value": f"{len(items)} productos", "text_color": "#581C87"}
        ]
        story.append(_crear_tarjetas_kpi_flujo(kpis, ancho_total=ancho_doc, styles=styles))
        story.append(Spacer(1, 12))
        
        # Tabla Ranking
        headers = ["#", "Producto / Descripción", "Marca", "Cantidad", "UoM", "Facturado ($)", "P. Prom ($)", "Facturas", "% Total"]
        col_widths = [24, 250, 68, 56, 32, 85, 75, 50, 50]
        t_data = [[Paragraph(h, styles['TableHdr']) for h in headers]]
        
        for idx, i in enumerate(items, 1):
            t_data.append([
                Paragraph(str(i.get("posicion", idx)), styles['TableCellCenter']),
                Paragraph(str(i.get("nombre", "")), styles['TableCellBold']),
                Paragraph(str(i.get("clasificacion", "")), styles['TableCellCenter']),
                Paragraph(f"{float(i.get('cantidad', 0) or 0):,.0f}", styles['TableCellRight']),
                Paragraph(str(i.get("uom", "Pza")), styles['TableCellCenter']),
                Paragraph(f"${float(i.get('subtotal', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"${float(i.get('precio_promedio', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(str(i.get("num_facturas", 0)), styles['TableCellCenter']),
                Paragraph(f"{float(i.get('pct_monto', 0) or 0):.1f}%", styles['TableCellCenter'])
            ])
            
        # Totales
        t_data.append([
            Paragraph("TOTAL", styles['TableHdr']),
            Paragraph(f"{len(items)} Productos Líderes", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph(f"{tot_cant:,.0f}", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph(f"${tot_monto:,.2f}", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("100.0%", styles['TableHdr'])
        ])
        
        t_table = Table(t_data, colWidths=col_widths, repeatRows=1)
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), C_SLATE_HEADER),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 3.5),
            ('BACKGROUND', (0, -1), (-1, -1), C_SLATE_DARK),
        ]
        for r in range(1, len(t_data) - 1):
            bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
            t_style.append(('BACKGROUND', (0, r), (-1, r), bg))
            
        t_table.setStyle(TableStyle(t_style))
        story.append(t_table)
        
        # ── SECCIÓN 2: MACHINE LEARNING FORECAST (PÁGINA 2) ───────────────
        if ml_data and ml_data.get("predicciones_ml"):
            story.append(PageBreak())
            
            mes_pron = ml_data.get("mes_pronosticado", "Próximo Mes")
            banner_ml = _crear_banner_flujo(
                titulo=f"CHALLENGER AI — PRONÓSTICO DE MACHINE LEARNING ({mes_pron.upper()})",
                subtitulo=f"Modelo XGBoost Regressor (Gradient Boosting v3.4)  |  Proyección de Demanda e Ingresos Futuros",
                ancho_total=ancho_doc,
                color_fondo=C_PURPLE_HEADER,
                styles=styles
            )
            story.append(banner_ml)
            story.append(Spacer(1, 10))
            
            preds = ml_data.get("predicciones_ml", [])
            tot_pred_u = sum(float(p.get("pred_unidades", 0) or 0) for p in preds)
            tot_pred_ing = sum(float(p.get("pred_ingreso", 0) or 0) for p in preds)
            tot_buf = sum(float(p.get("stock_sugerido", 0) or 0) for p in preds)
            conf_avg = (sum(float(p.get("confianza_score", 0) or 0) for p in preds) / len(preds)) if preds else 0.0
            
            kpis_ml = [
                {"label": f"Demanda Proyectada ({mes_pron})", "value": f"{int(tot_pred_u):,} uds", "text_color": "#581C87"},
                {"label": f"Ingreso Estimado ({mes_pron})", "value": f"${tot_pred_ing:,.2f}", "text_color": "#065F46"},
                {"label": "Stock Buffer Sugerido (+25%)", "value": f"{int(tot_buf):,} uds", "text_color": "#1E40AF"},
                {"label": "Confianza Modelo IA", "value": f"{conf_avg:.1f}%", "text_color": "#92400E"}
            ]
            story.append(_crear_tarjetas_kpi_flujo(kpis_ml, ancho_total=ancho_doc, styles=styles))
            story.append(Spacer(1, 12))
            
            headers_ml = ["#", "Producto", "Marca", "Mes Ant", "Prom Hist", f"Demanda {mes_pron}", f"Ingreso Est ($)", "Buffer Stock", "Tendencia IA", "Conf %", "Recomendación IA"]
            col_widths_ml = [20, 150, 58, 42, 45, 62, 75, 52, 68, 38, 110]
            t_data_ml = [[Paragraph(h, styles['TableHdr']) for h in headers_ml]]
            
            for p in preds:
                t_data_ml.append([
                    Paragraph(str(p.get("ranking", 1)), styles['TableCellCenter']),
                    Paragraph(str(p.get("producto", "")), styles['TableCellBold']),
                    Paragraph(str(p.get("categoria", "")), styles['TableCellCenter']),
                    Paragraph(f"{float(p.get('ult_mes_unidades', 0) or 0):,.0f}", styles['TableCellRight']),
                    Paragraph(f"{float(p.get('promedio_mensual', 0) or 0):,.0f}", styles['TableCellRight']),
                    Paragraph(f"<b>{float(p.get('pred_unidades', 0) or 0):,.0f} uds</b>", styles['TableCellRight']),
                    Paragraph(f"<b>${float(p.get('pred_ingreso', 0) or 0):,.2f}</b>", styles['TableCellRight']),
                    Paragraph(f"{float(p.get('stock_sugerido', 0) or 0):,.0f} uds", styles['TableCellCenter']),
                    Paragraph(str(p.get("tendencia_flag", "")), styles['TableCellCenter']),
                    Paragraph(f"{float(p.get('confianza_score', 0) or 0):.0f}%", styles['TableCellCenter']),
                    Paragraph(str(p.get("explicacion_ia", "")), styles['TableCell'])
                ])
                
            t_data_ml.append([
                Paragraph("TOTAL", styles['TableHdr']),
                Paragraph(f"{len(preds)} Productos", styles['TableHdr']),
                Paragraph("—", styles['TableHdr']),
                Paragraph("—", styles['TableHdr']),
                Paragraph("—", styles['TableHdr']),
                Paragraph(f"{tot_pred_u:,.0f} uds", styles['TableHdr']),
                Paragraph(f"${tot_pred_ing:,.2f}", styles['TableHdr']),
                Paragraph(f"{tot_buf:,.0f} uds", styles['TableHdr']),
                Paragraph("—", styles['TableHdr']),
                Paragraph(f"{conf_avg:.1f}%", styles['TableHdr']),
                Paragraph("Proyección Consolidada", styles['TableHdr'])
            ])
            
            t_table_ml = Table(t_data_ml, colWidths=col_widths_ml, repeatRows=1)
            t_style_ml = [
                ('BACKGROUND', (0, 0), (-1, 0), C_PURPLE_HEADER),
                ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 3),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#3B0764")),
            ]
            for r in range(1, len(t_data_ml) - 1):
                bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
                t_style_ml.append(('BACKGROUND', (0, r), (-1, r), bg))
                
            t_table_ml.setStyle(TableStyle(t_style_ml))
            story.append(t_table_ml)

            # ── SECCIÓN 3: MATRIZ HISTÓRICA MULTI-MES COMPLETA (PÁGINA 3) ───────
            periodos = ml_data.get("periodos_historico", [])
            prods_hist = ml_data.get("matriz_historica") or ml_data.get("top20_historico", [])
            if periodos and prods_hist:
                story.append(PageBreak())
                banner_hist = _crear_banner_flujo(
                    titulo="CHALLENGER AUTOMOTIVE — MATRIZ HISTÓRICA DE VENTAS (CATÁLOGO COMPLETO)",
                    subtitulo=f"Comportamiento de facturación mensual en los últimos {len(periodos)} meses para todos los productos",
                    ancho_total=ancho_doc,
                    color_fondo=C_BLUE_HEADER,
                    styles=styles
                )
                story.append(banner_hist)
                story.append(Spacer(1, 10))

                headers_hist = ["#", "Producto", "Marca"] + [f"{per}" for per in periodos] + ["Total ($)", "MoM %"]
                # Calcular anchos de columna
                w_pos = 20
                w_prod = 160
                w_cat = 55
                w_tot = 70
                w_mom = 45
                w_rem = ancho_doc - (w_pos + w_prod + w_cat + w_tot + w_mom)
                w_per = w_rem / len(periodos)
                col_widths_h = [w_pos, w_prod, w_cat] + [w_per] * len(periodos) + [w_tot, w_mom]

                t_data_h = [[Paragraph(h, styles['TableHdr']) for h in headers_hist]]

                for p in prods_hist:
                    row_h = [
                        Paragraph(str(p.get("ranking", 1)), styles['TableCellCenter']),
                        Paragraph(str(p.get("producto", "")), styles['TableCellBold']),
                        Paragraph(str(p.get("categoria", "")), styles['TableCellCenter'])
                    ]
                    for per in periodos:
                        sub_m = p.get("ventas_por_mes", {}).get(per, {}).get("subtotal", 0.0)
                        row_h.append(Paragraph(f"${sub_m:,.0f}" if sub_m > 0 else "—", styles['TableCellRight']))

                    row_h.append(Paragraph(f"<b>${p.get('total_subtotal', 0):,.2f}</b>", styles['TableCellRight']))
                    mom_v = p.get("mom_growth", 0)
                    mom_str = f"{'+' if mom_v > 0 else ''}{mom_v:.1f}%"
                    row_h.append(Paragraph(mom_str, styles['TableCellCenter']))
                    t_data_h.append(row_h)

                t_table_h = Table(t_data_h, colWidths=col_widths_h, repeatRows=1)
                t_style_h = [
                    ('BACKGROUND', (0, 0), (-1, 0), C_BLUE_HEADER),
                    ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('PADDING', (0, 0), (-1, -1), 2.5),
                ]
                for r in range(1, len(t_data_h)):
                    bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
                    t_style_h.append(('BACKGROUND', (0, r), (-1, r), bg))

                t_table_h.setStyle(TableStyle(t_style_h))
                story.append(t_table_h)

    elif tipo == "productos_ml":
        # ── REPORTE DEDICADO: PRONÓSTICO MACHINE LEARNING ─────────────────
        ml_data = ml_data or {}
        mes_pron = ml_data.get("mes_pronosticado", "Próximo Mes")
        banner_ml = _crear_banner_flujo(
            titulo=f"CHALLENGER AI — PRONÓSTICO DE MACHINE LEARNING ({mes_pron.upper()})",
            subtitulo=f"Modelo predictivo XGBoost Regressor (Gradient Boosting) | Demanda futura y buffer de stock",
            ancho_total=ancho_doc,
            color_fondo=C_PURPLE_HEADER,
            styles=styles
        )
        story.append(banner_ml)
        story.append(Spacer(1, 10))
        
        preds = ml_data.get("predicciones_ml") or items or []
        tot_pred_u = sum(float(p.get("pred_unidades", 0) or 0) for p in preds)
        tot_pred_ing = sum(float(p.get("pred_ingreso", 0) or 0) for p in preds)
        tot_buf = sum(float(p.get("stock_sugerido", 0) or 0) for p in preds)
        conf_avg = (sum(float(p.get("confianza_score", 0) or 0) for p in preds) / len(preds)) if preds else 0.0
        
        kpis_ml = [
            {"label": f"Demanda Proyectada ({mes_pron})", "value": f"{int(tot_pred_u):,} uds", "text_color": "#581C87"},
            {"label": f"Ingreso Estimado ({mes_pron})", "value": f"${tot_pred_ing:,.2f}", "text_color": "#065F46"},
            {"label": "Stock Buffer Sugerido (+25%)", "value": f"{int(tot_buf):,} uds", "text_color": "#1E40AF"},
            {"label": "Confianza Modelo IA", "value": f"{conf_avg:.1f}%", "text_color": "#92400E"}
        ]
        story.append(_crear_tarjetas_kpi_flujo(kpis_ml, ancho_total=ancho_doc, styles=styles))
        story.append(Spacer(1, 12))
        
        headers_ml = ["#", "Producto", "Marca", "Mes Ant", "Prom Hist", f"Demanda {mes_pron}", f"Ingreso Est ($)", "Buffer Stock", "Tendencia IA", "Conf %", "Recomendación IA"]
        col_widths_ml = [20, 150, 58, 42, 45, 62, 75, 52, 68, 38, 110]
        t_data_ml = [[Paragraph(h, styles['TableHdr']) for h in headers_ml]]
        
        for p in preds:
            t_data_ml.append([
                Paragraph(str(p.get("ranking", 1)), styles['TableCellCenter']),
                Paragraph(str(p.get("producto", "")), styles['TableCellBold']),
                Paragraph(str(p.get("categoria", "")), styles['TableCellCenter']),
                Paragraph(f"{float(p.get('ult_mes_unidades', 0) or 0):,.0f}", styles['TableCellRight']),
                Paragraph(f"{float(p.get('promedio_mensual', 0) or 0):,.0f}", styles['TableCellRight']),
                Paragraph(f"<b>{float(p.get('pred_unidades', 0) or 0):,.0f} uds</b>", styles['TableCellRight']),
                Paragraph(f"<b>${float(p.get('pred_ingreso', 0) or 0):,.2f}</b>", styles['TableCellRight']),
                Paragraph(f"{float(p.get('stock_sugerido', 0) or 0):,.0f} uds", styles['TableCellCenter']),
                Paragraph(str(p.get("tendencia_flag", "")), styles['TableCellCenter']),
                Paragraph(f"{float(p.get('confianza_score', 0) or 0):.0f}%", styles['TableCellCenter']),
                Paragraph(str(p.get("explicacion_ia", "")), styles['TableCell'])
            ])
            
        t_data_ml.append([
            Paragraph("TOTAL", styles['TableHdr']),
            Paragraph(f"{len(preds)} Productos", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph(f"{tot_pred_u:,.0f} uds", styles['TableHdr']),
            Paragraph(f"${tot_pred_ing:,.2f}", styles['TableHdr']),
            Paragraph(f"{tot_buf:,.0f} uds", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph(f"{conf_avg:.1f}%", styles['TableHdr']),
            Paragraph("Proyección Consolidada", styles['TableHdr'])
        ])
        
        t_table_ml = Table(t_data_ml, colWidths=col_widths_ml, repeatRows=1)
        t_style_ml = [
            ('BACKGROUND', (0, 0), (-1, 0), C_PURPLE_HEADER),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#3B0764")),
        ]
        for r in range(1, len(t_data_ml) - 1):
            bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
            t_style_ml.append(('BACKGROUND', (0, r), (-1, r), bg))
            
        t_table_ml.setStyle(TableStyle(t_style_ml))
        story.append(t_table_ml)

    elif tipo == "productos_historico":
        # ── REPORTE DEDICADO: MATRIZ HISTÓRICA MULTI-MES COMPLETA ─────────
        ml_data = ml_data or {}
        periodos = ml_data.get("periodos_historico", [])
        prods_hist = ml_data.get("matriz_historica") or ml_data.get("top20_historico") or items or []
        
        banner_hist = _crear_banner_flujo(
            titulo="CHALLENGER AUTOMOTIVE — MATRIZ HISTÓRICA DE VENTAS (CATÁLOGO COMPLETO)",
            subtitulo=f"Comportamiento de facturación mensual en los últimos {len(periodos)} meses para todos los productos",
            ancho_total=ancho_doc,
            color_fondo=C_BLUE_HEADER,
            styles=styles
        )
        story.append(banner_hist)
        story.append(Spacer(1, 10))

        headers_hist = ["#", "Producto", "Marca"] + [f"{per}" for per in periodos] + ["Total ($)", "MoM %"]
        w_pos = 20
        w_prod = 160
        w_cat = 55
        w_tot = 70
        w_mom = 45
        w_rem = ancho_doc - (w_pos + w_prod + w_cat + w_tot + w_mom)
        w_per = w_rem / max(len(periodos), 1)
        col_widths_h = [w_pos, w_prod, w_cat] + [w_per] * len(periodos) + [w_tot, w_mom]

        t_data_h = [[Paragraph(h, styles['TableHdr']) for h in headers_hist]]

        for p in prods_hist:
            row_h = [
                Paragraph(str(p.get("ranking", 1)), styles['TableCellCenter']),
                Paragraph(str(p.get("producto", "")), styles['TableCellBold']),
                Paragraph(str(p.get("categoria", "")), styles['TableCellCenter'])
            ]
            for per in periodos:
                sub_m = p.get("ventas_por_mes", {}).get(per, {}).get("subtotal", 0.0)
                row_h.append(Paragraph(f"${sub_m:,.0f}" if sub_m > 0 else "—", styles['TableCellRight']))

            row_h.append(Paragraph(f"<b>${p.get('total_subtotal', 0):,.2f}</b>", styles['TableCellRight']))
            mom_v = p.get("mom_growth", 0)
            mom_str = f"{'+' if mom_v > 0 else ''}{mom_v:.1f}%"
            row_h.append(Paragraph(mom_str, styles['TableCellCenter']))
            t_data_h.append(row_h)

        t_table_h = Table(t_data_h, colWidths=col_widths_h, repeatRows=1)
        t_style_h = [
            ('BACKGROUND', (0, 0), (-1, 0), C_BLUE_HEADER),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 2.5),
        ]
        for r in range(1, len(t_data_h)):
            bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
            t_style_h.append(('BACKGROUND', (0, r), (-1, r), bg))

        t_table_h.setStyle(TableStyle(t_style_h))
        story.append(t_table_h)

    elif tipo == "cobranza":
        # ── REPORTE DE CARTERA DE COBRANZA ───────────────────────────────
        tot_deuda = sum(float(i.get("saldo_pendiente", 0) or 0) for i in items)
        tot_al_dia = sum(float(i.get("saldo_pendiente", 0) or 0) for i in items if (i.get("dias_retraso", 0) or 0) <= 0)
        tot_reciente = sum(float(i.get("saldo_pendiente", 0) or 0) for i in items if 0 < (i.get("dias_retraso", 0) or 0) <= 60)
        tot_pasada = sum(float(i.get("saldo_pendiente", 0) or 0) for i in items if 60 < (i.get("dias_retraso", 0) or 0) <= 100)
        tot_atrasada = sum(float(i.get("saldo_pendiente", 0) or 0) for i in items if (i.get("dias_retraso", 0) or 0) > 100)
        
        banner = _crear_banner_flujo(
            titulo="CHALLENGER AUTOMOTIVE — CARTERA DE COBRANZA Y SALDOS VENCIDOS",
            subtitulo=f"Antigüedad de saldos (0-60d, 60-100d, >100d), facturas impagadas y asignación de vendedor",
            ancho_total=ancho_doc,
            color_fondo=C_EMERALD_HEADER,
            styles=styles
        )
        story.append(banner)
        story.append(Spacer(1, 10))
        
        kpis_cob = [
            {"label": "Saldo Total Cartera", "value": f"${tot_deuda:,.2f}", "text_color": "#991B1B"},
            {"label": "🟢 Reciente (0-60d)", "value": f"${tot_reciente:,.2f}", "text_color": "#065F46"},
            {"label": "🟡 Pasada (60-100d)", "value": f"${tot_pasada:,.2f}", "text_color": "#92400E"},
            {"label": "🚨 Atrasada (>100d)", "value": f"${tot_atrasada:,.2f}", "text_color": "#991B1B"}
        ]
        story.append(_crear_tarjetas_kpi_flujo(kpis_cob, ancho_total=ancho_doc, styles=styles))
        story.append(Spacer(1, 12))
        
        headers_cob = ["Folio", "Cliente / Razón Social", "Vendedor", "Fecha Fac", "Vencimiento", "Retraso", "Estatus", "Total Factura ($)", "Abonado ($)", "Saldo Pendiente ($)"]
        col_widths_cob = [65, 175, 90, 52, 52, 42, 64, 60, 60, 60]
        t_data_cob = [[Paragraph(h, styles['TableHdr']) for h in headers_cob]]
        
        for i in items:
            dias_r = int(i.get("dias_retraso", 0) or 0)
            if dias_r > 100: estatus_txt = "🚨 Atrasada >100d"
            elif dias_r > 60: estatus_txt = "🟡 Pasada 60-100d"
            elif dias_r > 0: estatus_txt = "🟢 Reciente 0-60d"
            else: estatus_txt = "✓ Al Día"
            
            t_data_cob.append([
                Paragraph(str(i.get("folio", "")), styles['TableCellCenter']),
                Paragraph(str(i.get("cliente", "")), styles['TableCellBold']),
                Paragraph(str(i.get("vendedor", "No Asignado")), styles['TableCell']),
                Paragraph(str(i.get("fecha_factura", "")), styles['TableCellCenter']),
                Paragraph(str(i.get("fecha_vencimiento", "")), styles['TableCellCenter']),
                Paragraph(f"{dias_r}d", styles['TableCellCenter']),
                Paragraph(estatus_txt, styles['TableCellCenter']),
                Paragraph(f"${float(i.get('total_factura', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"${float(i.get('monto_abonado', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"<b>${float(i.get('saldo_pendiente', 0) or 0):,.2f}</b>", styles['TableCellRight'])
            ])
            
        tot_fac = sum(float(i.get("total_factura", 0) or 0) for i in items)
        tot_ab = sum(float(i.get("monto_abonado", 0) or 0) for i in items)
        t_data_cob.append([
            Paragraph("TOTAL", styles['TableHdr']),
            Paragraph(f"{len(items)} Facturas", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph(f"${tot_fac:,.2f}", styles['TableHdr']),
            Paragraph(f"${tot_ab:,.2f}", styles['TableHdr']),
            Paragraph(f"${tot_deuda:,.2f}", styles['TableHdr'])
        ])
        
        t_table_cob = Table(t_data_cob, colWidths=col_widths_cob, repeatRows=1)
        t_style_cob = [
            ('BACKGROUND', (0, 0), (-1, 0), C_EMERALD_HEADER),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#064E3B")),
        ]
        for r in range(1, len(t_data_cob) - 1):
            bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
            t_style_cob.append(('BACKGROUND', (0, r), (-1, r), bg))
            
        t_table_cob.setStyle(TableStyle(t_style_cob))
        story.append(t_table_cob)

    elif tipo == "cobrado_mes":
        # ── REPORTE DE COBRADO & RECUPERACIÓN MENSUAL ─────────────────────
        cob_payload = cobrado_mes_data or {}
        meses_data = cob_payload.get("meses") or []
        res_glob = cob_payload.get("resumen_global") or {}
        per_filtro = periodo_filtro or "TODOS"
        vend_filtro = vendedor_filtro or "TODOS"

        tot_cob_hist = float(res_glob.get("total_cobrado_historico", sum(float(m.get("total_cobrado", 0) or 0) for m in meses_data)) or 0)
        tot_fact_hist = float(res_glob.get("total_facturado_historico", sum(float(m.get("total_facturado", 0) or 0) for m in meses_data)) or 0)
        tot_sal_hist = float(res_glob.get("total_saldo_historico", sum(float(m.get("saldo_pendiente", 0) or 0) for m in meses_data)) or 0)
        pct_ef_hist = (tot_cob_hist / tot_fact_hist * 100.0) if tot_fact_hist > 0 else 100.0

        banner = _crear_banner_flujo(
            titulo="CHALLENGER AUTOMOTIVE — COBRADO & RECUPERACIÓN MENSUAL",
            subtitulo=f"Período: {per_filtro}  |  Vendedor: {vend_filtro}  |  Empresa: {empresa_nombre}",
            ancho_total=ancho_doc,
            color_fondo=C_EMERALD_HEADER,
            styles=styles
        )
        story.append(banner)
        story.append(Spacer(1, 10))

        kpis_cm = [
            {"label": "Total Cobrado Histórico", "value": f"${tot_cob_hist:,.2f}", "text_color": "#065F46"},
            {"label": "Total Facturado en Meses", "value": f"${tot_fact_hist:,.2f}", "text_color": "#1E40AF"},
            {"label": "Saldo Insoluto Pendiente", "value": f"${tot_sal_hist:,.2f}", "text_color": "#991B1B"},
            {"label": "Tasa de Efectividad", "value": f"{pct_ef_hist:.1f}%", "text_color": "#581C87"}
        ]
        story.append(_crear_tarjetas_kpi_flujo(kpis_cm, ancho_total=ancho_doc, styles=styles))
        story.append(Spacer(1, 12))

        # SECCIÓN 1: TABLA HISTÓRICA MENSUAL
        story.append(Paragraph("<b>1. RESUMEN CONSOLIDADO DE COBRANZA MENSUAL</b>", styles['SectionHeader']))
        story.append(Spacer(1, 4))

        headers_m = ["Mes de Cobro / Período", "Pagos (#)", "Clientes (#)", "Total Cobrado ($)", "Total Facturado ($)", "Pendiente ($)", "% Cobranza"]
        col_w_m = [150, 70, 70, 110, 110, 110, 100]
        t_data_m = [[Paragraph(h, styles['TableHdr']) for h in headers_m]]

        for m in meses_data:
            pct_m = m.get("pct_efectividad_cobranza", 0) or 0
            t_data_m.append([
                Paragraph(str(m.get("mes_nombre", "")), styles['TableCellBold']),
                Paragraph(str(m.get("num_pagos", 0)), styles['TableCellCenter']),
                Paragraph(str(m.get("num_clientes", 0)), styles['TableCellCenter']),
                Paragraph(f"${float(m.get('total_cobrado', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"${float(m.get('total_facturado', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"${float(m.get('saldo_pendiente', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"{pct_m:.1f}%", styles['TableCellCenterBold'])
            ])

        t_data_m.append([
            Paragraph("TOTAL CONSOLIDADO", styles['TableHdr']),
            Paragraph(f"{sum(int(m.get('num_pagos', 0) or 0) for m in meses_data)}", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph(f"${tot_cob_hist:,.2f}", styles['TableHdr']),
            Paragraph(f"${tot_fact_hist:,.2f}", styles['TableHdr']),
            Paragraph(f"${tot_sal_hist:,.2f}", styles['TableHdr']),
            Paragraph(f"{pct_ef_hist:.1f}%", styles['TableHdr'])
        ])

        t_table_m = Table(t_data_m, colWidths=col_w_m, repeatRows=1)
        t_style_m = [
            ('BACKGROUND', (0, 0), (-1, 0), C_EMERALD_HEADER),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#064E3B")),
        ]
        for r in range(1, len(t_data_m) - 1):
            bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
            t_style_m.append(('BACKGROUND', (0, r), (-1, r), bg))
        t_table_m.setStyle(TableStyle(t_style_m))
        story.append(t_table_m)
        story.append(Spacer(1, 14))

        # SECCIÓN 2: TOP CLIENTES CON COBROS EN EL PERIODO
        story.append(Paragraph(f"<b>2. DESGLOSE DE COBROS POR CLIENTE ({per_filtro})</b>", styles['SectionHeader']))
        story.append(Spacer(1, 4))

        clientes_pdf = []
        if per_filtro == "TODOS":
            cmap = {}
            for m in meses_data:
                for c in m.get("clientes", []):
                    cid = c.get("cliente_id") or c.get("cliente_nombre")
                    if cid not in cmap:
                        cmap[cid] = {
                            "cliente_nombre": c.get("cliente_nombre"),
                            "rfc": c.get("rfc"),
                            "vendedor": c.get("vendedor"),
                            "total_cobrado": 0.0,
                            "num_pagos": 0,
                            "saldo_actual_cliente": c.get("saldo_actual_cliente", 0.0)
                        }
                    cmap[cid]["total_cobrado"] += float(c.get("total_cobrado", 0) or 0)
                    cmap[cid]["num_pagos"] += int(c.get("num_pagos", 0) or 0)
            clientes_pdf = sorted(cmap.values(), key=lambda x: x["total_cobrado"], reverse=True)
        else:
            m_target = next((m for m in meses_data if m.get("mes_key") == per_filtro), None)
            if m_target:
                clientes_pdf = sorted(m_target.get("clientes", []), key=lambda x: float(x.get("total_cobrado", 0) or 0), reverse=True)

        headers_c = ["#", "Cliente / Razón Social", "RFC", "Vendedor", "Total Cobrado ($)", "Pagos (#)", "Saldo Deudor Actual ($)"]
        col_w_c = [25, 235, 80, 110, 100, 60, 110]
        t_data_c = [[Paragraph(h, styles['TableHdr']) for h in headers_c]]

        for idx, c in enumerate(clientes_pdf[:100], 1):
            t_data_c.append([
                Paragraph(str(idx), styles['TableCellCenter']),
                Paragraph(str(c.get("cliente_nombre", "")), styles['TableCellBold']),
                Paragraph(str(c.get("rfc") or "—"), styles['TableCellCenter']),
                Paragraph(str(c.get("vendedor") or "Sin Asignar"), styles['TableCell']),
                Paragraph(f"${float(c.get('total_cobrado', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(str(c.get("num_pagos", 0)), styles['TableCellCenter']),
                Paragraph(f"${float(c.get('saldo_actual_cliente', 0) or 0):,.2f}", styles['TableCellRight'])
            ])

        t_table_c = Table(t_data_c, colWidths=col_w_c, repeatRows=1)
        t_style_c = [
            ('BACKGROUND', (0, 0), (-1, 0), C_SLATE_DARK),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]
        for r in range(1, len(t_data_c)):
            bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
            t_style_c.append(('BACKGROUND', (0, r), (-1, r), bg))
        t_table_c.setStyle(TableStyle(t_style_c))
        story.append(t_table_c)

    elif tipo in ["historial_cliente", "compras_cliente"]:
        # ── REPORTE ESTADO DE CUENTA Y COMPRAS DEL CLIENTE ───────────────
        h_data = hist_data or {}
        cliente_nom = h_data.get("cliente_nombre") or (items[0].get("cliente") if items else "Cliente")
        rfc = h_data.get("rfc") or "SIN RFC"
        vendedor = h_data.get("vendedor") or "Sin Asignar"
        tel = h_data.get("telefono") or "Sin teléfono"
        email = h_data.get("email") or "Sin correo"
        kpis = h_data.get("kpis", {})
        facturas = h_data.get("facturas") or items or []

        tot_comprado = float(kpis.get("total_comprado", sum(float(f.get("total", 0) or 0) for f in facturas)) or 0)
        tot_pagado = float(kpis.get("total_pagado", sum(float(f.get("monto_pagado", 0) or 0) for f in facturas)) or 0)
        tot_saldo = float(kpis.get("total_saldo_pendiente", sum(float(f.get("saldo_pendiente", 0) or 0) for f in facturas)) or 0)
        pct_cub = (tot_pagado / tot_comprado * 100.0) if tot_comprado > 0 else 100.0

        banner = _crear_banner_flujo(
            titulo=f"ESTADO DE CUENTA Y COMPRAS — {cliente_nom.upper()}",
            subtitulo=f"RFC: {rfc}  |  Vendedor: {vendedor}  |  Tel: {tel}  |  Email: {email}",
            ancho_total=ancho_doc,
            color_fondo=C_EMERALD_HEADER,
            styles=styles
        )
        story.append(banner)
        story.append(Spacer(1, 10))

        kpis_hc = [
            {"label": "Total Comprado (Ventas)", "value": f"${tot_comprado:,.2f}", "text_color": "#1E40AF"},
            {"label": "Total Pagado / Recuperado", "value": f"${tot_pagado:,.2f}", "text_color": "#065F46"},
            {"label": "Saldo Pendiente Deudor", "value": f"${tot_saldo:,.2f}", "text_color": "#991B1B"},
            {"label": "% Liquidado", "value": f"{pct_cub:.1f}%", "text_color": "#065F46" if pct_cub >= 80 else "#92400E"}
        ]
        story.append(_crear_tarjetas_kpi_flujo(kpis_hc, ancho_total=ancho_doc, styles=styles))
        story.append(Spacer(1, 12))

        # SECCIÓN 1: TABLA DE FACTURAS
        story.append(Paragraph("<b>1. RELACIÓN DE FACTURAS Y ESTADO DE CUENTA</b>", styles['SectionHeader']))
        story.append(Spacer(1, 4))

        headers_f = ["Folio", "Tipo", "Emisión", "Vencimiento", "Plazo / Retraso", "Estatus Pago", "Total Factura ($)", "Monto Pagado ($)", "Saldo Pendiente ($)"]
        col_w_f = [85, 75, 60, 60, 80, 80, 95, 95, 90]
        t_data_f = [[Paragraph(h, styles['TableHdr']) for h in headers_f]]

        for f in facturas:
            dias_r = int(f.get("dias_retraso", 0) or 0)
            dias_c = int(f.get("dias_credito", 0) or 0)
            plazo_txt = f"{dias_r}d retraso" if dias_r > 0 else f"{dias_c}d crédito"
            est_p = f.get("estatus_pago", "PENDIENTE")

            t_data_f.append([
                Paragraph(str(f.get("folio", "")), styles['TableCellCenterBold']),
                Paragraph(str(f.get("tipo", "Factura")), styles['TableCellCenter']),
                Paragraph(str(f.get("fecha_emision", "")), styles['TableCellCenter']),
                Paragraph(str(f.get("fecha_vencimiento", "")), styles['TableCellCenter']),
                Paragraph(plazo_txt, styles['TableCellCenter']),
                Paragraph(est_p, styles['TableCellCenterBold']),
                Paragraph(f"${float(f.get('total', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"${float(f.get('monto_pagado', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"<b>${float(f.get('saldo_pendiente', 0) or 0):,.2f}</b>", styles['TableCellRight'])
            ])

        t_data_f.append([
            Paragraph("TOTALES", styles['TableHdr']),
            Paragraph(f"{len(facturas)} Facturas", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph(f"${tot_comprado:,.2f}", styles['TableHdr']),
            Paragraph(f"${tot_pagado:,.2f}", styles['TableHdr']),
            Paragraph(f"${tot_saldo:,.2f}", styles['TableHdr'])
        ])

        t_table_f = Table(t_data_f, colWidths=col_w_f, repeatRows=1)
        t_style_f = [
            ('BACKGROUND', (0, 0), (-1, 0), C_EMERALD_HEADER),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#064E3B")),
        ]
        for r in range(1, len(t_data_f) - 1):
            bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
            t_style_f.append(('BACKGROUND', (0, r), (-1, r), bg))
        t_table_f.setStyle(TableStyle(t_style_f))
        story.append(t_table_f)
        story.append(Spacer(1, 14))

        # SECCIÓN 2: DESGLOSE DE PRODUCTOS VENDIDOS
        story.append(Paragraph("<b>2. DESGLOSE DE PRODUCTOS VENDIDOS POR FACTURA</b>", styles['SectionHeader']))
        story.append(Spacer(1, 4))

        headers_p = ["Folio", "Fecha", "Código/SKU", "Descripción del Producto", "Cant.", "UOM", "P. Unit ($)", "Subtotal ($)", "Total c/IVA ($)"]
        col_w_p = [75, 55, 65, 230, 45, 35, 65, 75, 75]
        t_data_p = [[Paragraph(h, styles['TableHdr']) for h in headers_p]]

        tot_cant_p = 0.0
        tot_sub_p = 0.0
        tot_iva_p = 0.0

        for f in facturas:
            fol = str(f.get("folio", ""))
            f_em = str(f.get("fecha_emision", ""))
            for p in f.get("productos", []):
                c_qty = float(p.get("cantidad", 0) or 0)
                c_sub = float(p.get("subtotal", 0) or 0)
                c_tot = float(p.get("total", 0) or 0)
                tot_cant_p += c_qty
                tot_sub_p += c_sub
                tot_iva_p += c_tot

                t_data_p.append([
                    Paragraph(fol, styles['TableCellCenterBold']),
                    Paragraph(f_em, styles['TableCellCenter']),
                    Paragraph(str(p.get("sku") or "—"), styles['TableCellCenter']),
                    Paragraph(str(p.get("producto", "")), styles['TableCell']),
                    Paragraph(f"{c_qty:,.1f}" if not c_qty.is_integer() else f"{int(c_qty):,}", styles['TableCellRight']),
                    Paragraph(str(p.get("uom") or "Pz"), styles['TableCellCenter']),
                    Paragraph(f"${float(p.get('precio_unit', 0) or 0):,.2f}", styles['TableCellRight']),
                    Paragraph(f"${c_sub:,.2f}", styles['TableCellRight']),
                    Paragraph(f"${c_tot:,.2f}", styles['TableCellRight'])
                ])

        if len(t_data_p) > 1:
            t_data_p.append([
                Paragraph("TOTALES", styles['TableHdr']),
                Paragraph("—", styles['TableHdr']),
                Paragraph("—", styles['TableHdr']),
                Paragraph(f"{len(t_data_p)-1} Renglones de Producto", styles['TableHdr']),
                Paragraph(f"{tot_cant_p:,.1f}", styles['TableHdr']),
                Paragraph("—", styles['TableHdr']),
                Paragraph("—", styles['TableHdr']),
                Paragraph(f"${tot_sub_p:,.2f}", styles['TableHdr']),
                Paragraph(f"${tot_iva_p:,.2f}", styles['TableHdr'])
            ])

            t_table_p = Table(t_data_p, colWidths=col_w_p, repeatRows=1)
            t_style_p = [
                ('BACKGROUND', (0, 0), (-1, 0), C_SLATE_DARK),
                ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 2.5),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#0F172A")),
            ]
            for r in range(1, len(t_data_p) - 1):
                bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
                t_style_p.append(('BACKGROUND', (0, r), (-1, r), bg))
            t_table_p.setStyle(TableStyle(t_style_p))
            story.append(t_table_p)

    elif tipo == "comisiones":
        # ── REPORTE DE COMISIONES POR VENDEDOR ───────────────────────────
        tot_cob = sum(float(i.get("cobrado", 0) or 0) for i in items)
        tot_com = sum(float(i.get("comision", 0) or 0) for i in items)
        
        banner = _crear_banner_flujo(
            titulo="CHALLENGER AUTOMOTIVE — LIQUIDACIÓN DE COMISIONES POR VENDEDOR",
            subtitulo=f"Desglose de cobros conciliados en Odoo y cálculo de comisión por producto",
            ancho_total=ancho_doc,
            color_fondo=C_SLATE_DARK,
            styles=styles
        )
        story.append(banner)
        story.append(Spacer(1, 10))
        
        kpis_com = [
            {"label": "Total Cobrado", "value": f"${tot_cob:,.2f}", "text_color": "#1E40AF"},
            {"label": "Total Comisión a Pagar", "value": f"${tot_com:,.2f}", "text_color": "#065F46"},
            {"label": "Pagos Conciliados", "value": f"{len(items)} pagos", "text_color": "#581C87"}
        ]
        story.append(_crear_tarjetas_kpi_flujo(kpis_com, ancho_total=ancho_doc, styles=styles))
        story.append(Spacer(1, 12))
        
        headers_com = ["Fecha", "Cliente", "Factura(s)", "Pago #", "Cobrado ($)", "Base Challenger ($)", "Base Multi/Pasta ($)", "Comisión ($)", "Estatus Tiempo"]
        col_widths_com = [55, 175, 80, 45, 75, 75, 75, 75, 65]
        t_data_com = [[Paragraph(h, styles['TableHdr']) for h in headers_com]]
        
        for i in items:
            t_data_com.append([
                Paragraph(str(i.get("fecha", "")), styles['TableCellCenter']),
                Paragraph(str(i.get("cliente", "")), styles['TableCellBold']),
                Paragraph(str(i.get("factura", "")), styles['TableCellCenter']),
                Paragraph(str(i.get("num_pago", "")), styles['TableCellCenter']),
                Paragraph(f"${float(i.get('cobrado', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"${float(i.get('base_challenger', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"${float(i.get('base_multi', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"<b>${float(i.get('comision', 0) or 0):,.2f}</b>", styles['TableCellRight']),
                Paragraph("🟢 En tiempo" if i.get("en_tiempo") else f"⚠️ {i.get('dias_retraso', 0)}d retraso", styles['TableCellCenter'])
            ])
            
        t_data_com.append([
            Paragraph("TOTAL", styles['TableHdr']),
            Paragraph(f"{len(items)} Pagos", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph(f"${tot_cob:,.2f}", styles['TableHdr']),
            Paragraph(f"${sum(float(i.get('base_challenger', 0) or 0) for i in items):,.2f}", styles['TableHdr']),
            Paragraph(f"${sum(float(i.get('base_multi', 0) or 0) for i in items):,.2f}", styles['TableHdr']),
            Paragraph(f"${tot_com:,.2f}", styles['TableHdr']),
            Paragraph("—", styles['TableHdr'])
        ])
        
        t_table_com = Table(t_data_com, colWidths=col_widths_com, repeatRows=1)
        t_style_com = [
            ('BACKGROUND', (0, 0), (-1, 0), C_SLATE_HEADER),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, -1), (-1, -1), C_SLATE_DARK),
        ]
        for r in range(1, len(t_data_com) - 1):
            bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
            t_style_com.append(('BACKGROUND', (0, r), (-1, r), bg))
            
        t_table_com.setStyle(TableStyle(t_style_com))
        story.append(t_table_com)

    elif tipo == "stock":
        # ── REPORTE DE STOCK ÓPTIMO & PLAN DE REABASTECIMIENTO ────────────
        tot_disp = sum(float(i.get("disponible", 0) or 0) for i in items)
        tot_v_mes = sum(float(i.get("venta_mensual_est", 0) or 0) for i in items)
        tot_stk_opt = sum(float(i.get("stock_sugerido_mes", 0) or 0) for i in items)
        tot_pedir = sum(float(i.get("sugerido_pedir", 0) or 0) for i in items)
        tot_inv_reorden = sum(float(i.get("inversion_reorden", 0) or 0) for i in items)
        
        banner = _crear_banner_flujo(
            titulo="CHALLENGER AUTOMOTIVE — PLAN DE STOCK ÓPTIMO Y SUGERENCIAS DE COMPRA",
            subtitulo="Precios a Precio de Venta + IVA (16%) | Estimación de demanda mensual (30d), stock a la mano y sugerido a pedir",
            ancho_total=ancho_doc,
            color_fondo=C_BLUE_HEADER,
            styles=styles
        )
        story.append(banner)
        story.append(Spacer(1, 10))
        
        kpis_stk = [
            {"label": "Stock A la mano Total", "value": f"{int(tot_disp):,} uds", "text_color": "#1E40AF"},
            {"label": "Demanda Mensual Est.", "value": f"{int(tot_v_mes):,} uds/mes", "text_color": "#581C87"},
            {"label": "Stock Óptimo Meta (30d)", "value": f"{int(tot_stk_opt):,} uds", "text_color": "#065F46"},
            {"label": "Total a Pedir (Faltante)", "value": f"{int(tot_pedir):,} uds", "text_color": "#991B1B"},
            {"label": "Inversión a Reabastecer", "value": f"${tot_inv_reorden:,.2f}", "text_color": "#065F46"}
        ]
        story.append(_crear_tarjetas_kpi_flujo(kpis_stk, ancho_total=ancho_doc, styles=styles))
        story.append(Spacer(1, 12))
        
        headers_stk = ["#", "Producto / Código", "Almacén", "Marca", "A la mano", "Demanda Mes", "Stock Mínimo", "Stock Óptimo", "A Pedir", "Inversión ($)", "Estatus"]
        col_widths_stk = [22, 178, 95, 50, 48, 52, 52, 55, 50, 60, 58]
        t_data_stk = [[Paragraph(h, styles['TableHdr']) for h in headers_stk]]
        
        for idx, i in enumerate(items, 1):
            pedir_val = float(i.get("sugerido_pedir", 0) or 0)
            inv_val = float(i.get("inversion_reorden", 0) or 0)
            st_txt = str(i.get("estado", ""))
            
            # Formato de celda de pedido e inversión
            if pedir_val > 0:
                pedir_cell = f"<font color='#991B1B'><b>{pedir_val:,.0f}</b></font>"
                inv_cell = f"<font color='#991B1B'>${inv_val:,.2f}</font>"
            else:
                pedir_cell = "0"
                inv_cell = "$0.00"
                
            t_data_stk.append([
                Paragraph(str(i.get("posicion", idx)), styles['TableCellCenter']),
                Paragraph(str(i.get("producto", "")), styles['TableCellBold']),
                Paragraph(str(i.get("almacen", "")), styles['TableCell']),
                Paragraph(str(i.get("clasificacion", "")), styles['TableCellCenter']),
                Paragraph(f"<b>{float(i.get('a_la_mano') or i.get('stock_actual') or 0):,.0f}</b>", styles['TableCellRight']),
                Paragraph(f"{float(i.get('venta_mensual_est', 0) or 0):,.0f}", styles['TableCellRight']),
                Paragraph(f"{float(i.get('stock_minimo', 0) or 0):,.0f}", styles['TableCellRight']),
                Paragraph(f"<b>{float(i.get('stock_sugerido_mes', 0) or 0):,.0f}</b>", styles['TableCellRight']),
                Paragraph(pedir_cell, styles['TableCellRight']),
                Paragraph(inv_cell, styles['TableCellRight']),
                Paragraph(st_txt, styles['TableCellCenter'])
            ])
            
        t_data_stk.append([
            Paragraph("TOTAL", styles['TableHdr']),
            Paragraph(f"{len(items)} Productos", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph(f"{tot_disp:,.0f}", styles['TableHdr']),
            Paragraph(f"{tot_v_mes:,.0f}", styles['TableHdr']),
            Paragraph(f"{sum(float(i.get('stock_minimo', 0) or 0) for i in items):,.0f}", styles['TableHdr']),
            Paragraph(f"{tot_stk_opt:,.0f}", styles['TableHdr']),
            Paragraph(f"{tot_pedir:,.0f}", styles['TableHdr']),
            Paragraph(f"${tot_inv_reorden:,.2f}", styles['TableHdr']),
            Paragraph("—", styles['TableHdr'])
        ])
        
        t_table_stk = Table(t_data_stk, colWidths=col_widths_stk, repeatRows=1)
        t_style_stk = [
            ('BACKGROUND', (0, 0), (-1, 0), C_BLUE_HEADER),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#172554")),
        ]
        for r in range(1, len(t_data_stk) - 1):
            bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
            t_style_stk.append(('BACKGROUND', (0, r), (-1, r), bg))
            
        t_table_stk.setStyle(TableStyle(t_style_stk))
        story.append(t_table_stk)

    elif tipo == "ventas_vendedor":
        # ── REPORTE DE VENTAS POR VENDEDOR & PRODUCTOS VENDIDOS ───────────
        vv_data = ml_data or {}
        resumen_vends = vv_data.get("resumen_vendedores") or items or []
        totales = vv_data.get("totales_generales") or {}
        periodo_nom = vv_data.get("periodo_seleccionado", "Mes Actual")

        tot_fact = totales.get("total_facturado", sum(float(v.get("total_subtotal", 0) or 0) for v in resumen_vends))
        tot_units = totales.get("total_unidades", sum(float(v.get("total_cantidad", 0) or 0) for v in resumen_vends))
        v_lider = totales.get("vendedor_lider", "—")

        banner = _crear_banner_flujo(
            titulo=f"CHALLENGER AUTOMOTIVE — VENTAS POR VENDEDOR ({periodo_nom.upper()})",
            subtitulo=f"Empresa: {empresa_nombre}  |  Facturación consolidada por vendedor oficial y productos",
            ancho_total=ancho_doc,
            color_fondo=C_EMERALD_HEADER,
            styles=styles
        )
        story.append(banner)
        story.append(Spacer(1, 10))

        kpis = [
            {"label": f"Total Facturado ({periodo_nom})", "value": f"${tot_fact:,.2f}", "text_color": "#065F46"},
            {"label": "Unidades Vendidas", "value": f"{int(tot_units):,} uds", "text_color": "#1E40AF"},
            {"label": "Vendedor Líder", "value": f"{v_lider}", "text_color": "#581C87"},
            {"label": "Vendedores Activos", "value": f"{len(resumen_vends)} ejecutivos", "text_color": "#92400E"}
        ]
        story.append(_crear_tarjetas_kpi_flujo(kpis, ancho_total=ancho_doc, styles=styles))
        story.append(Spacer(1, 12))

        # Tabla Resumen de Vendedores
        headers_vv = ["#", "Vendedor Oficial", "Facturado ($)", "Unidades", "Facturas #", "Clientes #", "Ticket Prom ($)", "% Total", "Top Producto Vendido"]
        col_widths_vv = [20, 140, 80, 55, 45, 45, 75, 50, 210]
        t_data_vv = [[Paragraph(h, styles['TableHdr']) for h in headers_vv]]

        for v in resumen_vends:
            t_data_vv.append([
                Paragraph(str(v.get("posicion", 1)), styles['TableCellCenter']),
                Paragraph(str(v.get("vendedor", "")), styles['TableCellBold']),
                Paragraph(f"${float(v.get('total_subtotal', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"{float(v.get('total_cantidad', 0) or 0):,.0f}", styles['TableCellRight']),
                Paragraph(str(v.get("num_facturas", 0)), styles['TableCellCenter']),
                Paragraph(str(v.get("num_clientes", 0)), styles['TableCellCenter']),
                Paragraph(f"${float(v.get('ticket_promedio', 0) or 0):,.2f}", styles['TableCellRight']),
                Paragraph(f"{float(v.get('pct_participacion', 0) or 0):.1f}%", styles['TableCellCenter']),
                Paragraph(str(v.get("top_producto", "—")), styles['TableCell'])
            ])

        t_data_vv.append([
            Paragraph("TOTAL", styles['TableHdr']),
            Paragraph(f"{len(resumen_vends)} Vendedores", styles['TableHdr']),
            Paragraph(f"${tot_fact:,.2f}", styles['TableHdr']),
            Paragraph(f"{tot_units:,.0f}", styles['TableHdr']),
            Paragraph(f"{sum(int(v.get('num_facturas', 0) or 0) for v in resumen_vends)}", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("—", styles['TableHdr']),
            Paragraph("100.0%", styles['TableHdr']),
            Paragraph("Consolidado Oficial", styles['TableHdr'])
        ])

        t_table_vv = Table(t_data_vv, colWidths=col_widths_vv, repeatRows=1)
        t_style_vv = [
            ('BACKGROUND', (0, 0), (-1, 0), C_EMERALD_HEADER),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#064E3B")),
        ]
        for r in range(1, len(t_data_vv) - 1):
            bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
            t_style_vv.append(('BACKGROUND', (0, r), (-1, r), bg))

        t_table_vv.setStyle(TableStyle(t_style_vv))
        story.append(t_table_vv)

        # Página 2: Top Productos por cada Vendedor
        if any(v.get("productos_vendidos") for v in resumen_vends):
            story.append(PageBreak())
            banner_pv = _crear_banner_flujo(
                titulo=f"CHALLENGER AUTOMOTIVE — DESGLOSE DE PRODUCTOS POR VENDEDOR ({periodo_nom.upper()})",
                subtitulo=f"Detalle de productos comercializados por cada ejecutivo de ventas",
                ancho_total=ancho_doc,
                color_fondo=C_SLATE_DARK,
                styles=styles
            )
            story.append(banner_pv)
            story.append(Spacer(1, 10))

            headers_pv = ["#", "Vendedor", "Producto / Código", "Marca", "Cantidad", "P. Prom ($)", "Total Facturado ($)", "% Vend", "Facturas"]
            col_widths_pv = [20, 120, 200, 55, 50, 65, 80, 50, 45]
            t_data_pv = [[Paragraph(h, styles['TableHdr']) for h in headers_pv]]

            for v in resumen_vends:
                v_nom = v.get("vendedor", "")
                for p in v.get("productos_vendidos", []):
                    t_data_pv.append([
                        Paragraph(str(p.get("posicion", 1)), styles['TableCellCenter']),
                        Paragraph(v_nom, styles['TableCell']),
                        Paragraph(str(p.get("producto", "")), styles['TableCellBold']),
                        Paragraph(str(p.get("categoria", "")), styles['TableCellCenter']),
                        Paragraph(f"{float(p.get('cantidad', 0) or 0):,.0f}", styles['TableCellRight']),
                        Paragraph(f"${float(p.get('precio_promedio', 0) or 0):,.2f}", styles['TableCellRight']),
                        Paragraph(f"${float(p.get('subtotal', 0) or 0):,.2f}", styles['TableCellRight']),
                        Paragraph(f"{float(p.get('pct_del_vendedor', 0) or 0):.1f}%", styles['TableCellCenter']),
                        Paragraph(str(p.get("num_facturas", 0)), styles['TableCellCenter'])
                    ])

            t_table_pv = Table(t_data_pv, colWidths=col_widths_pv, repeatRows=1)
            t_style_pv = [
                ('BACKGROUND', (0, 0), (-1, 0), C_SLATE_DARK),
                ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 2.5),
            ]
            for r in range(1, len(t_data_pv)):
                bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
                t_style_pv.append(('BACKGROUND', (0, r), (-1, r), bg))

            t_table_pv.setStyle(TableStyle(t_style_pv))
            story.append(t_table_pv)

    elif tipo == "ventas_vendedor_3meses":
        # ── REPORTE TRIMESTRAL (3 MESES) POR VENDEDOR & PRODUCTOS ─────────
        vv_data = ml_data or {}
        resumen_3m = vv_data.get("resumen_vendedores_3m") or items or []
        totales = vv_data.get("totales_generales_3m") or {}
        periodos_nombres = vv_data.get("periodos_meses_nombres") or ["Mes 1", "Mes 2", "Mes 3"]
        periodo_label = vv_data.get("periodo_trimestre", "Últimos 3 Meses")

        tot_fact = totales.get("total_facturado", sum(float(v.get("total_subtotal_3m", 0) or 0) for v in resumen_3m))
        tot_units = totales.get("total_unidades", sum(float(v.get("total_cantidad_3m", 0) or 0) for v in resumen_3m))
        v_lider = totales.get("vendedor_lider", "—")

        banner = _crear_banner_flujo(
            titulo=f"CHALLENGER AUTOMOTIVE — VENTAS POR VENDEDOR ({periodo_label.upper()})",
            subtitulo=f"Empresa: {empresa_nombre}  |  Reporte consolidado de los últimos 3 meses por ejecutivo",
            ancho_total=ancho_doc,
            color_fondo=C_PURPLE_HEADER,
            styles=styles
        )
        story.append(banner)
        story.append(Spacer(1, 10))

        kpis = [
            {"label": f"Facturación Trimestral ({periodo_label})", "value": f"${tot_fact:,.2f}", "text_color": "#581C87"},
            {"label": "Unidades Totales (3 Meses)", "value": f"{int(tot_units):,} uds", "text_color": "#1E40AF"},
            {"label": "Vendedor Líder Trimestral", "value": f"{v_lider}", "text_color": "#065F46"},
            {"label": "Ejecutivos Evaluados", "value": f"{len(resumen_3m)} vendedores", "text_color": "#92400E"}
        ]
        story.append(_crear_tarjetas_kpi_flujo(kpis, ancho_total=ancho_doc, styles=styles))
        story.append(Spacer(1, 12))

        # Tabla Resumen Trimestral de Vendedores
        headers_3m = [
            "#", "Vendedor Oficial",
            f"{periodos_nombres[0]}", f"{periodos_nombres[1]}", f"{periodos_nombres[2]}",
            "Total 3M ($)", "Unidades (3M)", "Fact #", "% Total", "Tendencia"
        ]
        col_widths_3m = [20, 130, 70, 70, 70, 85, 55, 45, 50, 55]
        t_data_3m = [[Paragraph(h, styles['TableHdr']) for h in headers_3m]]

        for v in resumen_3m:
            mom = v.get("tendencia_mom", 0)
            mom_str = f"{'+' if mom > 0 else ''}{mom:.1f}%"
            t_data_3m.append([
                Paragraph(str(v.get("posicion", 1)), styles['TableCellCenter']),
                Paragraph(str(v.get("vendedor", "")), styles['TableCellBold']),
                Paragraph(f"${float(v.get('sub_mes_1', 0) or 0):,.0f}", styles['TableCellRight']),
                Paragraph(f"${float(v.get('sub_mes_2', 0) or 0):,.0f}", styles['TableCellRight']),
                Paragraph(f"${float(v.get('sub_mes_3', 0) or 0):,.0f}", styles['TableCellRight']),
                Paragraph(f"<b>${float(v.get('total_subtotal_3m', 0) or 0):,.2f}</b>", styles['TableCellRight']),
                Paragraph(f"{float(v.get('total_cantidad_3m', 0) or 0):,.0f}", styles['TableCellRight']),
                Paragraph(str(v.get("num_facturas_3m", 0)), styles['TableCellCenter']),
                Paragraph(f"{float(v.get('pct_participacion_3m', 0) or 0):.1f}%", styles['TableCellCenter']),
                Paragraph(mom_str, styles['TableCellCenter'])
            ])

        t_data_3m.append([
            Paragraph("TOTAL", styles['TableHdr']),
            Paragraph(f"{len(resumen_3m)} Vendedores", styles['TableHdr']),
            Paragraph(f"${sum(float(v.get('sub_mes_1', 0) or 0) for v in resumen_3m):,.0f}", styles['TableHdr']),
            Paragraph(f"${sum(float(v.get('sub_mes_2', 0) or 0) for v in resumen_3m):,.0f}", styles['TableHdr']),
            Paragraph(f"${sum(float(v.get('sub_mes_3', 0) or 0) for v in resumen_3m):,.0f}", styles['TableHdr']),
            Paragraph(f"${tot_fact:,.2f}", styles['TableHdr']),
            Paragraph(f"{tot_units:,.0f}", styles['TableHdr']),
            Paragraph(f"{sum(int(v.get('num_facturas_3m', 0) or 0) for v in resumen_3m)}", styles['TableHdr']),
            Paragraph("100.0%", styles['TableHdr']),
            Paragraph("—", styles['TableHdr'])
        ])

        t_table_3m = Table(t_data_3m, colWidths=col_widths_3m, repeatRows=1)
        t_style_3m = [
            ('BACKGROUND', (0, 0), (-1, 0), C_PURPLE_HEADER),
            ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#3B0764")),
        ]
        for r in range(1, len(t_data_3m) - 1):
            bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
            t_style_3m.append(('BACKGROUND', (0, r), (-1, r), bg))

        t_table_3m.setStyle(TableStyle(t_style_3m))
        story.append(t_table_3m)

        # Página 2: Desglose de Productos por Vendedor en 3 Meses
        if any(v.get("productos_vendidos_3m") for v in resumen_3m):
            story.append(PageBreak())
            banner_p3m = _crear_banner_flujo(
                titulo=f"CHALLENGER AUTOMOTIVE — PRODUCTOS POR VENDEDOR ({periodo_label.upper()})",
                subtitulo=f"Detalle de productos comercializados por cada ejecutivo en los últimos 3 meses",
                ancho_total=ancho_doc,
                color_fondo=C_SLATE_DARK,
                styles=styles
            )
            story.append(banner_p3m)
            story.append(Spacer(1, 10))

            headers_p3m = [
                "#", "Vendedor", "Producto / Código", "Marca",
                f"Cant {periodos_nombres[0]}", f"Cant {periodos_nombres[1]}", f"Cant {periodos_nombres[2]}",
                "Cant Total", "P. Prom ($)", "Total 3M ($)", "% Vend"
            ]
            col_widths_p3m = [18, 100, 160, 45, 45, 45, 45, 45, 55, 65, 40]
            t_data_p3m = [[Paragraph(h, styles['TableHdr']) for h in headers_p3m]]

            for v in resumen_3m:
                v_nom = v.get("vendedor", "")
                for p in v.get("productos_vendidos_3m", []):
                    t_data_p3m.append([
                        Paragraph(str(p.get("posicion", 1)), styles['TableCellCenter']),
                        Paragraph(v_nom, styles['TableCell']),
                        Paragraph(str(p.get("producto", "")), styles['TableCellBold']),
                        Paragraph(str(p.get("categoria", "")), styles['TableCellCenter']),
                        Paragraph(f"{float(p.get('cant_mes_1', 0) or 0):,.0f}", styles['TableCellRight']),
                        Paragraph(f"{float(p.get('cant_mes_2', 0) or 0):,.0f}", styles['TableCellRight']),
                        Paragraph(f"{float(p.get('cant_mes_3', 0) or 0):,.0f}", styles['TableCellRight']),
                        Paragraph(f"<b>{float(p.get('total_cantidad_3m', 0) or 0):,.0f}</b>", styles['TableCellRight']),
                        Paragraph(f"${float(p.get('precio_promedio_3m', 0) or 0):,.2f}", styles['TableCellRight']),
                        Paragraph(f"${float(p.get('total_subtotal_3m', 0) or 0):,.2f}", styles['TableCellRight']),
                        Paragraph(f"{float(p.get('pct_del_vendedor_3m', 0) or 0):.1f}%", styles['TableCellCenter'])
                    ])

            t_table_p3m = Table(t_data_p3m, colWidths=col_widths_p3m, repeatRows=1)
            t_style_p3m = [
                ('BACKGROUND', (0, 0), (-1, 0), C_SLATE_DARK),
                ('GRID', (0, 0), (-1, -1), 0.5, C_BORDER),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 2.5),
            ]
            for r in range(1, len(t_data_p3m)):
                bg = C_WHITE if r % 2 == 1 else C_ZEBRA_LIGHT
                t_style_p3m.append(('BACKGROUND', (0, r), (-1, r), bg))

            t_table_p3m.setStyle(TableStyle(t_style_p3m))
            story.append(t_table_p3m)

    # Construir PDF usando NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    return tmp.name
