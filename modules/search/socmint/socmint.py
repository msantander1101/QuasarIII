# modules/search/socmint/socmint.py
import subprocess
import os
import json
import logging

logger = logging.getLogger(__name__)

def search_social_profiles(username: str, platforms=None):
    """
    SOCMINT limpio, seguro y compatible para Maigret / Sherlock.
    Recibe SOLO `username` (ej: 'miguel_santander'), nunca email.
    Devuelve diccionario: {"social_profiles": { "maigret": {...}, "sherlock": {...} }, ...}
    """
    if not username or not isinstance(username, str) or len(username.strip()) < 2:
        return {"social_profiles": {}, "error": "Username inválido"}

    username = username.strip()
    if platforms is None:
        platforms = ["maigret", "sherlock"]

    results = {"social_profiles": {}}

    # ---------- MAIGRET ----------
    if "maigret" in platforms:
        try:
            # Usar formato simple o ndjson según instalación; 'simple' es más estable para parseo
            cmd = ["maigret", "--json", "simple", username]

            raw = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            # Guardamos raw. Si en tu Maigret tienes JSON estructurado preferir parsearlo aquí
            results["social_profiles"]["maigret"] = {"raw_output": raw}

        except subprocess.CalledProcessError as e:
            logger.warning(f"[SOCMINT][Maigret] CalledProcessError: {e}")
            out = getattr(e, "output", str(e))
            results["social_profiles"]["maigret"] = {"error": out}
        except Exception as e:
            logger.exception(f"[SOCMINT][Maigret] Error ejecutando Maigret para {username}: {e}")
            results["social_profiles"]["maigret"] = {"error": str(e)}

    # ---------- SHERLOCK ----------
    if "sherlock" in platforms:
        try:
            # Generamos tmp file en cwd para evitar problemas de permisos y path en Windows
            tmp_file = os.path.join(os.getcwd(), f"sherlock_{username}.json")

            # Asegurarnos de no dejar archivos previos que confundan
            try:
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
            except Exception:
                pass

            cmd = ["sherlock", "--json", tmp_file, username]

            subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            if os.path.exists(tmp_file):
                try:
                    with open(tmp_file, "r", encoding="utf-8", errors="replace") as f:
                        data = f.read()
                    results["social_profiles"]["sherlock"] = {"raw_output": data}
                except Exception as e:
                    results["social_profiles"]["sherlock"] = {"error": f"No se pudo leer {tmp_file}: {e}"}
                finally:
                    # opcional: limpiar tmp para no llenar el disco
                    try:
                        os.remove(tmp_file)
                    except Exception:
                        pass
            else:
                results["social_profiles"]["sherlock"] = {"error": "Archivo JSON no generado por Sherlock."}

        except subprocess.CalledProcessError as e:
            logger.warning(f"[SOCMINT][Sherlock] CalledProcessError: {e}")
            out = getattr(e, "output", str(e))
            results["social_profiles"]["sherlock"] = {"error": out}
        except Exception as e:
            logger.exception(f"[SOCMINT][Sherlock] Error ejecutando Sherlock para {username}: {e}")
            results["social_profiles"]["sherlock"] = {"error": str(e)}

    return results
3