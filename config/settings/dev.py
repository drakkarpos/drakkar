"""
config/settings/dev.py
----------------------
Configuración de desarrollo: tu máquina.
"""

from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']