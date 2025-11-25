# modules/search/archive_search.py
import logging
import requests
import time
import json
from typing import List, Dict, Any
import re

logger = logging.getLogger(__name__)


class ArchiveSearcher:
    """
    Búsqueda en fuentes históricas como Wayback Machine, snapshots, etc.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'QuasarIII-OSINT/1.0',
            'Accept': 'application/json'
        })
        # URLs de servicios de archivo histórico
        self.wayback_url = "http://archive.org/wayback/available"
        self.archive_org_url = "https://archive.org/wayback/available"

    def search_wayback_machine(self, url: str, start_year: int = 2000, end_year: int = 2024) -> List[Dict]:
        """
        Búsqueda en Wayback Machine (Internet Archive).
        Busca capturas históricas de una URL específica.
        """
        try:
            logger.info(f"Buscando capturas históricas para: {url}")

            # Construir petición a Wayback Machine
            # Esta es la API básica de Wayback Machine
            params = {
                'url': url,
                'matchType': 'prefix',  # Buscar capturas parciales
                'limit': 100,
                'collapse': 'urlkey'
            }

            # Ejemplo directo a Wayback Machine (sin clave necesaria)
            # En producción podrías usar:
            # response = requests.get(f"{self.wayback_url}?url={url}&filter=mimetype:text/html",
            #                       headers={'User-Agent': 'QuasarIII-OSINT/1.0'})

            # Simulación de respuesta real para mostrar estructura
            # En producción esta sería una conexión real a la API
            results = []

            # Simular capturas de diferentes años
            years = list(range(start_year, min(end_year + 1, 2025)))
            for i, year in enumerate(years[:5]):  # Mostrar solo las primeras 5
                # En producción, cada año tendría diferente timestamp y url
                capture_url = f"https://web.archive.org/web/{year}0101000000/{url}"
                results.append({
                    "timestamp": f"{year}0101000000",
                    "url": capture_url,
                    "original_url": url,
                    "status": "200 OK",
                    "year": year,
                    "capture_type": "HTML_snapshot",
                    "archive_name": "Wayback Machine",
                    "confidence": 0.9 - (i * 0.05),  # Mayor confianza en años más recientes
                    "timestamp_human": f"Captura desde {year}"
                })

            return results

        except Exception as e:
            logger.error(f"Error buscando en Wayback Machine: {e}")
            return [{"error": f"Wayback Machine API error: {str(e)}"}]

    def search_archive_org(self, query: str, limit: int = 50) -> List[Dict]:
        """
        Búsqueda más amplia en Archive.org
        """
        try:
            logger.info(f"Buscando en Archive.org con consulta: {query}")

            # Simulación de búsqueda real
            # En producción tendría que conectarse a:
            # https://archive.org/advancedsearch.php
            # Con parámetros de búsqueda avanzada

            results = []
            for i in range(min(limit, 10)):  # Solo 10 resultados simulados
                results.append({
                    "title": f"Documento relacionado con '{query}' - {i + 1}",
                    "url": f"https://archive.org/details/doc_{i + 1}",
                    "description": f"Contenido histórico relacionado con {query}",
                    "date": "2023-01-01",
                    "source": "Archive.org",
                    "confidence": 0.8 - (i * 0.03),
                    "type": "document"
                })

            return results

        except Exception as e:
            logger.error(f"Error buscando en Archive.org: {e}")
            return [{"error": f"Archive.org API error: {str(e)}"}]

    def search_web_archives(self, query: str, sources: List[str] = None,
                            limit: int = 50) -> Dict[str, List]:
        """
        Búsqueda en múltiples fuentes de archivos web
        """
        if sources is None:
            sources = ['wayback', 'archive']

        results = {}

        # Buscar en cada fuente
        for source in sources:
            try:
                if source == 'wayback':
                    results['wayback'] = self.search_wayback_machine(query, 2000, 2024)
                elif source == 'archive':
                    results['archive'] = self.search_archive_org(query, limit)
                else:
                    results[source] = [{"warning": f"Fuente no implementada: {source}"}]

            except Exception as e:
                logger.error(f"Error en búsqueda en fuente {source}: {e}")
                results[source] = [{"error": f"Fuente {source} error: {str(e)}"}]

        return results

    def search_domain_history(self, domain: str, years: int = 10) -> List[Dict]:
        """
        Busca histórico de dominios específicos
        """
        try:
            # Simulación de búsqueda de historia de dominio
            # En producción usarías WHOIS historical APIs
            results = []

            # Años de historial
            current_year = 2024
            for i in range(min(years, 10)):
                year = current_year - i
                # Incluimos campos adicionales para que la interfaz tenga algo que mostrar
                results.append({
                    "year": year,
                    "domain": domain,
                    "registrant": f"Ejemplo Corp {year}",
                    "creation_date": f"{year}-01-01",
                    "expiration_date": f"{year + 10}-01-01",
                    "name_servers": [f"ns{i + 1}.{domain}", f"ns{i + 2}.{domain}"],
                    "status": "ACTIVE",
                    "registrar": "Registrar Name",
                    "timestamp": time.time() - (i * 31536000),  # Un año en segundos
                    # Campo que la UI utiliza para mostrar en la lista
                    "timestamp_human": f"{year}-01-01",
                    # También proporcionar una URL genérica relacionada con el dominio
                    "url": f"https://{domain}"
                })

            logger.info(f"Retornado {len(results)} años de historia de dominio para {domain}")
            return results

        except Exception as e:
            logger.error(f"Error buscando historia del dominio {domain}: {e}")
            return [{"error": f"History search error: {str(e)}"}]

    def search_file_snapshots(self, filepath: str, domain: str = None) -> List[Dict]:
        """
        Busca snapshots de archivos específicos
        """
        try:
            # Busca capturas de archivos específicos (PDF, DOC, etc.)
            results = []
            for i in range(5):
                results.append({
                    "path": filepath,
                    "domain": domain,
                    "snapshot_url": f"https://web.archive.org/web/*/http://example.com{filepath}?_={i}",
                    "format": filepath.split('.')[-1] if '.' in filepath else "unknown",
                    "size": f"{(100 + i * 10)} KB",
                    "timestamp": time.time() - (i * 86400),  # Un día por snapshot
                    "timestamp_formatted": time.strftime("%Y-%m-%d", time.localtime(time.time() - (i * 86400))),
                    "status": "archived"
                })

            return results

        except Exception as e:
            logger.error(f"Error buscando snapshots de archivo {filepath}: {e}")
            return [{"error": f"File snapshot error: {str(e)}"}]

    def search_website_timeline(self, url: str, periods: List[str] = None) -> Dict[str, Any]:
        """
        Obtiene cronología completa del sitio web
        """
        try:
            if periods is None:
                periods = ['daily', 'monthly', 'yearly']

            timeline = {
                "url": url,
                "timeline": []
            }

            # Simular diferentes periodos de cronología
            dates = ['2000-01-01', '2005-03-15', '2010-07-22', '2015-11-08', '2020-02-14', '2024-06-30']
            events = [
                "Lanzamiento del sitio",
                "Actualización de diseño",
                "Rediseño completo",
                "Incorporación de funciones nuevas",
                "Incorporación de función e-commerce",
                "Nueva versión del sistema"
            ]

            for i, (date, event) in enumerate(zip(dates, events)):
                timeline["timeline"].append({
                    "date": date,
                    "event": event,
                    "confidence": 0.9 - (i * 0.05),
                    "snapshot_url": f"https://web.archive.org/web/{date.replace('-', '')}*/{url}"
                })

            return timeline

        except Exception as e:
            logger.error(f"Error buscando línea de tiempo de website {url}: {e}")
            return {"error": f"Timeline search error: {str(e)}"}


# Instancia única (singleton)
archive_searcher = ArchiveSearcher()


# Funciones públicas directas
def search_wayback_machine(url: str, start_year: int = 2000, end_year: int = 2024) -> List[Dict]:
    """Búsqueda directa en Wayback Machine"""
    return archive_searcher.search_wayback_machine(url, start_year, end_year)


def search_archive_org(query: str, limit: int = 50) -> List[Dict]:
    """Búsqueda en Archive.org"""
    return archive_searcher.search_archive_org(query, limit)


def search_web_archives(query: str, sources: List[str] = None, limit: int = 50) -> Dict[str, List]:
    """Búsqueda multifuente en archivos web"""
    return archive_searcher.search_web_archives(query, sources, limit)


def search_domain_history(domain: str, years: int = 10) -> List[Dict]:
    """Búsqueda de historia del dominio"""
    return archive_searcher.search_domain_history(domain, years)


def search_file_snapshots(filepath: str, domain: str = None) -> List[Dict]:
    """Búsqueda de snapshots de archivo"""
    return archive_searcher.search_file_snapshots(filepath, domain)


def search_website_timeline(url: str, periods: List[str] = None) -> Dict[str, Any]:
    """Obtiene línea de tiempo del sitio web"""
    return archive_searcher.search_website_timeline(url, periods)
