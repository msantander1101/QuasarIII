import asyncio
import sherlock_project.sherlock as sherlock
from sherlock_project.sherlock import QueryStatus
import pandas as pd


async def buscar_username_en_plataformas(username, profundidad=3):
    """
    Wrapper asíncrono para Sherlock con categorización
    """
    # Cargar sitios de Sherlock
    sites = sherlock.sherlock.load_sites()

    # Seleccionar según profundidad
    if profundidad == 1:
        # Solo plataformas populares
        sitios_filtrados = {k: v for k, v in sites.items()
                            if k in ['Twitter', 'Instagram', 'Facebook', 'LinkedIn']}
    elif profundidad == 2:
        # Populares + foros principales
        sitios_filtrados = {k: v for k, v in sites.items()
                            if any(x in k.lower() for x in
                                   ['twitter', 'instagram', 'facebook', 'reddit', 'github'])}
    else:
        # Todas las plataformas
        sitios_filtrados = sites

    # Ejecutar búsqueda
    resultados = await sherlock.sherlock(
        username=username,
        site_data=sitios_filtrados,
        query_notify=None,
        timeout=30,
        recursive=False,
        print_found_only=False
    )

    # Parsear resultados
    data = []
    for site_name, site_data in resultados.items():
        status = "✅ ENCONTRADO" if site_data['status'].status == QueryStatus.CLAIMED else "❌ No encontrado"

        if site_data['status'].status == QueryStatus.CLAIMED:
            # Categorizar plataforma
            categoria = categorizar_plataforma(site_name)

            data.append({
                "plataforma": site_name,
                "url": site_data['url_user'],
                "status": status,
                "categoria": categoria,
                "metadata": site_data.get('metadata', {})
            })

    return data


def categorizar_plataforma(nombre):
    """
    Categoriza plataformas para filtrado
    """
    nombre_lower = nombre.lower()

    categorias = {
        "Social Media": ['twitter', 'instagram', 'facebook', 'tiktok', 'snapchat'],
        "Profesional": ['linkedin', 'xing', 'zoominfo', 'crunchbase'],
        "Gaming": ['steam', 'twitch', 'epicgames', 'xbox', 'playstation'],
        "Foros": ['reddit', 'quora', 'stackexchange', 'vbulletin'],
        "Dating": ['tinder', 'badoo', 'grindr', 'onlyfans'],
        "Tecnología": ['github', 'gitlab', 'bitbucket', 'docker'],
        "E-Commerce": ['ebay', 'amazon', 'mercadolibre', 'etsy']
    }

    for categoria, keywords in categorias.items():
        if any(keyword in nombre_lower for keyword in keywords):
            return categoria

    return "Otro"