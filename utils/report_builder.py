import streamlit as st
from datetime import datetime
from utils.pdf_generator import PDFReport
import json


class OSINTReportBuilder:
    """
    Construye reportes automáticamente desde resultados de módulos
    """

    def __init__(self, user_id, target_info, module_results):
        self.user_id = user_id
        self.target = target_info  # dict con username, email, etc.
        self.results = module_results  # dict con resultados por módulo
        self.critical_findings = []

    def analyze_critical_findings(self):
        """Analiza y extrae hallazgos críticos automáticamente"""
        for module_name, data in self.results.items():
            if not data:
                continue

            # SOC MINT - Perfiles sensibles
            if module_name == "socmint":
                for profile in data.get('profiles', []):
                    if profile.get('platform') in ['OnlyFans', 'Tinder', 'Grindr']:
                        self.critical_findings.append({
                            "module": "SOCMINT",
                            "title": f"Perfil en plataforma sensible: {profile['platform']}",
                            "description": f"Usuario encontrado en {profile['url']}",
                            "risk": "ALTO"
                        })

            # BREACH DATA - Email comprometido
            if module_name == "breachdata":
                if data.get('found_breaches'):
                    self.critical_findings.append({
                        "module": "Breach Data",
                        "title": f"Email comprometido en {len(data['found_breaches'])} breaches",
                        "description": f"Breach más reciente: {data['found_breaches'][0]}",
                        "risk": "ALTO"
                    })

            # TELEFONO - Exposición
            if module_name == "phoneint":
                if data.get('is_valid') and data.get('is_disposable'):
                    self.critical_findings.append({
                        "module": "Phone Intel",
                        "title": "Número de teléfono desechable detectado",
                        "description": "Posible intento de anonimato",
                        "risk": "MEDIO"
                    })

            # IMAGENES - Metadata con ubicación
            if module_name == "imageint":
                for img in data.get('images', []):
                    if img.get('gps_coordinates'):
                        self.critical_findings.append({
                            "module": "Image Intel",
                            "title": "Imagen con metadata de ubicación GPS",
                            "description": f"Coordenadas: {img['gps_coordinates']}",
                            "risk": "ALTO"
                        })

    def build_report(self, investigator_name):
        """Generar reporte completo"""
        report = PDFReport(title=f"OSINT Report - {self.target.get('username', 'Target')}")

        # Página de título
        report.add_title_page(
            investigator=investigator_name,
            target=self.target.get('username') or self.target.get('email') or "N/A",
            case_id=f"OSINT-{datetime.now().strftime('%Y%m%d')}-{self.user_id}"
        )

        # Resumen ejecutivo
        self.analyze_critical_findings()
        total_findings = sum(len(v) for v in self.results.values() if v)

        report.add_executive_summary(
            findings_count=total_findings,
            critical_findings=len(self.critical_findings),
            modules_used=len([k for k, v in self.results.items() if v])
        )

        # Hallazgos críticos (primero)
        if self.critical_findings:
            report.add_section_header(
                "HALLAZGOS CRÍTICOS",
                "CRITICAL ANALYSIS",
                len(self.critical_findings)
            )

            for finding in self.critical_findings:
                report.add_critical_finding(
                    title=finding['title'],
                    description=finding['description'],
                    risk_level=finding['risk']
                )

            report.add_page_break()

        # Resultados por módulo
        for module_name, data in self.results.items():
            if not data:
                continue

            # Mapeo de nombres amigables
            module_titles = {
                "general_search": "Búsqueda General",
                "socmint": "Inteligencia de Redes Sociales",
                "breachdata": "Análisis de Breaches",
                "emailint": "Inteligencia de Email",
                "domainint": "Inteligencia de Dominios",
                "imageint": "Análisis de Imágenes",
                "geoint": "Inteligencia Geográfica",
                "phoneint": "Inteligencia Telefónica"
            }

            title = module_titles.get(module_name, module_name.upper())

            report.add_section_header(
                title=title,
                module_name=module_name,
                findings_count=len(data)
            )

            # Formato específico por módulo
            if module_name == "socmint":
                profiles = data.get('profiles', [])
                if profiles:
                    findings = [
                        {
                            "Plataforma": p.get('platform'),
                            "URL": p.get('url'),
                            "Estado": "Encontrado",
                            "Categoría": p.get('category', 'N/A')
                        }
                        for p in profiles
                    ]
                    report.add_findings_table(
                        findings,
                        ["Plataforma", "URL", "Estado", "Categoría"]
                    )

            elif module_name == "breachdata":
                breaches = data.get('found_breaches', [])
                if breaches:
                    report.add_json_data(breaches, "Breaches Encontrados")

            elif module_name == "geoint":
                coords = data.get('coordinates', {})
                if coords:
                    report.add_json_data(coords, "Coordenadas GPS")

            else:
                # JSON genérico para otros módulos
                report.add_json_data(data, f"Datos de {module_name}")

            report.add_spacer()

        # Métricas finales
        report.add_chart(
            "bar",
            {k: len(v) for k, v in self.results.items() if v},
            "Distribución de Hallazgos por Módulo"
        )

        return report.generate()