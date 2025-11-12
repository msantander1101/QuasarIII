import sqlite3
import os
from datetime import datetime, timedelta
import json


class DatabaseManager:
    def __init__(self, db_path="osint_users.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Crea tablas si no existen"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabla de usuarios (contrasenia hasheada)
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS users
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           username
                           TEXT
                           UNIQUE
                           NOT
                           NULL,
                           email
                           TEXT
                           UNIQUE
                           NOT
                           NULL,
                           password_hash
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           is_active
                           INTEGER
                           DEFAULT
                           1
                       )
                       ''')

        # Tabla de configuraciones de API (claves cifradas)
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS api_keys
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           service_name
                           TEXT
                           NOT
                           NULL,
                           encrypted_key
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       ) ON DELETE CASCADE,
                           UNIQUE
                       (
                           user_id,
                           service_name
                       )
                           )
                       ''')

        # Tabla de búsquedas por usuario
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS searches
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           target_username
                           TEXT,
                           target_email
                           TEXT,
                           target_phone
                           TEXT,
                           results_json
                           TEXT,
                           search_date
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS monitoring_jobs
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           target_username
                           TEXT
                           NOT
                           NULL,
                           platform
                           TEXT
                           NOT
                           NULL,
                           interval_hours
                           INTEGER
                           DEFAULT
                           24,
                           last_check
                           TIMESTAMP,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS alerts
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           title
                           TEXT
                           NOT
                           NULL,
                           message
                           TEXT,
                           is_read
                           INTEGER
                           DEFAULT
                           0,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS proxies
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           proxy_type
                           TEXT
                           NOT
                           NULL,
                           host
                           TEXT
                           NOT
                           NULL,
                           port
                           INTEGER
                           NOT
                           NULL,
                           username
                           TEXT,
                           password
                           TEXT,
                           is_active
                           INTEGER
                           DEFAULT
                           1,
                           last_test
                           TIMESTAMP,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS monitoring_checks
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           target_username
                           TEXT
                           NOT
                           NULL,
                           platform
                           TEXT
                           NOT
                           NULL,
                           check_data
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           UNIQUE
                       (
                           user_id,
                           target_username,
                           platform,
                           created_at
                       ),
                           FOREIGN KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS batch_searches
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           user_id
                           INTEGER
                           NOT
                           NULL,
                           batch_id
                           TEXT
                           UNIQUE
                           NOT
                           NULL,
                           targets_count
                           INTEGER
                           NOT
                           NULL,
                           modules
                           TEXT
                           NOT
                           NULL,
                           results
                           TEXT,
                           metrics
                           TEXT,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           FOREIGN
                           KEY
                       (
                           user_id
                       ) REFERENCES users
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       ''')

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS batch_results
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           batch_id
                           TEXT
                           NOT
                           NULL,
                           target_id
                           TEXT
                           NOT
                           NULL,
                           target_data
                           TEXT
                           NOT
                           NULL,
                           results
                           TEXT,
                           status
                           TEXT
                           NOT
                           NULL,
                           FOREIGN
                           KEY
                       (
                           batch_id
                       ) REFERENCES batch_searches
                       (
                           batch_id
                       ) ON DELETE CASCADE
                           )
                       ''')
        conn.commit()
        conn.close()

    def create_user(self, username, email, password_hash):
        """Crea nuevo usuario"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            return None

    def get_user(self, username):
        """Obtiene usuario por username"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        return user

    def save_search(self, user_id, target_username, target_email, target_phone, results_json):
        """Guarda búsqueda en historial"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       INSERT INTO searches (user_id, target_username, target_email, target_phone, results_json)
                       VALUES (?, ?, ?, ?, ?)
                       ''', (user_id, target_username, target_email, target_phone, results_json))
        conn.commit()
        conn.close()

    def get_user_searches(self, user_id, limit=50):
        """Obtiene historial de búsquedas del usuario"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT *
                       FROM searches
                       WHERE user_id = ?
                       ORDER BY search_date DESC LIMIT ?
                       ''', (user_id, limit))
        searches = cursor.fetchall()
        conn.close()
        return searches

    def save_api_key(self, user_id, service_name, encrypted_key):
        """Guarda clave API o proxy (TEXT o BLOB)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO api_keys (user_id, service_name, encrypted_key)
            VALUES (?, ?, ?)
        ''', (user_id, service_name, encrypted_key))
        conn.commit()
        conn.close()

    def get_api_key(self, user_id, service_name):
        """Obtiene clave API cifrada"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT encrypted_key
                       FROM api_keys
                       WHERE user_id = ?
                         AND service_name = ?
                       ''', (user_id, service_name))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_all_api_keys(self, user_id):
        """Obtiene todas las claves API del usuario"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT service_name, encrypted_key
                       FROM api_keys
                       WHERE user_id = ?
                       ''', (user_id,))
        keys = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in keys}

    def delete_api_key(self, user_id, service_name):
        """Elimina una clave API"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       DELETE
                       FROM api_keys
                       WHERE user_id = ?
                         AND service_name = ?
                       ''', (user_id, service_name))
        conn.commit()
        conn.close()

    def delete_search(self, search_id):
        """Eliminar búsqueda del historial"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM searches WHERE id = ?", (search_id,))
        conn.commit()
        conn.close()

    def save_search(self, user_id, target_username, target_email, target_phone, results_json, report_pdf=None):
        """Guarda búsqueda con reporte PDF opcional"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Añadir columna report_pdf si no existe
        try:
            cursor.execute("ALTER TABLE searches ADD COLUMN report_pdf BLOB")
        except:
            pass

        cursor.execute('''
                       INSERT INTO searches
                       (user_id, target_username, target_email, target_phone, results_json, report_pdf)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ''', (user_id, target_username, target_email, target_phone, results_json, report_pdf))

        conn.commit()
        conn.close()

    def get_search_with_report(self, search_id):
        """Obtiene búsqueda incluyendo PDF"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT *
                       FROM searches
                       WHERE id = ?
                       ''', (search_id,))
        result = cursor.fetchone()
        conn.close()
        return result

    def get_unread_alerts(self, user_id):
        """Obtiene alertas no leídas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT *
                       FROM alerts
                       WHERE user_id = ?
                         AND is_read = 0
                       ORDER BY created_at DESC
                       ''', (user_id,))
        alerts = cursor.fetchall()
        conn.close()
        return alerts

    def save_monitoring_check(self, user_id, username, platform, data):
        """Guarda resultado de monitoreo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       INSERT INTO monitoring_checks (user_id, target_username, platform, check_data)
                       VALUES (?, ?, ?, ?)
                       ''', (user_id, username, platform, json.dumps(data)))
        conn.commit()
        conn.close()

    def get_total_searches(self, user_id: int) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM searches WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()[0]
        conn.close()
        return result

    def get_unique_targets_count(self, user_id: int) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT COUNT(DISTINCT COALESCE(target_username, target_email, target_phone))
                       FROM searches
                       WHERE user_id = ?
                       ''', (user_id,))
        result = cursor.fetchone()[0]
        conn.close()
        return result

    def get_critical_findings_count(self, user_id: int) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT COUNT(*)
                       FROM alerts
                       WHERE user_id = ?
                         AND priority = 'HIGH'
                       ''', (user_id,))
        result = cursor.fetchone()[0]
        conn.close()
        return result

    def get_recent_alerts(self, user_id: int, limit: int = 10) -> list:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT *
                       FROM alerts
                       WHERE user_id = ?
                       ORDER BY created_at DESC LIMIT ?
                       ''', (user_id, limit))
        alerts = cursor.fetchall()
        conn.close()
        return alerts

    def get_daily_activity(self, user_id: int, days: int = 30) -> list:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        start_date = datetime.now() - timedelta(days=days)
        cursor.execute('''
                       SELECT DATE (search_date) as date, COUNT (*) as count
                       FROM searches
                       WHERE user_id = ? AND search_date >= ?
                       GROUP BY DATE (search_date)
                       ORDER BY date
                       ''', (user_id, start_date.isoformat()))
        data = cursor.fetchall()
        conn.close()
        return data

    def save_batch_search(self, user_id, batch_id, targets_count, modules, results, metrics):
        """Guarda batch search en DB"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       INSERT INTO batch_searches
                           (user_id, batch_id, targets_count, modules, results, metrics)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ''', (user_id, batch_id, targets_count, modules, results, metrics))
        conn.commit()
        conn.close()

    def get_user_batch_searches(self, user_id, limit=50):
        """Obtiene historial de batches"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
                       SELECT *
                       FROM batch_searches
                       WHERE user_id = ?
                       ORDER BY created_at DESC LIMIT ?
                       ''', (user_id, limit))
        batches = cursor.fetchall()
        conn.close()
        return batches

    def mark_alert_read(self, alert_id: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE alerts SET is_read = 1 WHERE id = ?', (alert_id,))
        conn.commit()
        conn.close()
