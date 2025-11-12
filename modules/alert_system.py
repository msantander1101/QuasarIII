import sqlite3

import streamlit as st
import asyncio
import schedule
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import queue

from app import config, db
from modules import proxy_manager


class AlertOrchestrator:
    """
    Monitorea targets continuamente y genera alertas cuando detecta cambios
    """

    def __init__(self, user_id: int, db_manager, config_manager, proxy_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager
        self.proxy = proxy_manager

        # Estado interno
        self.is_monitoring = False
        self.scheduler_thread = None
        self.alert_rules = self._load_rules()
        self.previous_results = {}  # Caché de resultados anteriores
        self.alert_queue = queue.Queue()  # Cola de alertas generadas

        # Sistema de notificaciones
        self.notifier = Notifier(user_id, db_manager, config_manager)

    def _load_rules(self) -> List[Dict]:
        """Carga reglas desde DB"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT *
                           FROM alert_rules
                           WHERE user_id = ?
                             AND is_active = 1
                           ''', (self.user_id,))
            rules = cursor.fetchall()
            conn.close()
            return [json.loads(rule[4]) for rule in rules]
        except:
            return []

    def create_rule(
            self,
            name: str,
            target: Dict,
            modules: List[str],
            check_interval: int,
            trigger_conditions: Optional[Dict] = None
    ) -> str:
        """Crea nueva regla de alerta"""
        rule_id = str(uuid.uuid4())

        rule = {
            "id": rule_id,
            "name": name,
            "target": target,
            "modules": modules,
            "check_interval": check_interval,
            "is_active": True,
            "notification_channels": ["ui"],
            "trigger_conditions": trigger_conditions or {"any_change": True},
            "created_at": datetime.now().isoformat(),
            "last_check": None
        }

        # Guardar en DB
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       INSERT INTO alert_rules (user_id, rule_id, rule_data)
                       VALUES (?, ?, ?)
                       ''', (self.user_id, rule_id, json.dumps(rule)))
        conn.commit()
        conn.close()

        self.alert_rules.append(rule)
        self._schedule_rule(rule)
        return rule_id

    def start_monitoring(self):
        """Inicia thread de monitoreo"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            st.success("✅ Sistema de alertas iniciado")

    def stop_monitoring(self):
        """Detiene monitoreo"""
        if self.is_monitoring:
            self.is_monitoring = False
            st.info("⏸️ Sistema de alertas detenido")

    def _run_scheduler(self):
        """Thread principal del scheduler"""
        while self.is_monitoring:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                st.error(f"Error en scheduler: {e}")
                time.sleep(5)

    def schedule_all_rules(self):
        """Programa todas las reglas activas"""
        for rule in self.alert_rules:
            if rule["is_active"]:
                self._schedule_rule(rule)

    def _schedule_rule(self, rule: Dict):
        """Programa una regla específica"""
        interval = rule["check_interval"]

        def job():
            asyncio.run(self._check_rule(rule))

        schedule.every(interval).minutes.do(job)

    async def _check_rule(self, rule: Dict):
        """Ejecuta check para una regla"""
        try:
            target_type = rule["target"]["type"]
            target_value = rule["target"]["value"]

            # Ejecutar módulos
            new_results = {}
            for module_name in rule["modules"]:
                if module_name == "socmint" and target_type == "username":
                    from modules.socmint import SOCMINTOrchestrator
                    orch = SOCMINTOrchestrator(self.user_id, self.db, self.config)
                    new_results[module_name] = await orch.search_sherlock(target_value)
                elif module_name == "breachdata" and target_type == "email":
                    from modules.breachdata import BreachDataOrchestrator
                    orch = BreachDataOrchestrator(self.user_id, self.db, self.config)
                    new_results[module_name] = await orch.check_hibp(target_value)

            # Detectar cambios
            rule_key = f"{rule['id']}:{target_value}"
            previous = self.previous_results.get(rule_key, {})
            changes = self._detect_changes(previous, new_results, rule["trigger_conditions"])

            if changes:
                alert = self._create_alert(rule, changes, new_results)
                await self._process_alert(alert, rule["notification_channels"])
                self.previous_results[rule_key] = new_results

            rule["last_check"] = datetime.now().isoformat()
            self._update_rule_in_db(rule)

        except Exception as e:
            st.error(f"Error checking rule {rule['name']}: {e}")

    def _detect_changes(self, previous: Dict, new: Dict, conditions: Dict) -> Dict:
        """Detecta cambios significativos"""
        changes = {}

        # Nuevos perfiles
        if conditions.get("new_profiles"):
            old = {p["url"] for p in previous.get("socmint", [])}
            new_profiles = {p["url"] for p in new.get("socmint", [])}
            added = new_profiles - old
            if added:
                changes["new_profiles"] = list(added)

        # Nuevos breaches
        if conditions.get("new_breaches"):
            old = {b["name"] for b in previous.get("breachdata", [])}
            new_breaches = {b["name"] for b in new.get("breachdata", [])}
            added = new_breaches - old
            if added:
                changes["new_breaches"] = list(added)

        return changes

    def _create_alert(self, rule: Dict, changes: Dict, results: Dict) -> Dict:
        """Crea objeto de alerta"""
        return {
            "id": str(uuid.uuid4()),
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "timestamp": datetime.now().isoformat(),
            "target": rule["target"],
            "changes": changes,
            "results": results,
            "priority": "HIGH" if changes.get("new_breaches") else "MEDIUM"
        }

    async def _process_alert(self, alert: Dict, channels: List[str]):
        """Procesa alerta según canales"""
        for channel in channels:
            if channel == "ui":
                self.alert_queue.put(alert)
                st.toast(f"🚨 Alerta: {alert['rule_name']}", icon="🔔")
            elif channel == "email":
                await self.notifier.send_email_alert(alert)
            elif channel == "webhook":
                await self.notifier.send_webhook_alert(alert)

        # Guardar en DB
        self.db.create_alert(
            self.user_id,
            alert["id"],
            alert["rule_name"],
            alert["priority"],
            json.dumps(alert)
        )

    def _update_rule_in_db(self, rule: Dict):
        """Actualiza regla en DB"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       UPDATE alert_rules
                       SET rule_data = ?
                       WHERE rule_id = ?
                       ''', (json.dumps(rule), rule["id"]))
        conn.commit()
        conn.close()

    def render_ui(self):
        """UI completa del sistema de alertas"""
        st.header("🚨 Alert System - Monitoreo Continuo")

        # Status
        col1, col2, col3 = st.columns(3)

        with col1:
            status = "🟢 Activo" if self.is_monitoring else "🔴 Detenido"
            st.metric("Estado del Sistema", status)

        with col2:
            st.metric("Reglas Activas", len([r for r in self.alert_rules if r["is_active"]]))

        with col3:
            st.metric("Alertas Pendientes", self.alert_queue.qsize())

        # Controles
        col1, col2 = st.columns(2)

        with col1:
            if not self.is_monitoring:
                if st.button("▶️ Iniciar Monitoreo", use_container_width=True):
                    self.schedule_all_rules()
                    self.start_monitoring()
                    st.rerun()

        with col2:
            if self.is_monitoring:
                if st.button("⏹️ Detener Monitoreo", use_container_width=True):
                    self.stop_monitoring()
                    st.rerun()

        st.markdown("---")

        # Crear nueva regla
        with st.expander("➕ Crear Nueva Regla de Alerta", expanded=True):
            self._render_rule_creator()

        # Lista de reglas
        st.subheader("📋 Reglas Configuradas")
        self._render_rules_list()

        # Alertas recientes
        st.subheader("🔔 Alertas Recientes")
        self._render_recent_alerts()

    def _render_rule_creator(self):
        """Formulario para crear regla"""
        col1, col2 = st.columns(2)

        with col1:
            rule_name = st.text_input("Nombre de la regla", placeholder="Monitor CEO Twitter")

            target_type = st.selectbox("Tipo de Target", ["username", "email"])
            target_value = st.text_input("Valor del Target", placeholder="juanperezceo")

        with col2:
            check_interval = st.slider("Intervalo de chequeo (minutos)", 15, 1440, 60)

            selected_modules = st.multiselect(
                "Módulos a monitorear",
                ["socmint", "breachdata"],
                default=["socmint"]
            )

        # Condiciones trigger
        st.markdown("**Condiciones de Trigger**")

        trigger_conditions = {}
        trigger_conditions["new_profiles"] = st.checkbox("Nuevos perfiles sociales")
        trigger_conditions["new_breaches"] = st.checkbox("Nuevos breaches")

        if st.button("Crear Regla", type="primary"):
            if not rule_name or not target_value:
                st.error("❌ Nombre y target son obligatorios")
                return

            self.create_rule(
                name=rule_name,
                target={"type": target_type, "value": target_value},
                modules=selected_modules,
                check_interval=check_interval,
                trigger_conditions=trigger_conditions
            )

            st.success(f"✅ Regla '{rule_name}' creada")
            st.rerun()

    def _render_rules_list(self):
        """Lista de reglas con acciones"""
        for rule in self.alert_rules:
            with st.expander(f"**{rule['name']}**", expanded=False):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.code(f"{rule['target']['type']} = {rule['target']['value']}")
                    st.caption(f"⏱️ Cada {rule['check_interval']} minutos")

                with col2:
                    if st.button("🗑️", key=f"del_rule_{rule['id']}"):
                        self._delete_rule(rule['id'])
                        st.rerun()

    def _render_recent_alerts(self):
        """Muestra alertas recientes"""
        alerts = self.db.get_recent_alerts(self.user_id, limit=10)

        if not alerts:
            st.info("Sin alertas recientes")
            return

        for alert in alerts:
            with st.expander(f"🚨 **{alert['priority']}** - {alert['rule_name']}", expanded=False):
                st.json(alert['changes'])

                if alert['priority'] == "HIGH":
                    st.error("⚠️ Prioridad Alta")

                if st.button("Marcar leída", key=f"read_alert_{alert['id']}"):
                    self.db.mark_alert_read(alert['id'])
                    st.rerun()


class Notifier:
    """Sistema de notificaciones multi-canal"""

    def __init__(self, user_id, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager

    async def send_email_alert(self, alert: Dict):
        """Envía alerta por email"""
        try:
            # Obtener configuración SMTP del usuario
            smtp_config = self._get_smtp_config()
            if not smtp_config:
                st.warning("⚠️ SMTP no configurado")
                return

            msg = MIMEMultipart()
            msg['From'] = smtp_config["from"]
            msg['To'] = smtp_config["to"]
            msg['Subject'] = f"🚨 OSINT Alert: {alert['rule_name']}"

            body = f"""
Alerta de OSINT Framework

Regla: {alert['rule_name']}
Prioridad: {alert['priority']}
Target: {alert['target']['type']} = {alert['target']['value']}

Cambios detectados:
{json.dumps(alert['changes'], indent=2)}

Timestamp: {alert['timestamp']}
            """

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(smtp_config["host"], smtp_config["port"])
            server.starttls()
            server.login(smtp_config["username"], smtp_config["password"])
            server.send_message(msg)
            server.quit()

            st.success("📧 Alerta enviada por email")

        except Exception as e:
            st.error(f"Error enviando email: {e}")

    async def send_webhook_alert(self, alert: Dict):
        """Envía alerta a webhook"""
        try:
            webhook_url = self.config.get_decrypted_key(self.db, self.user_id, "WebhookAlert")
            if not webhook_url:
                return

            async with aiohttp.ClientSession() as session:
                await session.post(webhook_url, json={
                    "source": "osint_framework",
                    "alert": alert,
                    "timestamp": datetime.now().isoformat()
                })

        except Exception as e:
            st.error(f"Error en webhook: {e}")

    def _get_smtp_config(self) -> Optional[Dict]:
        """Obtiene configuración SMTP del usuario"""
        try:
            encrypted = self.db.get_api_key(self.user_id, "SMTPConfig")
            if encrypted:
                decrypted = self.config.decrypt_api_key(encrypted)
                return json.loads(decrypted)
        except:
            pass
        return None


# Integración en app.py
def render_alert_system():
    orchestrator = AlertOrchestrator(
        st.session_state.user["id"],db,config,proxy_manager
    )
    orchestrator.render_ui()


# Añadir a navbar
if st.button("🚨 Alertas"):
    st.session_state.page = "alerts"
    st.rerun()