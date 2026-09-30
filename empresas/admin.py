"""
Pantallas de Empresa y Local.

Tres herramientas que se repiten en todos los admin del proyecto:

  list_display  → qué columnas se ven en el listado
  list_filter   → los filtros de la barra lateral derecha
  search_fields → por qué campos busca el cuadro de búsqueda

Y una cuarta que aparece acá: fieldsets, que agrupa los campos del formulario
en secciones con título. Local tiene trece campos; sin fieldsets es una lista
plana donde no se distingue lo que identifica al local de lo que configura
cómo trabaja.
"""

from django.contrib import admin

from .models import Empresa, Local


class LocalInline(admin.TabularInline):
    """
    Los locales aparecen DENTRO de la ficha de la empresa.

    Un inline sirve cuando el hijo casi no se entiende solo. Un local sin su
    empresa no significa nada, así que verlos juntos es lo natural.
    """

    model = Local
    extra = 0  # sin filas vacías de regalo
    fields = ("nombre", "slug", "direccion", "activo")
    prepopulated_fields = {"slug": ("nombre",)}
    show_change_link = True  # link para abrir el local completo


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rut", "razon_social", "cantidad_locales", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "rut", "razon_social")
    inlines = [LocalInline]

    @admin.display(description="locales")
    def cantidad_locales(self, obj):
        """
        Columna calculada.

        OJO: esto dispara una consulta por fila (el problema N+1). Con veinte
        empresas no se nota; con dos mil, sí. Cuando llegue el Día 20 vamos a
        resolverlo con annotate() en get_queryset(). Lo dejo así a propósito
        para que puedas medir la diferencia cuando corresponda.
        """
        return obj.locales.count()


@admin.register(Local)
class LocalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "slug", "maneja_vencimiento", "maneja_lotes", "activo")
    list_filter = ("activo", "maneja_vencimiento", "maneja_lotes", "venta_por_medida", "empresa")
    search_fields = ("nombre", "slug", "empresa__nombre")
    prepopulated_fields = {"slug": ("nombre",)}

    # `empresa` como buscador en vez de desplegable: con 500 empresas, un
    # <select> obliga al navegador a cargarlas todas en cada formulario.
    autocomplete_fields = ["empresa"]

    fieldsets = (
        ("Identificación", {
            "fields": ("empresa", "nombre", "slug", "direccion", "activo"),
        }),
        ("Configuración operativa", {
            "description": (
                "Definen cómo trabaja este local. Los controla el administrador "
                "del cliente. Lo que el cliente tiene CONTRATADO se maneja aparte, "
                "en la suscripción."
            ),
            "fields": (
                "maneja_vencimiento",
                "maneja_lotes",
                "dias_alerta_vencimiento",
                "venta_por_medida",
                "permite_traspasos",
                "consulta_stock_otros_locales",
            ),
        }),
    )