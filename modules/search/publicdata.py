# modules/search/publicdata.py
import logging

logger = logging.getLogger(__name__)


def search_government_records(query: str, filters: dict = None) -> list:
    """
    Búsqueda en registros públicos de gobierno (simulada).
    """
    logger.info(f"Buscando en registros públicos sobre: {query}")

    # Simulación de resultados
    results = [
        {
            "document_type": "Certificado de Nacimiento",
            "issue_date": "2020-04-15",
            "agency": "Registro Civil Distrito Federal",
            "status": "Verificado",
            "details": "Nombre y fecha correctos según documento físico"
        },
        {
            "document_type": "Licencia de Conducir",
            "issue_date": "2018-07-20",
            "agency": "Secretaría de Seguridad Pública",
            "status": "Vigente",
            "details": "No tiene infracciones registradas"
        }
    ]
    return results


def search_public_company_data(company_name: str) -> dict:
    """
    Búsqueda de información oficial de empresas públicas.
    """
    logger.info(f"Buscando datos públicos de empresa: {company_name}")

    # Simulación de datos de empresa pública
    results = {
        "company_name": company_name,
        "registration_date": "2005-03-12",
        "legal_status": "Sociedad Anónima",
        "sector": "Sector Financiero",
        "registration_number": "RFC123456ABC",
        "offices": [
            {"branch": "Oficina Central", "city": "Ciudad de México", "address": "Av. Reforma 123"},
            {"branch": "Sucursal Norte", "city": "Guadalajara", "address": "Calle Principal 456"}
        ],
        "financial_info": {
            "last_reported_revenue": "$100 millones USD",
            "profit_margin": "12%",
            "assets": "$200 millones USD"
        }
    }
    return results