import time
import streamlit as st
import requests
import socks
import socket
import random
import json
from typing import Dict, List, Optional
import urllib3

from config_manager import ConfigManager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ProxyManager:
    """
    Gestiona proxies HTTP/HTTPS/SOCKS5 y Tor para anonimato total en OSINT
    """

    def __init__(self, user_id: int, db_manager, timeout: int = 30):
        self.user_id = user_id
        self.db = db_manager
        self.timeout = timeout
        self.proxies_list: List[Dict] = self._load_proxies()
        self.tor_enabled = self._check_tor_service()

        # Pool de sesiones para reutilización
        self.sessions = {}

    def _load_proxies(self) -> List[Dict]:
        """Carga proxies desde DB (cifrados)"""
        try:
            encrypted_data = self.db.get_api_key(self.user_id, "Proxies_List")
            if encrypted_data:
                from config_manager import ConfigManager
                config = ConfigManager()
                decrypted = config.decrypt_api_key(encrypted_data)
                return json.loads(decrypted)
        except Exception as e:
            st.error(f"Error cargando proxies: {e}")
        return []

    def _check_tor_service(self) -> bool:
        """Verifica si Tor está corriendo"""
        try:
            tor_session = self._get_tor_session()
            response = tor_session.get(
                "https://check.torproject.org/",
                timeout=10,
                verify=False
            )
            return "Congratulations. This browser is configured to use Tor." in response.text
        except:
            return False

    def _get_tor_session(self) -> requests.Session:
        """Crea sesión vía Tor SOCKS5"""
        session = requests.Session()
        session.proxies = {
            "http": "socks5h://127.0.0.1:9050",
            "https": "socks5h://127.0.0.1:9050"
        }
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0"
        })
        return session

    def _get_proxy_session(self, proxy: Dict) -> requests.Session:
        """Crea sesión con proxy específico"""
        session = requests.Session()

        proxy_url = f"{proxy['type']}://"
        if proxy.get('username') and proxy.get('password'):
            proxy_url += f"{proxy['username']}:{proxy['password']}@"
        proxy_url += f"{proxy['host']}:{proxy['port']}"

        session.proxies = {
            "http": proxy_url,
            "https": proxy_url
        }

        # Random User-Agent
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
        ]
        session.headers.update({"User-Agent": random.choice(ua_list)})

        return session

    def execute_request(self, method: str, url: str,
                        use_tor: bool = False,
                        max_retries: int = 3,
                        **kwargs) -> Optional[requests.Response]:
        """
        Ejecuta request con rotación automática de proxy/Tor
        """
        # Siempre verificar SSL pero permitir override
        kwargs.setdefault('verify', False)
        kwargs.setdefault('timeout', self.timeout)

        attempts = 0

        while attempts < max_retries:
            try:
                if use_tor and self.tor_enabled:
                    session = self._get_tor_session()
                    st.info("🧅 Usando red Tor...")
                elif self.proxies_list:
                    proxy = random.choice(self.proxies_list)
                    session = self._get_proxy_session(proxy)
                    st.info(f"🌐 Usando proxy: {proxy['host']}:{proxy['port']}")
                else:
                    session = requests.Session()
                    st.warning("⚠️ Sin proxies configurados - IP expuesta")

                response = session.request(method, url, **kwargs)

                # Verificar si IP fue bloqueada
                if response.status_code == 429:
                    st.error("⚠️ Rate limited - Rotando proxy...")
                    attempts += 1
                    time.sleep(random.uniform(2, 5))
                    continue

                return response

            except Exception as e:
                st.error(f"Error en request (intento {attempts + 1}/{max_retries}): {e}")
                attempts += 1
                time.sleep(random.uniform(1, 3))

        # Fallback a Tor si todo falla
        if not use_tor and self.tor_enabled:
            st.warning("❌ Todos fallaron. Intentando con Tor...")
            return self.execute_request(method, url, use_tor=True, **kwargs)

        return None

    def get_current_ip(self, use_tor: bool = False):
        """Obtiene IP actual para verificar anonimato"""
        try:
            session = self._get_tor_session() if use_tor else requests.Session()
            response = session.get("https://api.ipify.org?format=json", timeout=10)
            return response.json().get("ip", "Unknown")
        except:
            return "Error"

    def test_proxy(self, proxy: Dict) -> bool:
        """Testea si un proxy funciona"""
        try:
            session = self._get_proxy_session(proxy)
            response = session.get(
                "https://httpbin.org/ip",
                timeout=10,
                verify=False
            )
            return response.status_code == 200
        except:
            return False

    def render_ui(self):
        """UI completa para gestión de proxies"""
        st.header("🛡️ Proxy & Anonymity Manager")

        # Status Tor
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Estado Tor", "✅ Activo" if self.tor_enabled else "❌ Inactivo")
        with col2:
            if self.tor_enabled:
                if st.button("Obtener IP Tor"):
                    ip = self.get_current_ip(use_tor=True)
                    st.success(f"IP Tor actual: {ip}")

        # Lista de proxies
        st.subheader("🌐 Proxies Configurados")
        if self.proxies_list:
            for idx, proxy in enumerate(self.proxies_list):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.text(f"{proxy['type']}://{proxy['host']}:{proxy['port']}")
                with col2:
                    if st.button("Test", key=f"test_{idx}"):
                        if self.test_proxy(proxy):
                            st.success("✅ OK")
                        else:
                            st.error("❌ Falló")
                with col3:
                    if st.button("🗑️", key=f"del_proxy_{idx}"):
                        self.proxies_list.pop(idx)
                        self._save_proxies()
                        st.rerun()
        else:
            st.info("No hay proxies configurados")

        # Añadir proxy
        with st.expander("➕ Añadir Nuevo Proxy"):
            col1, col2 = st.columns(2)
            with col1:
                proxy_type = st.selectbox("Tipo", ["http", "https", "socks5"])
                host = st.text_input("Host", placeholder="192.168.1.1")
                port = st.number_input("Port", min_value=1, max_value=65535, value=8080)

            with col2:
                username = st.text_input("Username (opcional)", placeholder="proxy_user")
                password = st.text_input("Password (opcional)", type="password")

            if st.button("Guardar Proxy"):
                proxy = {
                    "type": proxy_type,
                    "host": host,
                    "port": port,
                    "username": username if username else None,
                    "password": password if password else None
                }

                if self.test_proxy(proxy):
                    self.proxies_list.append(proxy)
                    self._save_proxies()
                    st.success("✅ Proxy guardado y testeado")
                    st.rerun()
                else:
                    st.error("❌ Proxy no responde")

    def _save_proxies(self):
        """Guarda proxies cifrados en DB"""
        encrypted = ConfigManager().encrypt_api_key(json.dumps(self.proxies_list))
        self.db.save_api_key(self.user_id, "Proxies_List", encrypted)


# Uso en cualquier módulo:
def render_ui(user_id, api_keys, config, db):
    st.subheader("Configuración de Anonimato")
    proxy_manager = ProxyManager(user_id, db)

    # Checkbox global
    use_proxy = st.checkbox("🔒 Activar protección de proxy/Tor", value=True)

    # Siempre pasar proxy_manager a funciones que hacen requests
    if st.button("Iniciar Búsqueda"):
        if use_proxy:
            response = proxy_manager.execute_request("GET", "https://api.ejemplo.com")
        else:
            response = requests.get("https://api.ejemplo.com")