import os
import shutil
from typing import Optional

BASE_DORKS_DIR = "data/dorks"


def save_uploaded_dorks(
    user_id: int,
    uploaded_file,
) -> Optional[str]:
    """
    Guarda un archivo de dorks subido por el usuario (.txt o .json)
    y devuelve la ruta absoluta al fichero.
    """
    if not uploaded_file:
        return None

    filename = uploaded_file.name.lower()
    if not (filename.endswith(".txt") or filename.endswith(".json")):
        return None

    user_dir = os.path.join(BASE_DORKS_DIR, f"user_{user_id}")
    os.makedirs(user_dir, exist_ok=True)

    dst_path = os.path.join(user_dir, filename)

    with open(dst_path, "wb") as f:
        shutil.copyfileobj(uploaded_file, f)

    return dst_path
