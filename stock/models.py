"""
El stock: qué hay realmente en cada local, a qué precio y con qué vencimiento.

Dos modelos, dos preguntas distintas:
  ProductoLocal → "¿este local maneja este producto? ¿a cuánto lo vende?"
  Lote          → "¿cuánto hay, y cuándo vence lo que hay?"

Decisión central del Día 4: el stock NO es un campo. El stock es la suma de
los lotes. Un número guardado en dos lugares tarde o temprano deja de coincidir
consigo mismo, y no hay forma de saber cuál de los dos tiene razón.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from empresas.models import Local
from productos.models import Producto


class ProductoLocal(models.Model):
    """
    El puente entre el catálogo (de la empresa) y la realidad (de un local).

    El mismo producto puede costar $1.890 en un local y $1.950 en otro, y un
    local puede directamente no manejarlo. Lo único compartido entre locales
    es la IDENTIDAD del producto.
    """

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="en_locales",
        verbose_name="producto",
    )
    local = models.ForeignKey(
        Local,
        on_delete=models.PROTECT,
        related_name="productos",
        verbose_name="local",
    )

    precio = models.DecimalField(
        "precio",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Precio por unidad de medida del producto.",
    )
    stock_minimo = models.DecimalField(
        "stock mínimo",
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Se compara contra la suma de todos los lotes activos.",
    )

    # Si queda en null, se usa el del local. Permite que un producto crítico
    # avise antes que el resto sin cambiar la configuración general.
    dias_alerta_vencimiento = models.PositiveIntegerField(
        "días de alerta de vencimiento",
        null=True,
        blank=True,
        help_text="Si queda vacío, se usa el configurado en el local.",
    )

    activo = models.BooleanField(
        "activo",
        default=True,
        help_text="Apagarlo deja de mostrar el producto sin borrar su historia.",
    )
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "producto del local"
        verbose_name_plural = "productos del local"
        ordering = ["producto__nombre"]
        indexes = [
            # Listar el catálogo activo de un local: la pantalla más usada.
            models.Index(fields=["local", "activo"], name="prodlocal_local_activo_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["producto", "local"],
                name="un_producto_una_vez_por_local",
            ),
        ]

    def __str__(self):
        return f"{self.producto.nombre} @ {self.local.nombre}"


class Lote(models.Model):
    """
    Una tanda de mercadería. ACÁ vive el stock.

    Cuando el local no maneja lotes, el sistema crea un lote IMPLÍCITO por
    producto: sin número y sin fecha. El usuario nunca sabe que existe.

    Por qué siempre lote, incluso apagado:
    si el stock viviera en ProductoLocal con lotes apagados y en Lote con
    lotes prendidos, habría DOS caminos en el código para vender, ajustar,
    inventariar y reportar. Cada bug habría que arreglarlo dos veces, y cada
    función nueva escribirla dos veces. Un solo camino; la diferencia está
    solo en la interfaz.
    """

    producto_local = models.ForeignKey(
        ProductoLocal,
        on_delete=models.PROTECT,
        related_name="lotes",
        verbose_name="producto del local",
    )

    numero = models.CharField("número de lote", max_length=50, blank=True)
    fecha_vencimiento = models.DateField("fecha de vencimiento", null=True, blank=True)

    cantidad = models.DecimalField(
        "cantidad",
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Siempre con decimales. La interfaz decide si los muestra.",
    )

    precio_oferta = models.DecimalField(
        "precio de oferta",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Para liquidar lo que está por vencer. Si es null, usa el precio normal.",
    )

    activo = models.BooleanField("activo", default=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    class Meta:
        verbose_name = "lote"
        verbose_name_plural = "lotes"
        # FEFO: primero el que vence antes. Los sin fecha van al final
        # (nulls_last), porque "no vence" no es "vence ya".
        ordering = [models.F("fecha_vencimiento").asc(nulls_last=True), "creado_en"]
        indexes = [
            # Vender con FEFO y calcular alertas de un producto.
            models.Index(
                fields=["producto_local", "fecha_vencimiento"],
                name="lote_prodlocal_venc_idx",
            ),
            # Reporte "qué vence en los próximos N días" cruzando todos los
            # locales. Índice PARCIAL: solo indexa los lotes que importan
            # (activos y con stock). Más chico, más rápido de mantener.
            models.Index(
                fields=["fecha_vencimiento"],
                name="lote_venc_activos_idx",
                condition=models.Q(activo=True, cantidad__gt=0),
            ),
        ]

    def __str__(self):
        if self.numero:
            return f"{self.producto_local} — lote {self.numero}"
        if self.fecha_vencimiento:
            return f"{self.producto_local} — vence {self.fecha_vencimiento}"
        return str(self.producto_local)


