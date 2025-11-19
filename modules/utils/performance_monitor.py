# modules/utils/performance_monitor.py
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    @staticmethod
    def monitor_execution(func):
        """Decorador para monitoreo de rendimiento"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"{func.__name__} ejecutado en {execution_time:.2f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{func.__name__} falló después de {execution_time:.2f}s: {e}")
                raise
        return wrapper

# Uso en los módulos:
@PerformanceMonitor.monitor_execution
def optimized_search_function():
    # Tu lógica aquí
    pass