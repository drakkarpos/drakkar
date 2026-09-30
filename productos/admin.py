"""
Pantallas de Producto y CodigoBarra.

Los códigos van como inline dentro del producto: un código de barra suelto no
significa nada, y la operación real es "agregarle otro código a esta ficha".
"""

from django.contrib import admin

from .models import CodigoBarra, Producto


class CodigoBarraInline(admin.TabularInline):
    model = CodigoBarra
    extra = 1
    fields = ("codigo", "principal", "activo")
    # `empresa` no aparece en el formulario: se copia sola desde el producto
    # (ver save_formset más abajo). Es un campo denormalizado, existe solo
    # para que el escaneo sea rápido. Si se cargara a mano, tarde o temprano
    # alguien graba un código con la empresa equivocada y deja de encontrarse.


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "empresa",
        "unidad_medida",
        "controla_vencimiento",
        "controla_lote",
        "activo",
    )
    list_filter = ("activo", "unidad_medida", "controla_vencimiento", "controla_lote", "empresa")

    # Busca por nombre del producto Y por cualquiera de sus códigos de barra.
    # El doble guion bajo salta a la tabla relacionada: es como se atraviesan
    # relaciones en Django, tanto acá como en cualquier filtro.
    search_fields = ("nombre", "codigos__codigo")

    autocomplete_fields = ["empresa", "producto_padre"]
    inlines = [CodigoBarraInline]

    fieldsets = (
        ("Identificación", {
            "fields": ("empresa", "nombre", "descripcion", "unidad_medida", "activo"),
        }),
        ("Control de vencimiento", {
            "description": (
                "¿Esta COSA vence? Es una característica del producto. "
                "La fecha concreta de cada tanda se guarda en el lote."
            ),
            "fields": ("controla_vencimiento", "controla_lote"),
        }),
        ("Fraccionamiento", {
            "description": (
                "Solo si este producto sale de fraccionar otro. "
                "Ej: la unidad suelta que sale de una caja de 30. "
                "Los dos campos van juntos o ninguno."
            ),
            "classes": ("collapse",),  # arranca plegado: no aplica a la mayoría
            "fields": ("producto_padre", "factor_conversion"),
        }),
    )

    def save_formset(self, request, form, formset, change):
        """
        Al guardar los códigos de barra, les copia la empresa del producto.

        `save_formset` es el enganche que Django ofrece para meterse entre
        "el usuario apretó Guardar" y "se escribe en la base". Acá se completan
        los campos que el sistema sabe y el usuario no debería tener que saber.
        """
        if formset.model is CodigoBarra:
            instancias = formset.save(commit=False)
            for codigo in instancias:
                codigo.empresa = form.instance.empresa
                codigo.save()
            for borrado in formset.deleted_objects:
                borrado.delete()
            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)


@admin.register(CodigoBarra)
class CodigoBarraAdmin(admin.ModelAdmin):
    """
    Pantalla propia además del inline.

    Sirve para la pregunta al revés: "escaneé este código, ¿de qué producto es?".
    """

    list_display = ("codigo", "producto", "empresa", "principal", "activo")
    list_filter = ("activo", "principal", "empresa")
    search_fields = ("codigo", "producto__nombre")
    autocomplete_fields = ["producto", "empresa"]