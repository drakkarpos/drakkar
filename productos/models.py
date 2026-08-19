"""
El catálogo: qué cosas conoce la empresa.

Acá NO hay stock ni precio. Acá vive la identidad del producto: qué es, cómo
se mide, si vence. Cuánto hay y cuánto vale es asunto de cada local (app stock).

Decisión clave (Día 4, decisión 2): el código de barras NO identifica al
producto. Los laboratorios cambian códigos; si la identidad fuera el código,
cada cambio partiría el historial en dos productos distintos. La identidad es
el `id` interno: nunca cambia, nunca lo ve el usuario, y de él cuelga todo.
"""

from django.db import models

from empresas.models import Empresa


class UnidadMedida(models.TextChoices):
    """
    Cómo se mide y se vende el producto.

    El valor guardado es corto y estable; la etiqueta es lo que ve el usuario.
    `decimales` no está acá: la interfaz decide cuántos mostrar según la
    unidad (unidad → 0 decimales, kg → 3). La base siempre guarda decimales.
    """

    UNIDAD = "unidad", "Unidad"
    KILOGRAMO = "kg", "Kilogramo"
    GRAMO = "g", "Gramo"
    LITRO = "l", "Litro"
    MILILITRO = "ml", "Mililitro"
    METRO = "m", "Metro"


class Producto(models.Model):
    """
    Una ficha del catálogo de la empresa. Compartida por todos sus locales.

    Ojo con los dos campos de vencimiento del sistema, que suenan igual:
      - `controla_vencimiento` (acá): ¿esta COSA vence? La leche sí, el
        detergente no. No cambia nunca.
      - `fecha_vencimiento` (en Lote): ¿cuándo vence ESTE envase que tengo?
        Del mismo producto puedo tener tres tandas con tres fechas distintas.
    La regla va arriba, el dato va abajo.
    """

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="productos",
        verbose_name="empresa",
    )

    nombre = models.CharField("nombre", max_length=255)
    descripcion = models.TextField("descripción", blank=True)

    unidad_medida = models.CharField(
        "unidad de medida",
        max_length=10,
        choices=UnidadMedida.choices,
        default=UnidadMedida.UNIDAD,
    )

    controla_vencimiento = models.BooleanField(
        "controla vencimiento",
        default=False,
        help_text="¿Este producto vence? Es una característica del producto, no del rubro.",
    )
    controla_lote = models.BooleanField(
        "controla lote",
        default=False,
        help_text="¿Se numera cada tanda recibida? El jamón tiene fecha pero puede no tener lote.",
    )

    # --- Fraccionamiento por conversión ------------------------------------
    # Una caja de 30 unidades y la unidad suelta son DOS productos distintos
    # con dos códigos distintos. `producto_padre` los vincula para que abrir
    # una caja sea un solo acto: -1 caja, +30 unidades.
    producto_padre = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fracciones",
        verbose_name="producto padre",
        help_text="Producto del que este sale al fraccionar. Ej: la caja de 30.",
    )
    factor_conversion = models.DecimalField(
        "factor de conversión",
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Cuántas unidades de este producto salen de una del padre. Ej: 30.",
    )

    activo = models.BooleanField("activo", default=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["nombre"]
        indexes = [
            # El buscador por nombre dentro de una empresa.
            models.Index(fields=["empresa", "nombre"], name="prod_empresa_nombre_idx"),
        ]
        constraints = [
            # Si hay padre tiene que haber factor, y al revés. Uno sin el otro
            # es un dato a medias que rompe el fraccionamiento en silencio.
            models.CheckConstraint(
                condition=(
                    models.Q(producto_padre__isnull=True, factor_conversion__isnull=True)
                    | models.Q(producto_padre__isnull=False, factor_conversion__isnull=False)
                ),
                name="producto_padre_y_factor_juntos",
            ),
        ]

    def __str__(self):
        return self.nombre


class CodigoBarra(models.Model):
    """
    Los códigos con los que se escanea un producto. Uno a muchos: una ficha
    puede tener varios códigos legítimos al mismo tiempo.

    Casos que resuelve:
      - El laboratorio cambia el código → se agrega el nuevo a la MISMA ficha.
      - Códigos internos que crea el usuario para unidades fraccionadas.
      - Un producto que viene con dos códigos de fábrica.

    Un código viejo se DESACTIVA, no se borra: el historial de ventas tiene
    que seguir explicándose.

    Códigos internos: deben empezar con 2. El estándar EAN-13 reserva ese
    prefijo para uso interno de cada tienda, así que nunca chocan con uno real.
    """

    # `empresa` está denormalizado A PROPÓSITO (también está en producto).
    # Motivo: esta es la consulta más caliente del sistema — cada escaneo de
    # pistola. Con empresa acá se resuelve con una búsqueda directa al índice,
    # sin pasar por la tabla de productos.
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="codigos_barra",
        verbose_name="empresa",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,  # sin producto, el código no significa nada
        related_name="codigos",
        verbose_name="producto",
    )

    codigo = models.CharField("código", max_length=50)
    principal = models.BooleanField(
        "principal",
        default=False,
        help_text="El que se muestra en la ficha. Solo uno por producto.",
    )
    activo = models.BooleanField("activo", default=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "código de barra"
        verbose_name_plural = "códigos de barra"
        ordering = ["-principal", "codigo"]
        constraints = [
            # Dentro de una empresa, un código apunta a un solo producto.
            # Esto es lo que hace que escanear sea determinista.
            models.UniqueConstraint(
                fields=["empresa", "codigo"],
                name="codigo_unico_por_empresa",
            ),
            # Un solo código principal por producto. `condition` hace que la
            # regla aplique solo a las filas con principal=True.
            models.UniqueConstraint(
                fields=["producto"],
                condition=models.Q(principal=True),
                name="un_solo_codigo_principal_por_producto",
            ),
        ]

    def __str__(self):
        return self.codigo


