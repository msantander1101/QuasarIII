import time
from collections import deque, defaultdict


class PerformanceTracker:
    """
    Real-time performance monitoring for OSINT operations
    """

    def __init__(self, max_history=1000):
        self.search_times = deque(maxlen=max_history)
        self.module_performance = defaultdict(lambda: deque(maxlen=100))
        self.rate_limit_hits = 0
        self.error_count = 0

    def record_search(self, modules: list, duration: float, success: bool):
        """Registra una búsqueda completa"""
        self.search_times.append({
            "timestamp": time.time(),
            "duration": duration,
            "modules": modules,
            "success": success
        })

        if not success:
            self.error_count += 1

    def record_module_call(self, module_name: str, duration: float, success: bool):
        """Registra llamada individual de módulo"""
        self.module_performance[module_name].append({
            "timestamp": time.time(),
            "duration": duration,
            "success": success
        })

    def get_current_metrics(self) -> dict:
        """Obtiene métricas instantáneas"""
        if not self.search_times:
            return {
                "avg_duration": 0,
                "success_rate": 100,
                "rate_limit_hits": self.rate_limit_hits,
                "errors_per_minute": 0
            }

        recent = list(self.search_times)[-30:]  # Últimas 30 búsquedas
        avg_duration = sum(s["duration"] for s in recent) / len(recent)
        success_rate = sum(s["success"] for s in recent) / len(recent) * 100

        return {
            "avg_duration": avg_duration,
            "success_rate": success_rate,
            "rate_limit_hits": self.rate_limit_hits,
            "errors_per_minute": self.error_count / max((time.time() - self.search_times[0]["timestamp"]) / 60, 1)
        }

    def get_module_stats(self) -> dict:
        """Estadísticas por módulo"""
        stats = {}
        for module_name, calls in self.module_performance.items():
            if calls:
                avg_time = sum(c["duration"] for c in calls) / len(calls)
                success_rate = sum(c["success"] for c in calls) / len(calls) * 100
                stats[module_name] = {
                    "avg_time": avg_time,
                    "success_rate": success_rate,
                    "total_calls": len(calls)
                }
        return stats


# Instancia global
performance_tracker = PerformanceTracker()


# Decorador para track automático
def track_performance(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        success = True

        try:
            result = func(*args, **kwargs)
        except Exception as e:
            success = False
            PerformanceTracker.rate_limit_hits += 1
            raise e
        finally:
            duration = time.time() - start_time
            module_name = func.__module__.split(".")[-1]
            performance_tracker.record_module_call(module_name, duration, success)

        return result

    return wrapper