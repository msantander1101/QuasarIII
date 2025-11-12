from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, ListFlowable, ListItem, Frame, PageTemplate
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Line
from reportlab.graphics import renderPDF
import io
import json
from datetime import datetime
from babel.dates import format_datetime


class PDFReport:
    """
    Generador de reportes OSINT profesional
    """

    def __init__(self, title="OSINT Report"):
        self.title = title
        self.styles = self._create_custom_styles()
        self.elements = []
        self.buffer = io.BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

    def _create_custom_styles(self):
        """Crea estilos personalizados para el reporte"""
        styles = getSampleStyleSheet()

        # Título principal
        styles.add(ParagraphStyle(
            name='CustomTitle',
            fontSize=24,
            leading=30,
            alignment=1,  # Center
            spaceAfter=30,
            textColor=colors.HexColor('#1f4e79'),
            fontName='Helvetica-Bold'
        ))

        # Subtítulo
        styles.add(ParagraphStyle(
            name='CustomHeading',
            fontSize=16,
            leading=20,
            spaceAfter=12,
            textColor=colors.HexColor('#2e75b6'),
            fontName='Helvetica-Bold'
        ))

        # Texto normal
        styles.add(ParagraphStyle(
            name='CustomBody',
            fontSize=10,
            leading=14,
            spaceAfter=8,
            textColor=colors.black,
            fontName='Helvetica'
        ))

        # Texto de código/datos
        styles.add(ParagraphStyle(
            name='Code',
            fontSize=8,
            leading=10,
            fontName='Courier',
            textColor=colors.HexColor('#c7254e'),
            backColor=colors.HexColor('#f9f2f4')
        ))

        # Alerta crítica
        styles.add(ParagraphStyle(
            name='Critical',
            fontSize=11,
            leading=14,
            textColor=colors.red,
            fontName='Helvetica-Bold'
        ))

        # Éxito (dato positivo)
        styles.add(ParagraphStyle(
            name='Success',
            fontSize=11,
            leading=14,
            textColor=colors.green,
            fontName='Helvetica'
        ))

        return styles

    def add_title_page(self, investigator, target, case_id=None):
        """Página de portada"""
        # Logo (opcional)
        try:
            logo = Image("assets/logo.png", width=2 * inch, height=1 * inch)
            self.elements.append(logo)
            self.elements.append(Spacer(1, 20))
        except:
            pass

        # Título
        self.elements.append(Paragraph(self.title, self.styles['CustomTitle']))
        self.elements.append(Spacer(1, 30))

        # Información del caso
        data = [
            ["Investigador:", investigator],
            ["Target:", target],
            ["Fecha:", format_datetime(datetime.now(), format='long', locale='es_ES')],
            ["Case ID:", case_id or "N/A"],
        ]

        table = Table(data, colWidths=[2 * inch, 4 * inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))

        self.elements.append(table)
        self.elements.append(PageBreak())

    def add_executive_summary(self, findings_count, critical_findings, modules_used):
        """Resumen ejecutivo"""
        self.elements.append(Paragraph("RESUMEN EJECUTIVO", self.styles['CustomHeading']))
        self.elements.append(Spacer(1, 10))

        summary_text = f"""
        Esta investigación OSINT reveló un total de <b>{findings_count} hallazgos</b> 
        distribuidos en {modules_used} módulos de análisis. Se identificaron 
        <font color='red'><b>{critical_findings} hallazgos críticos</b></font> 
        que requieren atención inmediata.

        El reporte detalla información recolectada de múltiples fuentes abiertas, 
        redes sociales, breaches de datos y otras fuentes de inteligencia digital.
        """

        self.elements.append(Paragraph(summary_text, self.styles['CustomBody']))
        self.elements.append(PageBreak())

    def add_section_header(self, title, module_name, findings_count):
        """Cabecera de sección por módulo"""
        self.elements.append(Paragraph(title, self.styles['CustomHeading']))

        # Métricas en cuadro
        metrics_data = [
            ["Módulo:", module_name],
            ["Hallazgos:", str(findings_count)],
            ["Fecha de ejecución:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        ]

        metrics_table = Table(metrics_data, colWidths=[2 * inch, 4 * inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f8ff')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#2e75b6')),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))

        self.elements.append(metrics_table)
        self.elements.append(Spacer(1, 15))

    def add_findings_table(self, findings, headers):
        """Tabla de hallazgos"""
        if not findings:
            self.elements.append(Paragraph("No se encontraron resultados", self.styles['CustomBody']))
            return

        # Preparar datos
        data = [headers]
        for item in findings:
            row = [str(item.get(h, "N/A")) for h in headers]
            data.append(row)

        # Crear tabla
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e75b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f8ff')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#2e75b6')),
        ]))

        self.elements.append(table)
        self.elements.append(Spacer(1, 10))

    def add_critical_finding(self, title, description, risk_level="ALTO"):
        """Hallazgo crítico en caja roja"""
        risk_colors = {
            "ALTO": colors.red,
            "MEDIO": colors.orange,
            "BAJO": colors.green
        }

        data = [
            [f"🚨 HALLAZGO CRÍTICO - RIESGO: {risk_level}", ""],
            ["Título:", title],
            ["Descripción:", description]
        ]

        table = Table(data, colWidths=[1.5 * inch, 4.5 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), risk_colors.get(risk_level, colors.red)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ffe6e6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.red),
        ]))

        self.elements.append(table)
        self.elements.append(Spacer(1, 15))

    def add_json_data(self, data, title="Datos"):
        """JSON formateado"""
        self.elements.append(Paragraph(title, self.styles['CustomHeading']))
        json_str = json.dumps(data, indent=2, ensure_ascii=False)

        # Dividir en líneas para evitar desbordamiento
        for line in json_str.split('\n'):
            self.elements.append(Paragraph(line, self.styles['Code']))

        self.elements.append(Spacer(1, 10))

    def add_chart(self, chart_type, data, title):
        """Gráfico simple (barra/pie)"""
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics.charts.textlabels import Label

        d = Drawing(400, 200)

        if chart_type == "bar":
            chart = VerticalBarChart()
            chart.x = 50
            chart.y = 50
            chart.height = 125
            chart.width = 300
            chart.data = [list(data.values())]
            chart.categoryAxis.categoryNames = list(data.keys())
            d.add(chart)

        elif chart_type == "pie":
            pie = Pie()
            pie.x = 150
            pie.y = 50
            pie.height = 125
            pie.width = 125
            pie.data = list(data.values())
            pie.labels = list(data.keys())
            d.add(pie)

        self.elements.append(Paragraph(title, self.styles['CustomHeading']))
        self.elements.append(d)
        self.elements.append(Spacer(1, 10))

    def generate(self):
        """Generar PDF y retornar bytes"""
        self.doc.build(self.elements)
        return self.buffer.getvalue()