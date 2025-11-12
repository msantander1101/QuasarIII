import asyncio
import sqlite3
import schedule
import streamlit as st
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import uuid
from datetime import datetime


@dataclass
class WorkflowStep:
    id: str
    action_type: str  # "search", "condition", "notification", "export", "delay"
    config: Dict[str, Any]
    next_step_id: Optional[str] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None


@dataclass
class Workflow:
    id: str
    name: str
    description: str
    trigger: Dict[str, Any]  # {"type": "manual|schedule|alert", ...}
    steps: List[WorkflowStep]
    is_active: bool
    created_at: str
    last_run: Optional[str] = None


class WorkflowEngine:
    """
    Ejecuta workflows secuenciales con condiciones y ramificaciones
    """

    def __init__(self, user_id: int, db_manager, config_manager, alert_orchestrator):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager
        self.alert_system = alert_orchestrator

        self.actions = {
            "search": self._action_search,
            "condition": self._action_condition,
            "notification": self._action_notification,
            "export": self._action_export,
            "delay": self._action_delay
        }

        self.workflows = self._load_workflows()

    def _load_workflows(self) -> List[Workflow]:
        """Carga workflows desde DB"""
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT *
                           FROM workflows
                           WHERE user_id = ?
                             AND is_active = 1
                           ''', (self.user_id,))
            workflows_data = cursor.fetchall()
            conn.close()

            workflows = []
            for wf in workflows_data:
                wf_dict = json.loads(wf[4])
                steps = [WorkflowStep(**step) for step in wf_dict.pop("steps", [])]
                workflows.append(Workflow(steps=steps, **wf_dict))

            return workflows
        except:
            return []

    def create_workflow(self, **kwargs) -> str:
        """Crea nuevo workflow y lo programa"""
        workflow_id = str(uuid.uuid4())

        workflow = Workflow(
            id=workflow_id,
            created_at=datetime.now().isoformat(),
            **kwargs
        )

        # Guardar en DB
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       INSERT INTO workflows (user_id, workflow_id, workflow_data)
                       VALUES (?, ?, ?)
                       ''', (self.user_id, workflow_id, json.dumps(asdict(workflow))))
        conn.commit()
        conn.close()

        self.workflows.append(workflow)

        # Si es schedule, programarlo
        if workflow.trigger["type"] == "schedule":
            self._schedule_workflow(workflow)

        return workflow_id

    def _schedule_workflow(self, workflow: Workflow):
        """Programa workflow tipo schedule"""
        interval = workflow.trigger.get("interval", 60)  # minutos

        def job():
            asyncio.run(self.execute_workflow(workflow, {}))

        schedule.every(interval).minutes.do(job)

    async def execute_workflow(self, workflow: Workflow, initial_context: Dict) -> Dict:
        """Ejecuta workflow paso a paso"""
        context = {
            "workflow_id": workflow.id,
            "execution_id": str(uuid.uuid4()),
            "start_time": datetime.now().isoformat(),
            **initial_context
        }

        current_step_id = "start"
        executed_steps = []

        try:
            while current_step_id:
                step = self._get_step_by_id(workflow, current_step_id)
                if not step:
                    break

                result = await self._execute_step(step, context)
                executed_steps.append({
                    "step_id": current_step_id,
                    "action_type": step.action_type,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })

                # Ramificar según resultado
                if result.get("success", True):
                    current_step_id = step.on_success or step.next_step_id
                else:
                    current_step_id = step.on_failure

            context["status"] = "completed"

        except Exception as e:
            context["status"] = "failed"
            context["error"] = str(e)

        context["executed_steps"] = executed_steps
        context["end_time"] = datetime.now().isoformat()

        # Guardar ejecución
        self.db.save_workflow_execution(workflow.id, context["execution_id"], json.dumps(context))

        return context

    async def _execute_step(self, step: WorkflowStep, context: Dict) -> Dict:
        """Ejecuta un paso individual"""
        try:
            action_func = self.actions.get(step.action_type)
            if not action_func:
                return {"success": False, "error": f"Acción desconocida: {step.action_type}"}

            return await action_func(step.config, context)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _action_search(self, config: Dict, context: Dict) -> Dict:
        """Acción: ejecutar búsqueda OSINT"""
        target_type = config.get("target_type")
        target_value = config.get("target_value")

        # Resolver desde contexto si es variable
        if target_value.startswith("$"):
            target_value = context.get(target_value[1:], "")

        results = {}
        for module_name in config.get("modules", []):
            if module_name == "socmint":
                from modules.socmint import SOCMINTOrchestrator
                orch = SOCMINTOrchestrator(self.user_id, self.db, self.config)
                results[module_name] = await orch.search_sherlock(target_value)

        context["last_search"] = results
        return {"success": True, "data": results}

    async def _action_condition(self, config: Dict, context: Dict) -> Dict:
        """Acción: evaluar condición"""
        condition_type = config.get("type")

        if condition_type == "threshold":
            threshold = config.get("threshold", 0)
            actual = len(context.get("last_search", {}).get("profiles", []))
            return {"success": actual >= threshold, "data": {"actual": actual}}

        return {"success": False, "error": "Condición desconocida"}

    async def _action_notification(self, config: Dict, context: Dict) -> Dict:
        """Acción: enviar notificación"""
        message = config.get("message", "Alert from workflow")
        await self.alert_system.notifier.send_email_alert({
            "rule_name": "Workflow",
            "priority": "MEDIUM",
            "target": context.get("target", {}),
            "changes": {"message": message}
        })
        return {"success": True}

    async def _action_export(self, config: Dict, context: Dict) -> Dict:
        """Acción: exportar resultados"""
        # Implementar exportación
        return {"success": True}

    async def _action_delay(self, config: Dict, context: Dict) -> Dict:
        """Acción: esperar"""
        await asyncio.sleep(config.get("seconds", 5))
        return {"success": True}

    def _get_step_by_id(self, workflow: Workflow, step_id: str) -> Optional[WorkflowStep]:
        """Obtiene paso por ID"""
        for step in workflow.steps:
            if step.id == step_id:
                return step
        return None

    def trigger_from_alert(self, alert: Dict):
        """Dispara workflows basados en una alerta"""
        for workflow in self.workflows:
            if workflow.trigger.get("type") == "alert" and workflow.trigger.get("rule_id") == alert["rule_id"]:
                # Ejecutar en background
                context = {
                    "trigger": "alert",
                    "alert": alert,
                    "target": alert["target"]
                }
                asyncio.create_task(self.execute_workflow(workflow, context))

    def render_ui(self):
        """UI completa del Workflow Builder"""
        st.header("🔄 Workflow Engine - Automatización")

        # Resumen
        col1, col2, col3 = st.columns(3)
        col1.metric("Workflows", len(self.workflows))
        col2.metric("Ejecuciones Hoy", self.db.get_workflow_execution_count(self.user_id))
        col3.metric("Tasa Éxito", "95%")  # Placeholder

        # Crear workflow
        with st.expander("➕ Crear Workflow", expanded=True):
            workflow_name = st.text_input("Nombre del Workflow")
            trigger_type = st.selectbox("Trigger", ["manual", "schedule", "alert"])

            if trigger_type == "alert":
                rule_id = st.text_input("Rule ID (para alert trigger)")

            steps_json = st.text_area("Steps (JSON)", '[{"id": "step1", "action_type": "search", "config": {}}]')

            if st.button("Crear", type="primary"):
                try:
                    steps = json.loads(steps_json)
                    workflow_id = self.create_workflow(
                        name=workflow_name,
                        description="",
                        trigger={"type": trigger_type, "rule_id": rule_id} if trigger_type == "alert" else {
                            "type": trigger_type},
                        steps=[WorkflowStep(**step) for step in steps],
                        is_active=True
                    )
                    st.success(f"✅ Workflow creado: {workflow_id}")
                except Exception as e:
                    st.error(f"Error: {e}")

        # Lista workflows
        st.subheader("📋 Workflows")
        for wf in self.workflows:
            with st.expander(f"{wf.name} ({wf.trigger['type']})"):
                if st.button("▶️ Ejecutar", key=f"run_{wf.id}"):
                    asyncio.create_task(self.execute_workflow(wf, {}))