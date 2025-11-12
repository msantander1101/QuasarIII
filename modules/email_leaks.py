# modules/email_leaks.py
import holehe

async def verificar_email(email):
    """
    Verifica email en múltiples servicios
    """
    resultados = await holehe.email_reputation(email)
    return resultados