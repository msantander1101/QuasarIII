import logging
import requests
import time
from typing import Dict, List, Any
import subprocess
import tempfile
import json

logger = logging.getLogger(__name__)

class SocmintSearcher:
    """
    Sistema completo de SOCMINT con integración a APIs reales
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.timeout = 30

    def search_social_profiles(self, username: str, platforms: List[str] | None = None) -> Dict[str, Any]:
        from .people_search import PeopleSearcher
        try:
            searcher = PeopleSearcher()
            tool_results = searcher.search_social_profiles(username, platforms)
        except Exception as exc:
            logger.error(f"Error ejecutando herramientas OSINT: {exc}")
            return {
                "query": username,
                "platforms_searched": platforms or [],
                "timestamp": time.time(),
                "profiles_found": [],
                "total_profiles": 0,
                "errors": [f"Error ejecutando herramientas OSINT: {exc}"]
            }

        profiles_found: List[Dict[str, Any]] = []
        errors: List[str] = []

        if isinstance(tool_results, dict):
            for tool_name, data in tool_results.items():
                if isinstance(data, dict) and (data.get('error') or data.get('warning')):
                    msg = data.get('error') or data.get('warning')
                    errors.append(f"{tool_name}: {msg}")
                    continue
                if isinstance(data, dict) and data.get('raw_output'):
                    profiles_found.append({
                        'platform': tool_name,
                        'username': username,
                        'followers': 'N/A',
                        'posts': 'N/A',
                        'verified': False,
                        'url': None,
                        'source': tool_name,
                        'raw_output': data.get('raw_output')
                    })
                    continue
                if isinstance(data, dict):
                    for site, details in data.items():
                        try:
                            if not isinstance(details, dict):
                                errors.append(f"{tool_name}-{site}: formato no soportado")
                                continue
                            status = details.get('status') or details.get('state') or details.get('exists')
                            exists = False
                            if isinstance(status, str):
                                exists = status.lower() in ['claimed', 'found', 'exists', 'true', 'yes']
                            elif isinstance(status, bool):
                                exists = status
                            else:
                                exists = True
                            if not exists:
                                continue
                            profile = {
                                'platform': site,
                                'username': username,
                                'followers': details.get('followers', 'N/A'),
                                'posts': details.get('posts', details.get('videos', 'N/A')),
                                'verified': details.get('verified', False),
                                'url': details.get('url') or details.get('url_main'),
                                'source': tool_name
                            }
                            if platforms and site.lower() not in [p.lower() for p in platforms]:
                                continue
                            profiles_found.append(profile)
                        except Exception as ex:
                            errors.append(f"{tool_name}-{site}: parsing error {ex}")
                else:
                    errors.append(f"{tool_name}: formato de datos no soportado")

        return {
            "query": username,
            "platforms_searched": platforms or list(tool_results.keys()) if isinstance(tool_results, dict) else [],
            "timestamp": time.time(),
            "profiles_found": profiles_found,
            "total_profiles": len(profiles_found),
            "errors": errors
        }

# Instancia global
socmint_searcher = SocmintSearcher()

# Funciones públicas para exportar
def search_social_profiles(username: str, platforms: List[str] = None) -> Dict[str, Any]:
    return socmint_searcher.search_social_profiles(username, platforms)

def analyze_social_profile(username: str, platform: str = "all") -> Dict[str, Any]:
    return socmint_searcher.analyze_social_profile(username, platform)

def get_social_network_graph(usernames: List[str]) -> Dict[str, Any]:
    return socmint_searcher.get_social_network_graph(usernames)

def get_supported_platforms() -> List[str]:
    return socmint_searcher.get_supported_platforms()

def run_maigret(username):
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmpfile:
        cmd = ["maigret", username, "-J", "simple", "--json", tmpfile.name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": result.stderr}
        with open(tmpfile.name) as f:
            data = json.load(f)
        return data

def run_sherlock(username):
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmpfile:
        cmd = ["sherlock", username, "--json", tmpfile.name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": result.stderr}
        with open(tmpfile.name) as f:
            data = json.load(f)
        return data