"""
Panel de administración de Drakkar.

Django ordena las secciones del admin alfabéticamente. Eso deja Usuarios al
final, lejos de Empresas, cuando en realidad son lo primero que se toca al dar
de alta un cliente: empresa → sus locales → su administrador.

Acá se define el orden a mano, siguiendo el recorrido real de trabajo:

    Empresas  → quién es el cliente y dónde trabaja
    Usuarios  → quién entra
    Productos → qué vende
    Stock     → cuánto tiene
    Auth      → grupos y permisos (herramienta, va al final)
"""

from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig


class DrakkarAdminSite(AdminSite):
    site_header = "Drakkar — administración"
    site_title = "Drakkar"
    index_title = "Panel del superusuario"

    # El orden que queremos. Lo que no esté en esta lista va al final,
    # alfabético: así una app nueva aparece igual, aunque nos olvidemos
    # de agregarla acá.
    ORDEN_APPS = ["empresas", "usuarios", "productos", "stock", "auth"]

    def get_app_list(self, request, app_label=None):
        """
        Reordena las secciones de la portada del admin.

        `super()` devuelve la lista que Django armó (ya filtrada por permisos:
        cada usuario ve solo lo que puede tocar). Nosotros no decidimos QUÉ se
        muestra —eso sigue siendo cosa de los permisos— solo EN QUÉ ORDEN.
        """
        app_list = super().get_app_list(request, app_label)

        def posicion(app):
            etiqueta = app["app_label"]
            if etiqueta in self.ORDEN_APPS:
                return (0, self.ORDEN_APPS.index(etiqueta), "")
            # Las no listadas: después de todas las conocidas, alfabéticas.
            return (1, 0, app["name"])

        return sorted(app_list, key=posicion)


class DrakkarAdminConfig(AdminConfig):
    """
    Le dice a Django que use nuestro panel en vez del suyo.

    Se activa reemplazando "django.contrib.admin" por
    "config.admin.DrakkarAdminConfig" en INSTALLED_APPS.
    """

    default_site = "config.admin.DrakkarAdminSite"