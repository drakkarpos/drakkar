"""
Pantallas de ProductoLocal y Lote.

Acá aparece la primera consulta bien hecha del proyecto: el stock total.

El stock no es un campo, es la suma de los lotes. La forma ingenua de mostrarlo
en un listado es preguntar, fila por fila, "¿cuánto suman los lotes de este?".
Con 30 productos son 31 consultas a la base. Con 3.000, son 3.001.

La forma correcta es pedirle a PostgreSQL que sume mientras arma el listado:
una sola consulta que ya vuelve con el total calculado. Eso es `annotate()`,
y es la regla del Día 4: agregar en la base, no en Python.
"""

from django.contrib import admin
from django.db.models import Q, Sum

from .models import Lote, ProductoLocal


class LoteInline(admin.TabularInline):
    """Los lotes de un producto, dentro de la ficha del producto en ese local."""

    model = Lote
    extra = 0
    fields = ("numero", "fecha_vencimiento", "cantidad", "precio_oferta", "activo")
    ordering = ("fecha_vencimiento",)


@admin.register(ProductoLocal)
class ProductoLocalAdmin(admin.ModelAdmin):
    list_display = ("producto", "local", "precio", "stock_total", "stock_minimo", "bajo_minimo", "activo")
    list_filter = ("activo", "local", "local__empresa")
    search_fields = ("producto__nombre", "producto__codigos__codigo")
    autocomplete_fields = ["producto", "local"]
    inlines = [LoteInline]

    def get_queryset(self, request):
        """
        Le agrega a cada fila el total de sus lotes, calculado por PostgreSQL.

        `filter=Q(...)` hace que sume SOLO los lotes activos. Sin eso, un lote
        dado de baja seguiría contando como stock disponible.

        `select_related` trae producto y local en la misma consulta, en vez de
        una por fila cuando el listado los muestre.
        """
        queryset = super().get_queryset(request)
        return queryset.select_related("producto", "local").annotate(
            _stock_total=Sum("lotes__cantidad", filter=Q(lotes__activo=True))
        )

    @admin.display(description="stock", ordering="_stock_total")
    def stock_total(self, obj):
        """
        Muestra lo que annotate() ya calculó. No consulta nada.

        `ordering="_stock_total"` hace que la columna sea ordenable con un
        clic: PostgreSQL ordena por la suma. Una columna calculada en Python
        no se puede ordenar; una anotada, sí.
        """
        return obj._stock_total or 0

    @admin.display(description="bajo mínimo", boolean=True)
    def bajo_minimo(self, obj):
        """`boolean=True` dibuja el ✔/✘ en vez de escribir True/False."""
        return (obj._stock_total or 0) < obj.stock_minimo


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    """
    Pantalla propia además del inline: es la del reporte de vencimientos.

    Con el filtro de `fecha_vencimiento` de la barra lateral se responde
    "¿qué vence este mes?" cruzando todos los locales.
    """

    list_display = ("producto_local", "numero", "fecha_vencimiento", "cantidad", "precio_oferta", "activo")
    list_filter = ("activo", "fecha_vencimiento", "producto_local__local")
    search_fields = ("numero", "producto_local__producto__nombre")
    autocomplete_fields = ["producto_local"]
    date_hierarchy = "fecha_vencimiento"  # navegador por año / mes / día

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "producto_local__producto", "producto_local__local"
        )