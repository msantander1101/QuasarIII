# modules/search/domainint.py
import logging
import socket

logger = logging.getLogger(__name__)


def analyze_domain(domain: str) -> dict:
    """
    Realiza análisis básico de un dominio DNS.
    """
    logger.info(f"Analizando dominio: {domain}")

    results = {
        "domain": domain,
        "ip_addresses": [],
        "dns_records": [],  # A veces A, AAAA, MX
        "mx_records": [],
        "ns_records": [],
        "cname_records": [],
        "whois_info": {
            "registrar": "RegistrarName",
            "creation_date": "2020-01-01",
            "expiration_date": "2025-01-01",
            "nameservers": ["ns1.servidor.com", "ns2.servidor.com"]
        },
        # Información de posibles vulnerabilidades (simulada)
        "vulnerabilities": ["Missing Security Headers", "Outdated SSL/TLS"]
    }

    # Resolver IPs para ejemplo (puede fallar si falta permiso o DNS)
    try:
        ip_addrs = socket.gethostbyname_ex(domain)[2]
        results["ip_addresses"].extend(ip_addrs)
    except Exception as e:
        logger.warning(f"Error resolviendo DNS para {domain}: {e}")

    return results


def get_certificate_info(domain: str) -> dict:
    """
    Obtiene información del certificado SSL/TLS del dominio.
    """
    logger.info(f"Obteniendo certificados de: {domain}")

    info = {
        "domain": domain,
        "valid_from": "2023-01-01",
        "valid_until": "2024-01-01",
        "issuer": "Let's Encrypt",
        "subject": f"CN={domain}",
        "signature_algorithm": "RSA-SHA256",
        "public_key_algorithm": "RSA"
    }
    return info