"""
Modelo de usuario de Drakkar.

Por qué existe este archivo hoy, si el Día 9 es el de usuarios:
Django trae su propio modelo de usuario (auth.User) y lo crea en la primera
migración. A partir de ahí, permisos, grupos y sesiones quedan apuntando a esa
tabla. Reemplazarlo después es la operación más cara del framework.

La solución es declararlo AHORA, aunque todavía no le agreguemos nada.
AbstractUser nos da exactamente lo mismo que auth.User (username, password,
email, nombre, is_active, is_staff...), pero en una tabla NUESTRA.

El Día 9 le agregamos los campos que necesitemos (empresa, rol, teléfono) y
será una migración normal, no una cirugía.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Usuario del sistema. Hoy es idéntico a auth.User.

    NO agregar campos acá todavía: eso es el Día 9. Lo único que importa hoy
    es que la tabla exista con nuestro nombre antes del primer migrate.
    """

    class Meta:
        db_table = "usuarios_usuario"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return self.get_username()

# Create your models here.
