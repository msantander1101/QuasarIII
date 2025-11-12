import time
from datetime import datetime
from typing import Dict
import streamlit as st
from collections import deque
import json


class ProgressTracker:
    """
    Sistema de tracking en tiempo real con WebSockets (simulado)
    """

    def __init__(self, max_size=1000):
        self.history = deque(maxlen=max_size)
        self.current_speed = 0
        self.last_update = time.time()
        self.processed_in_last_second = 0

    def update(self, target_id: str, status: str, module: str = None):
        """Actualiza progreso"""
        now = time.time()
        self.processed_in_last_second += 1

        if now - self.last_update >= 1:
            self.current_speed = self.processed_in_last_second
            self.processed_in_last_second = 0
            self.last_update = now

        self.history.append({
            "target_id": target_id,
            "status": status,
            "module": module,
            "timestamp": datetime.now().isoformat()
        })

    def get_dashboard_stats(self) -> Dict:
        """Estadísticas para dashboard"""
        last_100 = list(self.history)[-100:]

        return {
            "total_processed": len(self.history),
            "current_speed": self.current_speed,
            "success_rate": sum(1 for x in last_100 if x["status"] == "success") / len(last_100) if last_100 else 0,
            "active_modules": len(set(x["module"] for x in last_100 if x["module"]))
        }