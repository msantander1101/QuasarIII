import re

def validate_username(username):
    """Valida formato username"""
    return re.match(r'^[a-zA-Z0-9_-]{3,32}$', username)

def validate_email(email):
    """Valida email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email)

def validate_phone(phone):
    """Valida formato internacional"""
    return re.match(r'^\+\d{10,15}$', phone)

# Añadir validación de inputs OSINT:

def validate_domain(domain):
    """Valida dominio real"""
    import socket
    try:
        socket.gethostbyname(domain)
        return True
    except:
        return False

def validate_address(address):
    """Valida formato BTC"""
    pattern = r'^(1|3)[a-km-zA-HJ-NP-Z1-9]{25,34}$|^(bc1)[ac-hj-np-z02-9]{8,87}$'
    return re.match(pattern, address) is not None
