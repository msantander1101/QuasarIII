# modules/utils/rate_limiter.py
import time
from collections import defaultdict
import threading


class RateLimiter:
    def __init__(self, max_calls: int = 100, window: int = 60):
        self.max_calls = max_calls
        self.window = window
        self.calls = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, key: str = "default") -> bool:
        """Verifica si está permitida una llamada"""
        now = time.time()
        with self.lock:
            # Limpiar llamadas antiguas
            self.calls[key] = [call for call in self.calls[key] if now - call < self.window]

            # Permitir si no se ha excedido límite
            if len(self.calls[key]) < self.max_calls:
                self.calls[key].append(now)
                return True
            return False


# Global rate limiter
rate_limiter = RateLimiter(max_calls=10, window=10)  # 10 llamadas por 10 segundos