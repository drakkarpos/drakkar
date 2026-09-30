"""
Registro del usuario en el admin.

Como Usuario hereda de AbstractUser, heredamos también el admin que Django ya
trae: el que sabe encriptar la contraseña, mostrar el formulario de cambio de
clave y manejar los permisos. Escribir uno desde cero sería rehacer trabajo
resuelto — y peor, arriesgarse a guardar contraseñas en texto plano.

El Día 9, cuando Usuario tenga campos propios, acá se agregan a los fieldsets.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Por ahora, idéntico al admin de usuarios de Django."""

    pass
