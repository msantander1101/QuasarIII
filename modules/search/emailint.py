# modules/search/emailint.py

"""
Búsqueda real de información de email con integración a APIs reales (HIBP + SkyMem + GHunt)
"""
import hashlib
import logging
import subprocess
import tempfile

import requests
import time
import json
import re
from typing import Dict, List, Any
from urllib.parse import quote_plus
from core.config_manager import config_manager

logger = logging.getLogger(__name__)

# Importa GHunt directamente
try:
    from ghunt import GHunt
    GHUNT_AVAILABLE = True
except ImportError:
    GHUNT_AVAILABLE = False
    logger.warning("GHunt no está disponible. Las búsquedas de GHunt serán omitidas.")


class EmailSearcher:
    """
    Sistema de búsqueda real de información de email con integración a APIs reales
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.timeout = 30

        # Inicializar GHunt si está disponible
        if GHUNT_AVAILABLE:
            self.ghunt = GHunt()
        else:
            self.ghunt = None

    def get_user_email_sources(self, user_id: int) -> Dict[str, Dict]:
        """
        Obtener fuentes de búsqueda de email disponibles para el usuario
        """
        sources = {}

        api_dependent_sources = {
            'hibp': 'hibp',
            'skymem': 'skymem',
            'hunter': 'hunter',
            'gmail_searcher': 'gmail_searcher'
        }

        no_api_sources = {
            'email_search': 'email_search',
            'email_verification': 'email_verification'
        }

        for key, source_name in api_dependent_sources.items():
            api_key = config_manager.get_config(user_id, key)
            sources[source_name] = {
                'enabled': bool(api_key),
                'requires_api': True,
                'api_key': api_key,
                'config_key': key
            }

        for source_name, source_type in no_api_sources.items():
            sources[source_name] = {
                'enabled': True,
                'requires_api': False,
                'config_key': source_name
            }

        # Registrar GHunt como fuente opcional
        sources['ghunt'] = {
            'enabled': GHUNT_AVAILABLE,
            'requires_api': False,
            'source_type': 'ghunt'
        }

        return sources

    def search_ghunt(self, email: str) -> Dict[str, Any]:
        """
        Búsqueda de email usando GHunt de manera segura
        """
        if not self.ghunt:
            return {"success": False, "error": "GHunt no está disponible"}

        try:
            result = self.ghunt.email_search(email)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Mantener métodos existentes ---
    def check_email_breach(self, email: str, user_id: int) -> Dict[str, Any]:
        # Tu implementación existente de HIBP, SkyMem, Hunter
        ...

    def search_email_paste_accounts(self, email: str, user_id: int) -> Dict[str, Any]:
        ...

    def verify_email_format(self, email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def verify_email_deliverability(self, email: str, user_id: int) -> Dict[str, Any]:
        ...

    def search_email_info(self, email: str, user_id: int, services: List[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        results = {
            "email": email,
            "timestamp": time.time(),
            "breeches_info": {},
            "paste_info": {},
            "verification_info": {},
            "search_time": 0,
            "errors": []
        }

        # Brechas
        breach_result = self.check_email_breach(email, user_id)
        results["breeches_info"] = breach_result if isinstance(breach_result, dict) else {"error": str(breach_result)}

        # Paste accounts
        paste_result = self.search_email_paste_accounts(email, user_id)
        results["paste_info"] = paste_result if isinstance(paste_result, dict) else {"error": str(paste_result)}

        # Verificación
        verify_result = self.verify_email_deliverability(email, user_id)
        results["verification_info"] = verify_result if isinstance(verify_result, dict) else {"error": str(verify_result)}

        # GHunt
        ghunt_result = self.search_ghunt(email)
        if ghunt_result.get("success"):
            results["breeches_info"]["ghunt"] = ghunt_result["data"]
        else:
            results["errors"].append({"ghunt": ghunt_result.get("error")})

        results["search_time"] = time.time() - start_time
        return results


# Instancia global
email_searcher = EmailSearcher()

# Funciones públicas
check_email_breach = email_searcher.check_email_breach
search_email_paste_accounts = email_searcher.search_email_paste_accounts
verify_email_format = email_searcher.verify_email_format
verify_email_deliverability = email_searcher.verify_email_deliverability
search_email_info = email_searcher.search_email_info
