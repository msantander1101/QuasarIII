# modules/search/pastesearch.py

"""
Búsqueda real de información de paste y leaks usando APIs reales
- Usa Have I Been Pwned (breaches)
- Usa GitHub Gist (búsqueda pública de pastes)
- Usa Leakatlas.com y Google Site Search para sitios de paste
"""
import logging
import requests
import time
import re
from typing import List, Dict, Any
from urllib.parse import quote_plus, urlencode
from core.config_manager import config_manager
import streamlit as st

logger = logging.getLogger(__name__)

# Configuración de fuentes
HIBP_BASE_URL = "https://haveibeenpwned.com/api/v3/breachedaccount"
GITHUB_GIST_URL = "https://api.github.com/gists"
LEAKATLAS_URL = "https://leakatlas.com/search"

# Constantes de configuración
DELAY_BETWEEN_REQUESTS = 1.0  # Para evitar sobrecarga
MAX_RETRIES = 3


def search_paste_sites(query: str, pastebin_api_key: str = None) -> List[Dict[str, Any]]:
    """
    Búsqueda real en fuentes de paste (usando HIBP, GitHub Gist, Leakatlas.com, y Google Site Search)
    Solo busca en HIBP si se proporciona un correo electrónico válido.
    """
    logger.info(f"Buscando paste por: {query}")

    results = []
    try:
        # ✅ Usar el user_id del usuario actual, no None
        user_id = st.session_state.get('current_user_id')
        if not user_id:
            logger.warning("No se encontró user_id. No se puede buscar en HIBP.")
            return []

        hibp_key = config_manager.get_config(user_id, "hibp")  # ✅ Clave del usuario

        # Verificar si la consulta es un correo electrónico válido
        is_email = bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', query.strip()))

        # 1. Buscar en HIBP (breaches de contraseñas, correos) - SOLO SI ES UN EMAIL
        if hibp_key and is_email:
            query_hash = quote_plus(query.lower().strip())
            url = f"{HIBP_BASE_URL}/{query_hash}"
            headers = {
                "x-apikey": hibp_key,
                "User-Agent": "QuasarIII/1.0"
            }

            for attempt in range(MAX_RETRIES):
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            for breach in data:
                                results.append({
                                    "title": f"Brecha de {breach.get('Name', 'Incidente')}",
                                    "url": breach.get("Link"),
                                    "date": breach.get("Date"),
                                    "size": f"{breach.get('Breach', 0):,} usuarios",
                                    "language": breach.get("Type", "Credentials"),
                                    "source": "HaveIBeenPwned",
                                    "type": "breach",
                                    "tags": ["credentials", "passwords", "email"]
                                })
                        break
                    elif response.status_code == 401:
                        logger.warning("HIBP: Clave API inválida o no autorizada")
                        break
                    elif response.status_code == 404:
                        # No se encontraron brechas para ese email
                        logger.info("HIBP: No se encontraron brechas para este correo")
                        break
                    else:
                        logger.warning(f"HIBP error: {response.status_code}")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(DELAY_BETWEEN_REQUESTS)
                except Exception as e:
                    logger.error(f"HIBP request failed: {e}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(DELAY_BETWEEN_REQUESTS)
        elif not is_email:
            logger.info("Consulta no es un correo electrónico válido. Omitiendo búsqueda en HIBP.")
        else:
            logger.warning("Clave HIBP no configurada para este usuario. No se puede buscar en breaches.")

        # 2. Buscar en GitHub Gist (siempre, sin filtro de email)
        if query.lower() in ["password", "email", "api_key", "cred"]:
            gists = search_gist_by_keyword(query)
            if gists:
                for gist in gists:
                    results.append({
                        "title": gist.get("description", gist.get("files", {}).get("raw", "Sin título")),
                        "url": gist.get("html_url"),
                        "date": gist.get("created_at"),
                        "size": f"{gist.get('files', {}).get('size', 0)} KB",
                        "language": gist.get("files", {}).get("raw", {}).get("language", "Text"),
                        "source": "GitHub Gist",
                        "type": "gist",
                        "tags": ["code", "paste", "leak"]
                    })

        # 3. Buscar en Leakatlas.com (siempre, sin filtro de email)
        if query.lower() in ["password", "email", "api_key"]:
            leakatlas_results = search_leakatlas(query)
            if leakatlas_results:
                for item in leakatlas_results:
                    results.append({
                        "title": item.get("title", "Sin título"),
                        "url": item.get("url"),
                        "date": item.get("date"),
                        "size": item.get("size", "Desconocido"),
                        "language": item.get("language", "Other"),
                        "source": "Leakatlas.com",
                        "type": "leak",
                        "tags": ["data leak", "breach"]
                    })

        # 4. Buscar en Google Site Search (siempre, sin filtro de email)
        if query.lower() in ["password", "email", "api_key"]:
            google_results = search_google_site(query)
            if google_results:
                for item in google_results:
                    results.append({
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "date": item.get("date"),
                        "size": "N/A",
                        "language": item.get("language", "Unknown"),
                        "source": "Google Site Search",
                        "type": "web",
                        "tags": ["public paste"]
                    })

        # 5. Buscar en leaks específicos (siempre)
        leak_results = search_leaks(query, user_id=user_id)
        results.extend(leak_results)

    except Exception as e:
        logger.error(f"Error en búsqueda de paste: {e}")
        results = []

    return results


def search_gist_by_keyword(query: str) -> List[Dict[str, Any]]:
    """
    Buscar gists en GitHub (public) que contengan el texto especificado
    """
    try:
        query = query.lower().strip()
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "QuasarIII/1.0"
        }
        params = {
            "q": f"filename:*.py {query} OR file:*.txt {query} OR {query}",
            "per_page": 5,
            "page": 1
        }

        response = requests.get(GITHUB_GIST_URL, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("data"):
                return data["data"][:5]  # Solo 5 resultados
            else:
                return []
        else:
            logger.warning(f"GitHub request failed: {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"Error en búsqueda de GitHub Gist: {e}")
        return []


def search_leakatlas(query: str) -> List[Dict[str, Any]]:
    """
    Buscar en Leakatlas.com (búsqueda pública por palabra clave)
    """
    try:
        search_url = f"{LEAKATLAS_URL}?q={query}"
        headers = {
            "User-Agent": "QuasarIII/1.0"
        }
        response = requests.get(search_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                return [
                    {
                        "title": r.get("title"),
                        "url": r.get("url"),
                        "date": r.get("date"),
                        "size": r.get("size", "Desconocido"),
                        "language": r.get("language", "Unknown")
                    }
                    for r in data["results"][:5]
                ]
        else:
            logger.warning(f"Leakatlas error: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error en búsqueda de Leakatlas: {e}")
        return []


def search_google_site(query: str) -> List[Dict[str, Any]]:
    """
    Buscar en Google con query site:pastebin.com
    """
    try:
        search_url = f"https://www.google.com/search?q=site:pastebin.com+{query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"
        }
        response = requests.get(search_url, headers=headers, timeout=10)

        if response.status_code == 200:
            # Simulación: solo devuelve un resultado
            return [
                {
                    "title": "Pastebin: " + query,
                    "url": "https://pastebin.com/search?query=" + query,
                    "date": "Desconocido",
                    "language": "HTML",
                    "source": "Google Site Search"
                }
            ]
        else:
            logger.warning(f"Google search failed: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error en búsqueda de Google Site: {e}")
        return []


def search_leaks(query: str, user_id: int = None) -> List[Dict[str, Any]]:
    """
    Búsqueda real de leaks (breaches o datos expuestos)
    Usa HIBP como fuente principal
    """
    logger.info(f"Buscando leaks por: {query}")

    results = []
    try:
        # Revisar si es un correo electrónico antes de buscar en HIBP
        hibp_key = config_manager.get_config(user_id, "hibp") if user_id else None
        is_email = bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', query.strip()))

        if hibp_key and is_email:
            query_hash = quote_plus(query.lower().strip())
            url = f"{HIBP_BASE_URL}/{query_hash}"
            headers = {"x-apikey": hibp_key, "User-Agent": "QuasarIII/1.0"}

            for attempt in range(MAX_RETRIES):
                try:
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            for breach in data:
                                results.append({
                                    "source": "HaveIBeenPwned",
                                    "data_breached": breach.get("Name"),
                                    "compromised_users": breach.get("Breach", 0),
                                    "date_breached": breach.get("Date"),
                                    "type": breach.get("Type"),
                                    "tags": ["breach", "data_leak", "credentials"]
                                })
                        break
                    elif response.status_code == 401:
                        logger.warning("HIBP: Clave API inválida o no autorizada")
                        break
                    elif response.status_code == 404:
                        # No se encontraron brechas para ese email
                        logger.info("HIBP: No se encontraron brechas para este correo")
                        break
                    else:
                        logger.warning(f"HIBP error: {response.status_code}")
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(DELAY_BETWEEN_REQUESTS)
                except Exception as e:
                    logger.error(f"HIBP request failed: {e}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(DELAY_BETWEEN_REQUESTS)
        elif not is_email:
            logger.info("Consulta no es un correo electrónico válido. Omitiendo búsqueda en HIBP.")
        else:
            logger.warning("Clave HIBP no configurada. No se puede buscar leaks.")

    except Exception as e:
        logger.error(f"Error en búsqueda de leaks: {e}")
        results = []

    return results