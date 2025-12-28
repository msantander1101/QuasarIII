import sqlite3
import os
import logging
import json

# Configurar logger
logger = logging.getLogger(__name__)


def create_db(db_path: str = 'data/users.db'):
    """
    Crea la base de datos SQLite e inicializa las tablas si no existen.
    """
    # Asegurarse de que el directorio 'data' existe
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    logger.info("Intentando conectar a DB: %s", db_path)

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        logger.info("Conexión a SQLite establecida.")

        # Tabla de usuarios
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash BLOB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')

        # Tabla para almacenar informacion de personas buscadas (búsqueda y relaciones)
        c.execute('''CREATE TABLE IF NOT EXISTS persons (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        name TEXT,
                        email TEXT,
                        phone TEXT,
                        location TEXT,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )''')

        # Tabla para almacenar RELACIONES entre personas
        c.execute('''CREATE TABLE IF NOT EXISTS relationships (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        person1_id INTEGER NOT NULL,
                        person2_id INTEGER NOT NULL,
                        relationship_type TEXT NOT NULL,
                        details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (person1_id) REFERENCES persons (id),
                        FOREIGN KEY (person2_id) REFERENCES persons (id)
                    )''')

        # Tabla para almacenar datos de búsqueda realizadas por usuario
        c.execute('''CREATE TABLE IF NOT EXISTS analysis_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        data_type TEXT NOT NULL,
                        data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )''')

        # --- NUEVA TABLA PARA CONFIGURACIONES DE USUARIO ---
        c.execute('''CREATE TABLE IF NOT EXISTS user_configs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        config_key TEXT NOT NULL,
                        config_value TEXT NOT NULL,
                        encrypted BOOLEAN DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        UNIQUE(user_id, config_key)
                    )''')

        # Tabla de INVESTIGACIONES (búsquedas agrupadas en una entidad)
        c.execute('''CREATE TABLE IF NOT EXISTS investigations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        root_query TEXT NOT NULL,
                        entity_type TEXT,              -- p.ej. person, email, domain, username
                        label TEXT,                    -- nombre amigable para la investigación
                        notes TEXT,                    -- notas libres del analista
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )''')

        # Resultados asociados a una investigación (snapshot en JSON)
        c.execute('''CREATE TABLE IF NOT EXISTS investigation_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        investigation_id INTEGER NOT NULL,
                        source TEXT NOT NULL,          -- p.ej. combined, people, email, web, dorks...
                        result_json TEXT NOT NULL,     -- JSON completo con resultados
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (investigation_id) REFERENCES investigations (id)
                    )''')

        conn.commit()
        conn.close()
        logger.info("Tablas creadas o verificadas correctamente.")
        return True
    except Exception as e:
        logger.error(f"Error al crear tablas: {e}")
        return False


# --- FUNCIONES CRUD BÁSICAS de PERSONAS ---
def create_person(user_id: int, name: str, email: str = "", phone: str = "", location: str = "", description: str = "", db_path: str = 'data/users.db'):
    """Crea una nueva persona en la base de datos."""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO persons (user_id, name, email, phone, location, description) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, email, phone, location, description)
        )
        person_id = c.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Persona '{name}' creada con ID {person_id} para usuario {user_id}.")
        return person_id
    except Exception as e:
        logger.error(f"Error creando persona: {e}")
        return None


def get_person_by_id(person_id: int, db_path: str = 'data/users.db'):
    """Obtiene información de una persona por su ID."""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "SELECT id, user_id, name, email, phone, location, description, created_at FROM persons WHERE id=?",
            (person_id,)
        )
        person = c.fetchone()
        conn.close()
        if person:
            return {
                "id": person[0],
                "user_id": person[1],
                "name": person[2],
                "email": person[3],
                "phone": person[4],
                "location": person[5],
                "description": person[6],
                "created_at": person[7]
            }
        return None
    except Exception as e:
        logger.error(f"Error obteniendo persona por ID: {e}")
        return None


def get_persons_by_user(user_id: int, db_path: str = 'data/users.db'):
    """Obtiene todas las personas asociadas a un usuario (para el historial de búsquedas)."""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "SELECT id, name, email, phone, location, description, created_at FROM persons WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)
        )
        persons = c.fetchall()
        conn.close()
        # Convertir a lista de diccionarios
        return [
            {
                "id": p[0],
                "name": p[1],
                "email": p[2],
                "phone": p[3],
                "location": p[4],
                "description": p[5],
                "created_at": p[6]
            }
            for p in persons
        ]
    except Exception as e:
        logger.error(f"Error obteniendo personas por usuario: {e}")
        return []


# --- FUNCIONES CRUD BÁSICAS de RELACIONES ---
def create_relationship(person1_id: int, person2_id: int, relationship_type: str, details: str = "", db_path: str = 'data/users.db'):
    """Crea una relación entre dos personas."""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "INSERT INTO relationships (person1_id, person2_id, relationship_type, details) VALUES (?, ?, ?, ?)",
            (person1_id, person2_id, relationship_type, details)
        )
        rel_id = c.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Relación creada entre personas {person1_id} y {person2_id} de tipo '{relationship_type}'.")
        return rel_id
    except Exception as e:
        logger.error(f"Error creando relación: {e}")
        return None


def get_relationships_for_person(person_id: int, db_path: str = 'data/users.db'):
    """Obtiene todas las relaciones de una persona."""
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        # Usando JOINs para obtener datos completos de ambas personas
        c.execute('''SELECT r.id, p1.id, p1.name, p1.email, p1.phone, p1.location, 
                           p2.id, p2.name, p2.email, p2.phone, p2.location,
                           r.relationship_type, r.details
                    FROM relationships r
                    JOIN persons p1 ON r.person1_id = p1.id
                    JOIN persons p2 ON r.person2_id = p2.id
                    WHERE r.person1_id = ? OR r.person2_id = ?
                    ORDER BY r.created_at DESC''', (person_id, person_id))
        results = c.fetchall()
        conn.close()
        relationships = []
        for row in results:
            rel_info = {
                "id": row[0],
                "person1": {
                    "id": row[1],
                    "name": row[2],
                    "email": row[3],
                    "phone": row[4],
                    "location": row[5]
                },
                "person2": {
                    "id": row[6],
                    "name": row[7],
                    "email": row[8],
                    "phone": row[9],
                    "location": row[10]
                },
                "type": row[11],
                "details": row[12]
            }
            relationships.append(rel_info)
        return relationships
    except Exception as e:
        logger.error(f"Error obteniendo relaciones: {e}")
        return []


def get_all_relationships_for_persons(person_ids: list, db_path: str = 'data/users.db'):
    """
    Obtiene todas las relaciones que involucran un conjunto de personas.
    Útil para dibujar el grafo completo.
    """
    placeholders = ','.join('?' * len(person_ids))
    query = f'''SELECT r.id, r.person1_id, r.person2_id, r.relationship_type, r.details
                FROM relationships r
                WHERE r.person1_id IN ({placeholders}) AND r.person2_id IN ({placeholders})
                ORDER BY r.created_at DESC'''

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(query, person_ids * 2)
        results = c.fetchall()
        conn.close()
        # Convertir a una lista de diccionarios
        return [
            {
                "id": row[0],
                "person1_id": row[1],
                "person2_id": row[2],
                "type": row[3],
                "details": row[4]
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Error obteniendo relaciones múltiples: {e}")
        return []


# --- FUNCIONES AUXILIARES DE BÚSQUEDA ---
def search_persons_by_criteria(user_id: int, criteria: dict, db_path: str = 'data/users.db'):
    """
    Busca personas basadas en criterios proporcionados (nombre, email, etc.)
    Por simplicidad, asumimos que todos los campos son LIKE.
    """
    query = "SELECT id, name, email, phone, location, description, created_at FROM persons WHERE user_id=?"
    params = [user_id]
    conditions = []

    for field, value in criteria.items():
        if field in ["name", "email", "phone", "location"]:
            conditions.append(f"{field} LIKE ?")
            params.append(f"%{value}%")

    if conditions:
        query += " AND " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC"

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(query, params)
        results = c.fetchall()
        conn.close()
        return [
            {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "phone": row[3],
                "location": row[4],
                "description": row[5],
                "created_at": row[6]
            }
            for row in results
        ]
    except Exception as e:
        logger.error(f"Error en búsqueda por criterios: {e}")
        return []


# --- FUNCIONES PARA EL GRAFO (GRAFOS COMPLETOS) ---
def get_graph_for_user(user_id: int, db_path: str = 'data/users.db'):
    """
    Obtiene todas las personas y relaciones de un usuario para dibujar un grafo.
    Resultado compatible con visualización.
    """
    # Primero obtener todas las personas
    persons = get_persons_by_user(user_id, db_path)
    if not persons:
        return {"persons": [], "relationships": []}

    person_ids = [p["id"] for p in persons]

    # Luego obtener las relaciones relacionadas con estas personas
    all_rels = get_all_relationships_for_persons(person_ids, db_path)
    relationships = [
        {
            "source": r["person1_id"],
            "target": r["person2_id"],
            "type": r["type"],
            "details": r["details"]
        }
        for r in all_rels
    ]

    # Agregar también personas no conectadas al grafo (pueden ser nodos "aislados")
    # Esto ya lo tenemos en 'persons'

    return {"persons": persons, "relationships": relationships}


# --- FUNCIONES PARA CONFIGURACIONES ---
def save_user_config(user_id: int, config_key: str, config_value: str, encrypt_value: bool = False, db_path: str = 'data/users.db') -> bool:
    """
    Guarda una configuración (clave API) para un usuario.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        encrypted = 1 if encrypt_value else 0
        c.execute(
            '''INSERT OR REPLACE INTO user_configs (user_id, config_key, config_value, encrypted) 
               VALUES (?, ?, ?, ?)''',
            (user_id, config_key, config_value, encrypted)
        )
        conn.commit()
        conn.close()
        logger.info(f"Configuración guardada para usuario {user_id}: {config_key}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar configuración: {e}")
        return False


def get_user_config(user_id: int, config_key: str, db_path: str = 'data/users.db') -> str:
    """
    Obtiene valor de una configuración para un usuario.
    No devuelve claves sensibles si están cifradas.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "SELECT config_value FROM user_configs WHERE user_id=? AND config_key=?",
            (user_id, config_key)
        )
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Error obteniendo configuración para usuario {user_id} clave {config_key}: {e}")
        return None


def delete_user_config(user_id: int, config_key: str, db_path: str = 'data/users.db') -> bool:
    """
    Elimina una configuración específica de un usuario.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "DELETE FROM user_configs WHERE user_id=? AND config_key=?",
            (user_id, config_key)
        )
        conn.commit()
        rows_impacted = c.rowcount
        conn.close()
        logger.info(f"Configuración eliminada para usuario {user_id}: {config_key}, filas afectadas: {rows_impacted}")
        return rows_impacted > 0
    except Exception as e:
        logger.error(f"Error eliminando configuración: {e}")
        return False


def list_user_configs(user_id: int, db_path: str = 'data/users.db') -> list:
    """
    Devuelve todas las configuraciones disponibles para un usuario (sin los valores realmente sensibles).
    Puede usarse para mostrar la lista de claves almacenadas.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "SELECT config_key, created_at, updated_at FROM user_configs WHERE user_id=?",
            (user_id,)
        )
        results = c.fetchall()
        conn.close()
        return [
            {
                "config_key": r[0],
                "created_at": r[1],
                "updated_at": r[2]
            }
            for r in results
        ]
    except Exception as e:
        logger.error(f"Error listando configuraciones: {e}")
        return []


# --- FUNCIONES AUXILIARES PARA USUARIOS ---
def get_user_by_username(username: str, db_path: str = 'data/users.db'):
    """
    Obtiene información de un usuario por su nombre de usuario.
    Retorna una tupla con (id, username, email, password_hash) o None si no existe.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "SELECT id, username, email, password_hash FROM users WHERE username=?",
            (username,)
        )
        user = c.fetchone()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Error obteniendo usuario por nombre de usuario: {e}")
        return None


def get_user_by_id(user_id: int, db_path: str = 'data/users.db'):
    """
    Obtiene información de un usuario por su ID.
    Retorna una tupla con (id, username, email) o None si no existe.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            "SELECT id, username, email FROM users WHERE id=?",
            (user_id,)
        )
        user = c.fetchone()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Error obteniendo usuario por ID: {e}")
        return None


# --- FUNCIONES PARA INVESTIGACIONES / CASOS ---

def create_investigation(
    user_id: int,
    root_query: str,
    entity_type: str = None,
    label: str = None,
    notes: str = "",
    db_path: str = 'data/users.db',
) -> int:
    """
    Crea una nueva 'investigación' asociada a una búsqueda.

    Devuelve el ID de la investigación creada.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            """INSERT INTO investigations (user_id, root_query, entity_type, label, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, root_query, entity_type, label, notes),
        )
        inv_id = c.lastrowid
        conn.commit()
        conn.close()
        logger.info(
            "Investigación creada: id=%s user_id=%s root_query=%s",
            inv_id, user_id, root_query
        )
        return inv_id
    except Exception as e:
        logger.error(f"Error creando investigación: {e}")
        return None


def save_investigation_results(
    investigation_id: int,
    results: dict,
    source: str = "combined",
    db_path: str = 'data/users.db',
) -> bool:
    """
    Guarda un snapshot JSON de los resultados asociados a una investigación.

    Por defecto guarda todo el dict 'results' bajo el source 'combined'.
    """
    try:
        payload = json.dumps(results, ensure_ascii=False)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            """INSERT INTO investigation_results (investigation_id, source, result_json)
               VALUES (?, ?, ?)""",
            (investigation_id, source, payload),
        )
        conn.commit()
        conn.close()
        logger.info(
            "Resultados guardados para investigación id=%s (source=%s)",
            investigation_id, source
        )
        return True
    except Exception as e:
        logger.error(f"Error guardando resultados de investigación: {e}")
        return False


def list_investigations_for_user(
    user_id: int,
    db_path: str = 'data/users.db',
):
    """
    Devuelve un listado básico de investigaciones de un usuario.
    Incluye notes para poder editarlas desde la UI.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            """SELECT id, root_query, entity_type, label, notes, created_at
               FROM investigations
               WHERE user_id=?
               ORDER BY created_at DESC""",
            (user_id,),
        )
        rows = c.fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "root_query": r[1],
                "entity_type": r[2],
                "label": r[3],
                "notes": r[4],
                "created_at": r[5],
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"Error listando investigaciones para user_id {user_id}: {e}")
        return []


def get_investigation_with_results(
    investigation_id: int,
    db_path: str = 'data/users.db',
):
    """
    Recupera una investigación y su snapshot de resultados (si existe).
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        c.execute(
            """SELECT id, user_id, root_query, entity_type, label, notes, created_at
               FROM investigations
               WHERE id=?""",
            (investigation_id,),
        )
        inv = c.fetchone()
        if not inv:
            conn.close()
            return None

        investigation = {
            "id": inv[0],
            "user_id": inv[1],
            "root_query": inv[2],
            "entity_type": inv[3],
            "label": inv[4],
            "notes": inv[5],
            "created_at": inv[6],
        }

        c.execute(
            """SELECT id, source, result_json, created_at
               FROM investigation_results
               WHERE investigation_id=?
               ORDER BY created_at DESC""",
            (investigation_id,),
        )
        res_rows = c.fetchall()
        conn.close()

        results = []
        for r in res_rows:
            try:
                payload = json.loads(r[2])
            except Exception:
                payload = None
            results.append(
                {
                    "id": r[0],
                    "source": r[1],
                    "data": payload,
                    "created_at": r[3],
                }
            )

        investigation["results"] = results
        return investigation
    except Exception as e:
        logger.error(f"Error obteniendo investigación id={investigation_id}: {e}")
        return None


def update_investigation_notes(
    investigation_id: int,
    notes: str,
    db_path: str = 'data/users.db',
) -> bool:
    """
    Actualiza las notas de una investigación concreta.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(
            """UPDATE investigations
               SET notes=?
               WHERE id=?""",
            (notes, investigation_id),
        )
        conn.commit()
        rows = c.rowcount
        conn.close()
        logger.info(
            "Notas actualizadas para investigación id=%s (rows=%s)",
            investigation_id, rows
        )
        return rows > 0
    except Exception as e:
        logger.error(f"Error actualizando notas de investigación id={investigation_id}: {e}")
        return False


def delete_investigation(
    investigation_id: int,
    db_path: str = 'data/users.db',
) -> bool:
    """
    Elimina una investigación y todos sus snapshots de resultados asociados.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Primero borramos los resultados asociados
        c.execute(
            "DELETE FROM investigation_results WHERE investigation_id=?",
            (investigation_id,),
        )

        # Luego la investigación en sí
        c.execute(
            "DELETE FROM investigations WHERE id=?",
            (investigation_id,),
        )
        conn.commit()
        rows = c.rowcount
        conn.close()

        logger.info(
            "Investigación eliminada id=%s (rows=%s)",
            investigation_id, rows
        )
        return rows > 0
    except Exception as e:
        logger.error(f"Error eliminando investigación id={investigation_id}: {e}")
        return False
