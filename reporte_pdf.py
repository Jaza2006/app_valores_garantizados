from datetime import datetime
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

AZUL = colors.HexColor("#1F3A5F")
AZUL_CLARO = colors.HexColor("#E8EEF5")
GRIS = colors.HexColor("#6B7280")


def _money(v) -> str:
    return f"${float(v):,.2f}"


def _estilos():
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", parent=base["Title"], fontSize=18,
                                 textColor=AZUL, spaceAfter=2),
        "sub": ParagraphStyle("sub", parent=base["Normal"], fontSize=9,
                              textColor=GRIS, alignment=TA_CENTER, spaceAfter=10),
        "h": ParagraphStyle("h", parent=base["Heading2"], fontSize=12,
                            textColor=AZUL, spaceBefore=10, spaceAfter=4),
        "n": ParagraphStyle("n", parent=base["Normal"], fontSize=9, leading=12),
        "nota": ParagraphStyle("nota", parent=base["Normal"], fontSize=7.5,
                               leading=10, textColor=GRIS),
    }


def _tabla_clave_valor(filas, ancho_total):
    """Tabla de 2 columnas (concepto / valor) con estilo ejecutivo."""
    t = Table(filas, colWidths=[ancho_total * 0.55, ancho_total * 0.45])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, AZUL_CLARO]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _pie_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRIS)
    canvas.drawString(0.75 * inch, 0.5 * inch,
                      "Matematicas Actuariales - Valores Garantizados")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch,
                           f"Página {doc.page}")
    canvas.restoreState()


def generar_pdf_ejecutivo(
    params: dict,
    primas: dict,
    garantizados_t: dict,
    df_proyeccion: pd.DataFrame,
) -> bytes:
    """
    params:  datos de la póliza y supuestos (ver app.py)
    primas:  PNN, PPT, gamma, beta, K, etc.
    garantizados_t: rescate, saldado, prorroga y dote al año evaluado
    df_proyeccion: tabla proyectada (misma que se ve en pantalla)
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.7 * inch, bottomMargin=0.8 * inch,
        title="Poliza - JR Valores Garantizados",
        author="Rolando y Jazael",
    )
    ancho = letter[0] - 1.5 * inch
    est = _estilos()
    story = []

    # ---------- Encabezado ----------
    story.append(Paragraph("Reporte Ejecutivo", est["titulo"]))
    story.append(Paragraph(
        f"Prima Comercial y Valores Garantizados &nbsp;|&nbsp; "
        f"Generado el {datetime.now():%d/%m/%Y %H:%M}", est["sub"]))

    # ---------- 1. Datos de la póliza ----------
    story.append(Paragraph("1. Datos de la póliza y supuestos", est["h"]))
    story.append(_tabla_clave_valor([
        ["Tipo de seguro", params["tipo"]],
        ["Edad de contratación (x)", str(params["edad"])],
        ["Suma asegurada", _money(params["sa"])],
        ["Plazo de cobertura (n)", params["plazo_cobertura"]],
        ["Plazo de pagos (p)", params["plazo_pagos"]],
        ["Tasa de interés anual", f"{params['tasa_pct']:.2f}%"],
        ["Tabla de mortalidad", params["tabla"]],
        ["Escenario de recargos", params["escenario"]],
    ], ancho))

    # ---------- 2. Primas ----------
    story.append(Paragraph("2. Resultados de la póliza (primas anuales)", est["h"]))
    story.append(_tabla_clave_valor([
        ["Prima Neta Nivelada (PNN)", _money(primas["pnn"])],
        ["Prima Comercial (PPT)", _money(primas["ppt"])],
        ["Gastos de administración (gamma)", f"{primas['gamma'] * 1000:.2f} al millar de la SA"],
        ["Gastos de cobranza (beta)", f"{primas['beta'] * 100:.2f}% de la prima"],
        ["Comisión de agenciamiento (K)", f"{primas['k'] * 100:.1f}% de la prima"],
        ["Honorarios médicos (alpha)", f"{primas['alpha'] * 1000:.2f} al millar de la SA"],
    ], ancho))

    # ---------- 3. Valores garantizados al año t ----------
    g = garantizados_t
    story.append(KeepTogether([
        Paragraph(
            f"3. Valores garantizados al año t = {g['t']} (edad {g['edad']})",
            est["h"]),
        _tabla_clave_valor([
            ["Valor de rescate", _money(g["rescate"])],
            ["Seguro saldado (suma asegurada reducida)", _money(g["saldado"])],
            ["Seguro prorrogado", g["prorroga"]],
            ["Dote sobrante", _money(g["dote"])],
        ], ancho),
    ]))

    # ---------- 4. Tabla proyectada ----------
    story.append(PageBreak())
    story.append(Paragraph("4. Tabla proyectada de valores garantizados", est["h"]))

    encabezado = ["t", "Edad", "Reserva\nneta", "Ajuste\nZillmer",
                  "Valor de\nrescate", "Seguro\nsaldado", "Prórroga", "Dote\nsobrante"]
    filas = [encabezado]
    for _, r in df_proyeccion.iterrows():
        filas.append([
            int(r["Año (t)"]), int(r["Edad (x+t)"]),
            f"{r['Reserva Neta ($)']:,.2f}",
            f"{r['Ajuste Zillmer ($)']:,.2f}",
            f"{r['Valor de Rescate ($)']:,.2f}",
            f"{r['Seguro Saldado ($)']:,.2f}",
            r["Prórroga (Tiempo)"],
            f"{r['Dote Sobrante ($)']:,.2f}",
        ])

    anchos = [0.3, 0.4, 0.95, 0.9, 0.95, 0.95, 0.85, 0.8]
    suma = sum(anchos)
    t = Table(filas, colWidths=[ancho * a / suma for a in anchos], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("LEADING", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 1), (1, -1), "CENTER"),
        ("ALIGN", (2, 1), (5, -1), "RIGHT"),
        ("ALIGN", (6, 1), (6, -1), "CENTER"),
        ("ALIGN", (7, 1), (7, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, AZUL_CLARO]),
        ("LINEBELOW", (0, 1), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    # ---------- Notas ----------
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Notas: el valor de rescate se calcula con la reserva Zillmerizada "
        "El seguro saldado es la suma asegurada reducida que se compra con el "
        "valor de rescate. El seguro prorrogado es el tiempo de cobertura "
        "(seguro temporal) que compra el valor de rescate. Resultados "
        "calculados con la tabla de mortalidad y la tasa indicadas; sujetos a "
        "los supuestos de recargos mostrados.", est["nota"]))

    doc.build(story, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
    return buffer.getvalue()