# modules/instagram_osint.py
from instaloader import Instaloader, Profile
import json


def investigar_instagram(username, session_id):
    """
    Extrae datos de Instagram usando sesión
    """
    L = Instaloader()
    L.load_session_from_file(username, session_id)

    profile = Profile.from_username(L.context, username)

    data = {
        "followers": profile.followers,
        "seguidos": profile.followees,
        "bio": profile.biography,
        "external_url": profile.external_url,
        "es_privado": profile.is_private,
        "fotos": []
    }

    # Obtener posts recientes
    for post in profile.get_posts():
        data["fotos"].append({
            "fecha": post.date.isoformat(),
            "ubicacion": post.location.name if post.location else None,
            "keywords": post.caption_hashtags
        })
        if len(data["fotos"]) >= 10:  # Limitar
            break

    return data