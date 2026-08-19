"""
Empresa y Local: quién es el cliente y dónde trabaja.

Empresa = el cliente que contrata Drakkar (una razón social).
Local   = cada punto de venta de esa empresa. Es la unidad que paga
          suscripción y la que tiene stock propio.

Regla del proyecto (Día 4, decisión 7): el campo `local` existe desde el día
uno en todo lo que sea stock, precio o venta. Agregarlo después sería la
migración más cara del proyecto.
"""

from django.core.validators import MinValueValidator
from django.db import models


class Empresa(models.Model):
    """El cliente. Dueño del catálogo de productos."""

    nombre = models.CharField("nombre de fantasía", max_length=200)
    rut = models.CharField("RUT", max_length=20, unique=True)
    razon_social = models.CharField("razón social", max_length=255)
    giro = models.CharField("giro", max_length=255, blank=True)

    activo = models.BooleanField("activa", default=True)
    creado_en = models.DateTimeField("creada en", auto_now_add=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Local(models.Model):
    """
    Un punto de venta. Tiene su propio stock, sus propios precios y su propia
    configuración operativa.

    Los switches de abajo los controla el ADMIN DEL CLIENTE: definen cómo
    trabaja este local, no qué le cobramos. Los switches de "qué módulos tiene
    contratados" los controla el superusuario y van a vivir en la suscripción
    (Día 26). Son dos cosas distintas y no se mezclan.
    """

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,  # nunca borrar una empresa con locales
        related_name="locales",
        verbose_name="empresa",
    )
    nombre = models.CharField("nombre", max_length=150)
    direccion = models.CharField("dirección", max_length=255, blank=True)

    # Identificador que aparece en la URL: app.drakkar.cl/<slug>
    # Ver ARQ-001: un local = una URL.
    slug = models.SlugField("identificador en la URL", max_length=60, unique=True)

    activo = models.BooleanField("activo", default=True)
    creado_en = models.DateTimeField("creado en", auto_now_add=True)

    # --- Configuración operativa -------------------------------------------
    # Si un switch está en False, el tema NO aparece en ninguna pantalla.
    # La base igual guarda los campos: apagar un switch oculta, no destruye.

    maneja_vencimiento = models.BooleanField(
        "maneja vencimientos",
        default=True,
        help_text="Si está apagado, las fechas de vencimiento no se piden ni se muestran.",
    )
    maneja_lotes = models.BooleanField(
        "maneja lotes",
        default=False,
        help_text="Requiere que maneje vencimientos. Permite numerar cada tanda recibida.",
    )
    venta_por_medida = models.BooleanField(
        "venta por medida",
        default=False,
        help_text="Habilita unidades distintas de 'unidad' (kg, litro, metro) y decimales en pantalla.",
    )
    permite_traspasos = models.BooleanField(
        "permite traspasos entre locales",
        default=False,
    )
    consulta_stock_otros_locales = models.BooleanField(
        "puede consultar stock de otros locales",
        default=False,
    )
    dias_alerta_vencimiento = models.PositiveIntegerField(
        "días de alerta de vencimiento",
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Con cuántos días de anticipación avisar. En días, no en meses.",
    )

    class Meta:
        verbose_name = "local"
        verbose_name_plural = "locales"
        ordering = ["empresa__nombre", "nombre"]
        constraints = [
            # Dos locales de la misma empresa no pueden llamarse igual.
            # (Locales de empresas distintas sí: "Sucursal Centro" es común.)
            models.UniqueConstraint(
                fields=["empresa", "nombre"],
                name="local_nombre_unico_por_empresa",
            ),
            # Regla de negocio sostenida por la BASE, no solo por el formulario:
            # no se pueden manejar lotes sin manejar vencimientos.
            models.CheckConstraint(
                condition=models.Q(maneja_lotes=False) | models.Q(maneja_vencimiento=True),
                name="local_lotes_requiere_vencimiento",
            ),
        ]

    def __str__(self):
        return f"{self.empresa.nombre} — {self.nombre}"