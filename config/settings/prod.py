"""
config/settings/prod.py
-----------------------
Configuración de producción: Raspberry Pi y VPS.
"""

from .base import *

DEBUG = False

# Sin valor por defecto a propósito: en producción hay que declarar
# explícitamente qué dominios pueden servir esta aplicación.
ALLOWED_HOSTS = os.environ['DJANGO_ALLOWED_HOSTS'].split(',')

# Exigen HTTPS. Se activan cuando el dominio esté funcionando (Día 29).
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True