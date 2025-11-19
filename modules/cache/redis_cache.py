# modules/cache/redis_cache.py
import redis
import json
import pickle
import logging

logger = logging.getLogger(__name__)


class DistributedCache:
    def __init__(self):
        self.redis_client = None
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
        except Exception as e:
            logger.warning(f"No se pudo conectar a Redis: {e}")
            self.redis_client = None

    def set(self, key: str, value: any, expire: int = 3600):
        """Establece valor en cache"""
        try:
            if self.redis_client:
                self.redis_client.setex(key, expire, pickle.dumps(value))
            else:
                # Fallback simple (en memoria)
                pass
        except Exception as e:
            logger.error(f"Error en cache SET: {e}")

    def get(self, key: str) -> any:
        """Obtiene valor del cache"""
        try:
            if self.redis_client:
                data = self.redis_client.get(key)
                if data:
                    return pickle.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error en cache GET: {e}")
            return None


# Cache global
cache = DistributedCache()