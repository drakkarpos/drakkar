"""
Tests de Producto y CodigoBarra.

Ver empresas/tests.py para la explicación de cómo funciona un test.

    python manage.py test productos
"""

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from empresas.models import Empresa
from .models import CodigoBarra, Producto, UnidadMedida


class CodigoBarraTest(TestCase):
    """
    La identidad del producto es su `id` interno, NO su código de barra (D-4.2).

    Estos tests protegen la consulta más caliente del sistema: cada escaneo
    de pistola busca por (empresa, codigo).
    """

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Mariamarket", rut="76.111.111-1", razon_social="Maria SpA"
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa, nombre="Leche 1L"
        )

    def test_un_codigo_no_se_repite_dentro_de_una_empresa(self):
        """
        Esto es lo que hace que escanear sea determinista: un código, un producto.
        Si se repitiera, el sistema no sabría cuál cobrar.
        """
        CodigoBarra.objects.create(
            empresa=self.empresa, producto=self.producto, codigo="7801234567890"
        )

        otro = Producto.objects.create(empresa=self.empresa, nombre="Leche 2L")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CodigoBarra.objects.create(
                    empresa=self.empresa, producto=otro, codigo="7801234567890"
                )

    def test_dos_empresas_si_pueden_usar_el_mismo_codigo(self):
        """
        Dos farmacias distintas venden el mismo producto con el mismo código
        de fábrica. La unicidad es POR empresa.
        """
        otra = Empresa.objects.create(
            nombre="Otro Market", rut="77.222.222-2", razon_social="Otro SpA"
        )
        producto_otra = Producto.objects.create(empresa=otra, nombre="Leche 1L")

        CodigoBarra.objects.create(
            empresa=self.empresa, producto=self.producto, codigo="7801234567890"
        )
        CodigoBarra.objects.create(
            empresa=otra, producto=producto_otra, codigo="7801234567890"
        )

        self.assertEqual(CodigoBarra.objects.filter(codigo="7801234567890").count(), 2)

    def test_un_producto_tiene_un_solo_codigo_principal(self):
        """El principal es el que se muestra en la ficha: no puede haber dos."""
        CodigoBarra.objects.create(
            empresa=self.empresa, producto=self.producto,
            codigo="7801234567890", principal=True,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CodigoBarra.objects.create(
                    empresa=self.empresa, producto=self.producto,
                    codigo="7809999999999", principal=True,
                )

    def test_un_producto_puede_tener_varios_codigos_no_principales(self):
        """
        El caso real: el laboratorio cambia el código y se agrega el nuevo a la
        MISMA ficha, para no partir el historial en dos productos (D-4.2).
        """
        CodigoBarra.objects.create(
            empresa=self.empresa, producto=self.producto,
            codigo="7801234567890", principal=True,
        )
        CodigoBarra.objects.create(
            empresa=self.empresa, producto=self.producto, codigo="7809999999999"
        )
        CodigoBarra.objects.create(
            empresa=self.empresa, producto=self.producto, codigo="2000000000015"
        )

        self.assertEqual(self.producto.codigos.count(), 3)

    def test_el_codigo_viejo_se_desactiva_no_se_borra(self):
        """
        Un código dado de baja sigue existiendo: el historial de ventas tiene
        que poder explicarse. Solo deja de estar activo.
        """
        viejo = CodigoBarra.objects.create(
            empresa=self.empresa, producto=self.producto, codigo="7801234567890"
        )
        viejo.activo = False
        viejo.save()

        self.assertEqual(self.producto.codigos.count(), 1)
        self.assertEqual(self.producto.codigos.filter(activo=True).count(), 0)


class FraccionamientoTest(TestCase):
    """
    Producto padre y factor de conversión van juntos o ninguno.

    Uno sin el otro es un dato a medias: el sistema sabría que la unidad sale
    de la caja, pero no cuántas salen. El fraccionamiento fallaría en silencio.
    """

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Mariamarket", rut="76.111.111-1", razon_social="Maria SpA"
        )
        self.caja = Producto.objects.create(
            empresa=self.empresa, nombre="Caja de leche x30"
        )

    def test_no_se_puede_tener_padre_sin_factor(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Producto.objects.create(
                    empresa=self.empresa, nombre="Leche suelta",
                    producto_padre=self.caja,
                )

    def test_no_se_puede_tener_factor_sin_padre(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Producto.objects.create(
                    empresa=self.empresa, nombre="Leche suelta",
                    factor_conversion=Decimal("30"),
                )

    def test_los_dos_juntos_funcionan(self):
        unidad = Producto.objects.create(
            empresa=self.empresa, nombre="Leche 1L",
            producto_padre=self.caja, factor_conversion=Decimal("30"),
        )

        self.assertEqual(unidad.producto_padre, self.caja)
        self.assertEqual(self.caja.fracciones.count(), 1)

    def test_un_producto_normal_no_necesita_ninguno(self):
        """La mayoría de los productos no se fraccionan. Ninguno de los dos campos."""
        normal = Producto.objects.create(
            empresa=self.empresa, nombre="Detergente", unidad_medida=UnidadMedida.UNIDAD
        )

        self.assertIsNone(normal.producto_padre)
        self.assertIsNone(normal.factor_conversion)
