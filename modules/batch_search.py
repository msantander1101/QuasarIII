import streamlit as st
import pandas as pd
import asyncio
import aiofiles
import aiohttp
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue
import time

from pandas import io

from app import db, config


@dataclass
class BatchTarget:
    """Representa un target individual del batch"""
    id: str
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    domain: Optional[str] = None
    metadata: Optional[Dict] = None


class BatchSearchOrchestrator:
    """
    Procesa múltiples targets con paralelismo inteligente
    """

    def __init__(self, user_id: int, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager

        # Configuración de paralelismo
        self.max_workers = 10  # Máximo concurrente
        self.rate_limiter = AsyncRateLimiter(requests_per_second=5)

        # Estado del batch
        self.is_running = False
        self.progress_queue = queue.Queue()
        self.results_cache = {}

        # Métricas
        self.metrics = {
            "total_targets": 0,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "start_time": None,
            "end_time": None
        }

    async def process_target(self, target: BatchTarget, modules: List[str]) -> Dict:
        """
        Procesa un target individual con todos los módulos seleccionados
        """
        target_results = {
            "id": target.id,
            "target": {
                "username": target.username,
                "email": target.email,
                "phone": target.phone,
                "domain": target.domain
            },
            "modules": {},
            "timestamp": datetime.now().isoformat(),
            "status": "processing"
        }

        try:
            # Ejecutar módulos en paralelo para este target
            module_tasks = []

            for module_name in modules:
                if hasattr(target, module_name) and getattr(target, module_name):
                    module = __import__(f"modules.{module_name}", fromlist=[module_name])
                    orchestrator = getattr(module, f"{module_name.capitalize()}Orchestrator")(
                        self.user_id, self.db, self.config
                    )

                    # Usar getattr para llamar search_all o método específico
                    if hasattr(orchestrator, "search_all"):
                        task = orchestrator.search_all(getattr(target, module_name))
                    else:
                        task = self._fallback_module_search(orchestrator, module_name, target)

                    module_tasks.append((module_name, task))

            # Esperar todas las tareas
            for module_name, task in module_tasks:
                try:
                    result = await asyncio.wait_for(task, timeout=60)
                    target_results["modules"][module_name] = result
                    self.rate_limiter.acquire()
                except asyncio.TimeoutError:
                    target_results["modules"][module_name] = {"error": "timeout"}
                except Exception as e:
                    target_results["modules"][module_name] = {"error": str(e)}

            target_results["status"] = "completed"
            self.metrics["successful"] += 1

        except Exception as e:
            target_results["status"] = "failed"
            target_results["error"] = str(e)
            self.metrics["failed"] += 1

        self.metrics["processed"] += 1
        self.progress_queue.put(target_results)

        return target_results

    async def _fallback_module_search(self, orchestrator, module_name: str, target: BatchTarget):
        """Método fallback para módulos sin search_all"""
        # Implementar métodos específicos si no hay search_all
        if module_name == "phoneint" and target.phone:
            return await orchestrator.search_phone(target.phone)
        elif module_name == "emailint" and target.email:
            return await orchestrator.validate_format(target.email)
        return {}

    async def process_batch(self, targets: List[BatchTarget], modules: List[str]) -> List[Dict]:
        """
        Procesa todos los targets con límite de concurrencia
        """
        self.metrics["total_targets"] = len(targets)
        self.metrics["start_time"] = datetime.now()
        self.metrics["processed"] = 0
        self.metrics["successful"] = 0
        self.metrics["failed"] = 0

        semaphore = asyncio.Semaphore(self.max_workers)

        async def sem_task(target):
            async with semaphore:
                return await self.process_target(target, modules)

        tasks = [sem_task(target) for target in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        self.metrics["end_time"] = datetime.now()

        # Filtrar excepciones
        return [r for r in results if not isinstance(r, Exception)]

    def load_targets_from_csv(self, file) -> List[BatchTarget]:
        """
        Carga targets desde CSV con validación
        """
        df = pd.read_csv(file)
        targets = []

        required_columns = ["username", "email", "phone", "domain"]
        available_cols = [col for col in required_columns if col in df.columns]

        if not available_cols:
            st.error("CSV debe contener al menos una columna: username, email, phone o domain")
            return []

        for idx, row in df.iterrows():
            # Validar y crear target
            target_data = {col: row[col] for col in available_cols if pd.notna(row[col])}

            if not any(target_data.values()):
                continue

            targets.append(BatchTarget(
                id=str(uuid.uuid4()),
                **target_data,
                metadata={"row": idx, "source_file": file.name}
            ))

        return targets

    def render_ui(self):
        """UI completa de Batch Search"""
        st.header("📊 Batch Search - Procesamiento Masivo")

        # Sección 1: Carga de targets
        st.subheader("1️⃣ Cargar Targets")

        col1, col2 = st.columns(2)

        with col1:
            input_method = st.radio(
                "Método de entrada",
                ["CSV/Excel", "Pegar lista", "Importar desde clipboard"]
            )

        targets = []

        if input_method == "CSV/Excel":
            uploaded_file = st.file_uploader(
                "Subir archivo (CSV, XLSX, JSON)",
                type=["csv", "xlsx", "json"],
                help="Archivo con columnas: username, email, phone, domain"
            )

            if uploaded_file:
                if uploaded_file.name.endswith('.csv'):
                    targets = self.load_targets_from_csv(uploaded_file)
                elif uploaded_file.name.endswith('.xlsx'):
                    # Implementar para Excel
                    pass
                elif uploaded_file.name.endswith('.json'):
                    # Implementar para JSON
                    pass

        elif input_method == "Pegar lista":
            text_input = st.text_area(
                "Pega una lista (uno por línea)",
                placeholder="user1@example.com\nuser2@example.com\n@twitteruser"
            )

            if st.button("Procesar lista"):
                lines = text_input.strip().split('\n')
                for i, line in enumerate(lines):
                    if "@" in line and "." in line:  # Email
                        targets.append(BatchTarget(
                            id=str(uuid.uuid4()),
                            email=line.strip()
                        ))
                    elif line.startswith('@'):  # Username
                        targets.append(BatchTarget(
                            id=str(uuid.uuid4()),
                            username=line.strip('@')
                        ))

        st.info(f"📋 **Total targets cargados**: {len(targets)}")

        # Sección 2: Configuración de módulos
        st.subheader("2️⃣ Seleccionar Módulos")

        available_modules = {
            "socmint": "📱 Redes Sociales",
            "breachdata": "🔓 Breaches",
            "emailint": "📧 Email Intel",
            "domainint": "🌐 Domains",
            "phoneint": "📞 Phone Intel"
        }

        selected_modules = []
        cols = st.columns(len(available_modules))

        for idx, (module_key, module_label) in enumerate(available_modules.items()):
            with cols[idx]:
                if st.checkbox(module_label, value=True, key=f"batch_module_{module_key}"):
                    selected_modules.append(module_key)

        # Configuración avanzada
        with st.expander("⚙️ Configuración Avanzada"):
            col1, col2 = st.columns(2)

            with col1:
                self.max_workers = st.slider(
                    "Workers concurrentes",
                    min_value=1,
                    max_value=20,
                    value=10,
                    help="Número de búsquedas paralelas"
                )

            with col2:
                timeout_per_target = st.slider(
                    "Timeout por target (segundos)",
                    min_value=30,
                    max_value=300,
                    value=60
                )

        # Sección 3: Ejecución
        if len(targets) > 0 and len(selected_modules) > 0:
            st.subheader("3️⃣ Ejecutar Búsqueda Masiva")

            # Preview de primeros 5 targets
            with st.expander("👁️ Vista previa de targets"):
                preview_df = pd.DataFrame([t.__dict__ for t in targets[:5]])
                st.dataframe(preview_df, use_container_width=True)

            # Botón de ejecución con confirmación
            if st.button("🚀 INICIAR BATCH SEARCH", type="primary", use_container_width=True):
                # Confirmación para batches grandes
                if len(targets) > 100:
                    st.warning(
                        f"⚠️ Estás a punto de procesar {len(targets)} targets. Esto puede tardar varios minutos.")
                    if not st.checkbox("Confirmar batch grande"):
                        return

                # Inicializar estado
                st.session_state.batch_results = []
                st.session_state.batch_running = True

                # UI de progreso
                progress_container = st.empty()
                metrics_container = st.empty()
                results_container = st.empty()

                # Ejecutar en thread separado para no bloquear UI
                def run_batch():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(
                        self.process_batch(targets, selected_modules)
                    )
                    st.session_state.batch_results = results
                    st.session_state.batch_running = False

                thread = threading.Thread(target=run_batch, daemon=True)
                thread.start()

                # Monitorear progreso
                while st.session_state.batch_running:
                    self._render_progress_ui(progress_container, metrics_container)
                    time.sleep(1)

                # Mostrar resultados finales
                self._render_final_results(results_container)

    def _render_progress_ui(self, progress_container, metrics_container):
        """Renderiza UI de progreso en tiempo real"""
        with progress_container:
            # Barra de progreso
            progress = self.metrics["processed"] / max(self.metrics["total_targets"], 1)
            st.progress(progress, text=f"Procesados: {self.metrics['processed']}/{self.metrics['total_targets']}")

            # Métricas en tiempo real
            with metrics_container:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("✅ Éxitos", self.metrics["successful"])
                col2.metric("❌ Fallidos", self.metrics["failed"])
                col3.metric("⏱️ Tiempo", self._get_elapsed_time())
                col4.metric("⚡ Rate", f"{self.metrics['processed']}/s")

            # Últimos resultados
            if hasattr(st.session_state, 'batch_results') and st.session_state.batch_results:
                latest = st.session_state.batch_results[-5:]  # Últimos 5
                st.write("Últimos procesados:")
                for res in latest:
                    st.text(f"✓ {res.get('target', {}).get('username') or res.get('target', {}).get('email')}")

    def _render_final_results(self, container):
        """Renderiza resultados finales del batch"""
        with container:
            st.markdown("---")
            st.header("✅ Batch Completado")

            results = st.session_state.batch_results

            # Resumen ejecutivo
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Procesados", self.metrics["processed"])
            col2.metric("Tasa de Éxito", f"{(self.metrics['successful'] / self.metrics['processed'] * 100):.1f}%")
            col3.metric("Tiempo Total", self._get_elapsed_time())
            col4.metric("Hallazgos Totales", sum(len(r.get('modules', {})) for r in results))

            # Análisis por módulo
            st.subheader("📊 Análisis por Módulo")

            module_stats = {}
            for result in results:
                for module_name, module_data in result.get('modules', {}).items():
                    if module_name not in module_stats:
                        module_stats[module_name] = {
                            "found": 0,
                            "not_found": 0,
                            "errors": 0
                        }

                    if isinstance(module_data, dict) and module_data.get('profiles'):
                        module_stats[module_name]["found"] += len(module_data['profiles'])
                    elif isinstance(module_data, list):
                        module_stats[module_name]["found"] += len(module_data)
                    elif "error" in str(module_data):
                        module_stats[module_name]["errors"] += 1
                    else:
                        module_stats[module_name]["not_found"] += 1

            # Mostrar estadísticas
            for module_name, stats in module_stats.items():
                with st.expander(f"**{module_name.upper()}** - Total: {stats['found']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("✅ Encontrados", stats['found'])
                    col2.metric("❌ No Encontrados", stats['not_found'])
                    col3.metric("⚠️ Errores", stats['errors'])

            # Dataframe completo
            st.subheader("📋 Resultados Detallados")

            # Flatten results para DataFrame
            rows = []
            for result in results:
                row = {
                    "id": result['id'],
                    "status": result['status']
                }
                row.update(result['target'])

                # Añadir contadores por módulo
                for module_name in ["socmint", "breachdata", "emailint", "domainint", "phoneint"]:
                    module_data = result['modules'].get(module_name, {})
                    if isinstance(module_data, dict) and module_data.get('profiles'):
                        row[f"{module_name}_count"] = len(module_data['profiles'])
                    elif isinstance(module_data, list):
                        row[f"{module_name}_count"] = len(module_data)
                    else:
                        row[f"{module_name}_count"] = 0

                rows.append(row)

            df_results = pd.DataFrame(rows)
            st.dataframe(df_results, use_container_width=True)

            # Exportación masiva
            st.subheader("📤 Exportación Masiva")

            col1, col2, col3 = st.columns(3)

            with col1:
                # JSON completo
                json_str = json.dumps(results, indent=2, ensure_ascii=False)
                st.download_button(
                    "📥 Descargar JSON",
                    data=json_str,
                    file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )

            with col2:
                # CSV plano
                csv_buffer = io.StringIO()
                df_results.to_csv(csv_buffer, index=False)
                st.download_button(
                    "📥 Descargar CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with col3:
                # Excel con múltiples hojas
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    # Hoja principal
                    df_results.to_excel(writer, sheet_name='Summary', index=False)

                    # Hoja por módulo
                    for module_name in ["socmint", "breachdata"]:
                        module_rows = []
                        for result in results:
                            module_data = result['modules'].get(module_name, {})
                            if isinstance(module_data, dict) and module_data.get('profiles'):
                                for profile in module_data['profiles']:
                                    profile_row = result['target'].copy()
                                    profile_row.update(profile)
                                    module_rows.append(profile_row)

                        if module_rows:
                            df_module = pd.DataFrame(module_rows)
                            df_module.to_excel(writer, sheet_name=module_name.upper(), index=False)

                st.download_button(
                    "📥 Descargar Excel",
                    data=excel_buffer.getvalue(),
                    file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            # Guardar batch en DB
            if st.button("💾 Guardar Batch en Historial", type="primary"):
                batch_id = str(uuid.uuid4())
                self.db.save_batch_search(
                    user_id=self.user_id,
                    batch_id=batch_id,
                    targets_count=len(targets),
                    modules=json.dumps(selected_modules),
                    results=json.dumps(results),
                    metrics=json.dumps(self.metrics)
                )
                st.success(f"✅ Batch guardado con ID: {batch_id}")

    def _get_elapsed_time(self) -> str:
        """Calcula tiempo transcurrido formateado"""
        if not self.metrics["start_time"]:
            return "00:00"

        end = self.metrics["end_time"] or datetime.now()
        elapsed = end - self.metrics["start_time"]

        minutes, seconds = divmod(elapsed.seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"


class AsyncRateLimiter:
    """Rate limiter asíncrono para API calls"""

    def __init__(self, requests_per_second: float):
        self.rate = requests_per_second
        self.tokens = 0
        self.last_update = time.time()
        self.lock = threading.Lock()

    async def acquire(self):
        """Espera hasta tener token disponible"""
        while True:
            with self.lock:
                now = time.time()
                elapsed = now - self.last_update
                self.last_update = now
                self.tokens += elapsed * self.rate

                if self.tokens > self.rate:
                    self.tokens = self.rate

                if self.tokens >= 1:
                    self.tokens -= 1
                    return

            await asyncio.sleep(0.1)


# Integración en app.py
def render_batch_search_ui():
    orchestrator = BatchSearchOrchestrator(
        st.session_state.user["id"], db, config
    )
    orchestrator.render_ui()


# Añadir a la navbar
if st.button("📊 Batch Search"):
    st.session_state.page = "batch"
    st.rerun()

# En control de páginas
if st.session_state.page == "batch":
    render_batch_search_ui()