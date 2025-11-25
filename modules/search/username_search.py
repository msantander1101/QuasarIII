# modules/search/username_search.py
"""
Búsqueda especializada de usernames y direcciones de correo
"""
import logging
import re
import requests
from typing import List, Dict, Any
from core.config_manager import config_manager
import streamlit as st

logger = logging.getLogger(__name__)

# Posibles fuentes de búsqueda de usernames
# Usaremos solo fuentes que no requieran claves API o que sean públicas
USERNAME_SOURCES = [
    'github',
    'twitter',
    'linkedin',
    'facebook',
    'reddit',
    'pastebin'
]


def search_usernames_and_emails(query: str) -> List[Dict[str, Any]]:
    """
    Búsqueda especializada solo de usernames y emails en fuentes públicas

    Args:
        query: Término de búsqueda (nombre, username, email)

    Returns:
        Lista de resultados encontrados con username y email
    """
    logger.info(f"Buscando usernames/emails por: {query}")

    # Validar que el query sea válido
    if not query or len(query.strip()) < 2:
        return []

    results = []

    try:
        # Extraer posible email del query
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, query)

        # Si hay un email válido, lo añadimos
        for email in emails:
            results.append({
                "type": "email",
                "value": email,
                "source": "query",
                "confidence": 0.9,
                "details": "Email extraído directamente del query"
            })

        # Verificar si el query es un nombre completo
        if len(query.split()) >= 2 and len(query) <= 50:
            # Simulación de búsqueda en fuentes públicas para usuarios
            # En entornos reales, podrías conectarte aquí con APIs públicas o scraping
            simulated_results = simulate_username_search(query)
            results.extend(simulated_results)

        # Si solo hay un término (posible username)
        elif len(query.split()) == 1 and len(query) <= 30:
            # Verificar si es un email que ya no fue detectado
            if '@' not in query:
                # Búsqueda simular username en GitHub
                simulated_results = simulate_github_username_search(query)
                results.extend(simulated_results)

    except Exception as e:
        logger.error(f"Error en búsqueda de usernames/emails: {e}")

    return results


def simulate_username_search(name: str) -> List[Dict[str, Any]]:
    """
    Simulación de búsqueda de username basada en nombre (en realidad no se hace búsqueda real)
    """
    # Simulamos algunos resultados posibles
    results = []

    # Intentar generar algún resultado basado en nombres
    if ' ' in name:
        parts = name.split()
        if len(parts) >= 2:
            # Generar posibles usernames combinando partes
            first_part = parts[0].lower()
            last_part = parts[-1].lower()

            # Posibles combinaciones
            possible_usernames = [
                f"{first_part}{last_part}",
                f"{first_part}.{last_part}",
                f"{first_part}_{last_part}",
                f"{last_part}{first_part}",
                f"{first_part[0]}{last_part}",
                f"{first_part}{last_part[0]}",
                f"{first_part}-{last_part}",
                f"{last_part}-{first_part}"
            ]

            # Añadir algunos como resultado
            for i, uname in enumerate(possible_usernames[:3]):  # Limitar a 3
                if len(uname) >= 3:
                    results.append({
                        "type": "username",
                        "value": uname,
                        "source": "simulation",
                        "confidence": 0.6 - (i * 0.05),  # Menor confianza cuanto más lejos esté de la primera
                        "details": f"Posible username generado a partir de '{name}'"
                    })

    # Si es un nombre solo...
    if len(name.split()) == 1:
        results.append({
            "type": "username",
            "value": name.lower(),
            "source": "direct",
            "confidence": 0.7,
            "details": "Username directo como se ingresa"
        })

    return results


def simulate_github_username_search(username: str) -> List[Dict[str, Any]]:
    """
    Simulación de búsqueda de username en GitHub
    """
    results = []

    # Simular búsqueda con un patrón común
    if len(username) >= 2:
        # Si hay patrones comunes en repositorios de GitHub
        possible_usernames = [
            username.lower(),
            f"{username.lower()}_dev",
            f"{username.lower()}_user",
            f"dev_{username.lower()}",
            f"user_{username.lower()}"
        ]

        for i, uname in enumerate(possible_usernames[:3]):
            if len(uname) >= 3:
                results.append({
                    "type": "username",
                    "value": uname,
                    "source": "github_sim",
                    "confidence": 0.5 + (i * 0.05),
                    "details": f"Simulación de username en GitHub"
                })

    return results


def search_simple_emails(query: str) -> List[Dict[str, Any]]:
    """
    Búsqueda simple solo de correos electrónicos en el parámetro de búsqueda
    """
    emails_found = []

    try:
        # Pattern más robusto para encontrar emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        found_emails = re.findall(email_pattern, query)

        for email in found_emails:
            emails_found.append({
                "type": "email",
                "value": email,
                "source": "direct_query",
                "confidence": 0.95,
                "details": "Email encontrado directamente en consulta"
            })

    except Exception as e:
        logger.error(f"Error buscando emails: {e}")

    return emails_found


# Función pública para usar desde otros módulos
def find_usernames_and_emails(query: str) -> List[Dict[str, Any]]:
    """
    Función principal que busca usernames y emails de forma especializada
    """
    try:
        # Primero buscamos emails
        email_results = search_simple_emails(query)

        # Después buscamos usernames
        username_results = search_usernames_and_emails(query)

        # Combinamos resultados y los devolvemos
        all_results = email_results + username_results

        return all_results
    except Exception as e:
        logger.error(f"Error general en búsqueda de usernames/emails: {e}")
        return []


# Funciones más específicas si se quiere usar directamente desde la UI
def search_usernames_only(query: str) -> List[Dict[str, Any]]:
    """
    Búsqueda solo de usernames
    """
    return search_usernames_and_emails(query)


def search_emails_only(query: str) -> List[Dict[str, Any]]:
    """
    Búsqueda solo de emails
    """
    return search_simple_emails(query)
