# modules/cache/search_cache.py
import time
import hashlib
import pickle
import logging
import threading
from typing import Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CachedResult:
    """Clase para almacenar resultados en caché"""
    key: str
    data: Any
    timestamp: float
    ttl: int = 3600  # 1 hora por defecto


class SearchCache:
    """Sistema de caché para resultados de búsqueda"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.cache = {}
        self.access_times = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.lock = threading.RLock()

    def get_key(self, query: str, sources: list = None) -> str:
        """Generar clave única para búsqueda"""
        combined = f"{query}|{'|'.join(sorted(sources)) if sources else 'all'}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get(self, key: str) -> Any:
        """Obtener resultado del cache"""
        with self.lock:
            if key in self.cache:
                cached_result = self.cache[key]
                if time.time() - cached_result.timestamp < cached_result.ttl:
                    self.access_times[key] = time.time()
                    return cached_result.data
                else:
                    self._remove_key(key)
            return None

    def set(self, key: str, data: Any, ttl: int = None) -> bool:
        """Guardar resultado en cache"""
        with self.lock:
            try:
                if ttl is None:
                    ttl = self.default_ttl

                cached_result = CachedResult(
                    key=key,
                    data=data,
                    timestamp=time.time(),
                    ttl=ttl
                )

                if len(self.cache) >= self.max_size:
                    self._cleanup_lru()

                self.cache[key] = cached_result
                self.access_times[key] = time.time()

                return True

            except Exception as e:
                logger.error(f"Error al guardar en cache: {e}")
                return False

    def invalidate(self, key: str) -> bool:
        """Invalidar entrada de cache"""
        with self.lock:
            return self._remove_key(key)

    def cleanup_expired(self) -> int:
        """Limpiar entradas expiradas"""
        with self.lock:
            expired_count = 0
            current_time = time.time()
            expired_keys = []

            for key, cached_result in self.cache.items():
                if current_time - cached_result.timestamp >= cached_result.ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                self._remove_key(key)
                expired_count += 1

            return expired_count

    def _remove_key(self, key: str) -> bool:
        """Eliminar clave del cache"""
        if key in self.cache:
            del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
            return True
        return False

    def _cleanup_lru(self):
        """Limpiar entradas menos usadas"""
        if len(self.cache) <= self.max_size:
            return

        sorted_keys = sorted(self.access_times.items(), key=lambda x: x[1])
        keys_to_remove = []

        for key, _ in sorted_keys[:10]:
            keys_to_remove.append(key)

        for key in keys_to_remove:
            self._remove_key(key)


# Instancia única del cache
search_cache = SearchCache()


# Funciones de acceso rápido
def cache_get(key: str) -> Any:
    """Obtener de cache"""
    return search_cache.get(key)


def cache_set(key: str, data: Any, ttl: int = None) -> bool:
    """Guardar en cache"""
    return search_cache.set(key, data, ttl)


def cache_invalidate(key: str) -> bool:
    """Invalidar cache"""
    return search_cache.invalidate(key)