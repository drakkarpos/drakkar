"""
Tests de ProductoLocal y Lote.

Acá están los dos tests más importantes del proyecto hasta ahora:
el ORDEN FEFO y el STOCK TOTAL. Son las reglas que sostienen la venta.

Ver empresas/tests.py para la explicación de cómo funciona un test.

    python manage.py test stock
"""

from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.test import TestCase

from empresas.models import Empresa, Local
from productos.models import Producto
from .models import Lote, ProductoLocal


class BaseStockTest(TestCase):
    """
    Escenario compartido: una empresa, un local, un producto que vence.

    Heredar de esta clase evita repetir el mismo setUp en cada grupo de pruebas.
    """

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Mariamarket", rut="76.111.111-1", razon_social="Maria SpA"
        )
        self.local = Local.objects.create(
            empresa=self.empresa, nombre="Centro", slug="centro",
            maneja_vencimiento=True,
        )
        self.producto = Producto.objects.create(
            empresa=self.empresa, nombre="Leche 1L", controla_vencimiento=True
        )
        self.producto_local = ProductoLocal.objects.create(
            producto=self.producto, local=self.local,
            precio=Decimal("1290"), stock_minimo=Decimal("5"),
        )


class ProductoLocalTest(BaseStockTest):

    def test_un_producto_solo_una_vez_por_local(self):
        """Si se repitiera, el mismo producto tendría dos precios en el mismo local."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductoLocal.objects.create(
                    producto=self.producto, local=self.local, precio=Decimal("1500")
                )

    def test_el_mismo_producto_puede_estar_en_varios_locales_con_distinto_precio(self):
        """
        Lo único compartido entre locales es la IDENTIDAD del producto.
        El precio y el stock son de cada local (D-4.3).
        """
        otro_local = Local.objects.create(
            empresa=self.empresa, nombre="Norte", slug="norte"
        )
        pl2 = ProductoLocal.objects.create(
            producto=self.producto, local=otro_local, precio=Decimal("1350")
        )

        self.assertEqual(self.producto.en_locales.count(), 2)
        self.assertNotEqual(self.producto_local.precio, pl2.precio)


class FefoTest(BaseStockTest):
    """
    FEFO: First Expired, First Out. Se vende primero lo que vence antes.

    Es la regla de negocio más delicada del sistema: si se rompe, la mercadería
    vence en la góndola y el cliente pierde plata sin entender por qué.
    """

    def test_los_lotes_salen_ordenados_por_vencimiento(self):
        """
        Se crean DESORDENADOS a propósito. El orden tiene que venir del modelo
        (Meta.ordering), no del orden en que se guardaron.
        """
        Lote.objects.create(
            producto_local=self.producto_local, cantidad=Decimal("6"),
            fecha_vencimiento=date(2026, 12, 20),
        )
        Lote.objects.create(
            producto_local=self.producto_local, cantidad=Decimal("4"),
            fecha_vencimiento=date(2026, 12, 2),
        )
        Lote.objects.create(
            producto_local=self.producto_local, cantidad=Decimal("8"),
            fecha_vencimiento=date(2026, 12, 10),
        )

        fechas = [lote.fecha_vencimiento for lote in self.producto_local.lotes.all()]

        self.assertEqual(
            fechas,
            [date(2026, 12, 2), date(2026, 12, 10), date(2026, 12, 20)],
        )

    def test_los_lotes_sin_fecha_van_al_FINAL(self):
        """
        EL TEST MÁS IMPORTANTE DE ESTE ARCHIVO.

        Un lote sin fecha significa "no vence", no "vence ya". Si quedara
        primero, el sistema vendería primero lo que no tiene ninguna urgencia
        y dejaría vencer lo demás.

        En SQL un valor nulo no es cero ni infinito: el motor decide dónde
        ponerlo. Por eso el modelo lo declara explícitamente con nulls_last.
        """
        Lote.objects.create(producto_local=self.producto_local, cantidad=Decimal("2"))
        Lote.objects.create(
            producto_local=self.producto_local, cantidad=Decimal("6"),
            fecha_vencimiento=date(2026, 12, 20),
        )
        Lote.objects.create(
            producto_local=self.producto_local, cantidad=Decimal("4"),
            fecha_vencimiento=date(2026, 12, 2),
        )

        lotes = list(self.producto_local.lotes.all())

        self.assertEqual(lotes[0].fecha_vencimiento, date(2026, 12, 2))
        self.assertEqual(lotes[1].fecha_vencimiento, date(2026, 12, 20))
        self.assertIsNone(lotes[2].fecha_vencimiento)

    def test_el_primero_de_la_lista_es_el_que_se_vende(self):
        """
        Así se va a usar el FEFO al vender: `.first()` sobre los lotes con stock.
        Este test fija ese contrato antes de que exista el código de ventas.
        """
        Lote.objects.create(
            producto_local=self.producto_local, cantidad=Decimal("6"),
            fecha_vencimiento=date(2026, 12, 20),
        )
        urgente = Lote.objects.create(
            producto_local=self.producto_local, cantidad=Decimal("4"),
            fecha_vencimiento=date(2026, 12, 2),
        )

        primero = self.producto_local.lotes.filter(
            activo=True, cantidad__gt=0
        ).first()

        self.assertEqual(primero, urgente)


class StockTotalTest(BaseStockTest):
    """
    El stock NO es un campo: es la suma de los lotes activos (D-4.1).

    Un número guardado en dos lugares tarde o temprano deja de coincidir
    consigo mismo, y no hay forma de saber cuál tiene razón.
    """

    def _stock(self):
        """La consulta real: suma en la BASE, no recorriendo listas en Python."""
        return self.producto_local.lotes.filter(activo=True).aggregate(
            total=Sum("cantidad")
        )["total"]

    def test_el_stock_es_la_suma_de_los_lotes(self):
        Lote.objects.create(producto_local=self.producto_local, cantidad=Decimal("6"))
        Lote.objects.create(producto_local=self.producto_local, cantidad=Decimal("4"))
        Lote.objects.create(producto_local=self.producto_local, cantidad=Decimal("2"))

        self.assertEqual(self._stock(), Decimal("12"))

    def test_los_lotes_inactivos_no_cuentan_como_stock(self):
        """
        Un lote dado de baja (vencido, mermado) sigue existiendo para el
        historial, pero NO es stock disponible.
        """
        Lote.objects.create(producto_local=self.producto_local, cantidad=Decimal("6"))
        Lote.objects.create(
            producto_local=self.producto_local, cantidad=Decimal("100"), activo=False
        )

        self.assertEqual(self._stock(), Decimal("6"))

    def test_sin_lotes_el_stock_es_nulo_no_cero(self):
        """
        Detalle real que muerde: Sum() sobre una tabla vacía devuelve None, no 0.
        Quien use este cálculo tiene que contemplarlo (`or 0`), como hace el admin.
        """
        self.assertIsNone(self._stock())

    def test_se_detecta_cuando_el_stock_cae_bajo_el_minimo(self):
        """El stock_minimo del producto en este local es 5."""
        Lote.objects.create(producto_local=self.producto_local, cantidad=Decimal("3"))

        self.assertLess(self._stock(), self.producto_local.stock_minimo)

    def test_las_cantidades_guardan_decimales(self):
        """
        Venta por peso: 1,250 kg tiene que guardarse tal cual.
        Que se muestren o no los decimales lo decide la pantalla, no la base.
        """
        lote = Lote.objects.create(
            producto_local=self.producto_local, cantidad=Decimal("1.250")
        )
        lote.refresh_from_db()

        self.assertEqual(lote.cantidad, Decimal("1.250"))


class IndiceVencimientosTest(BaseStockTest):
    """
    El reporte "qué vence en N días", que cruza todos los locales.

    Se apoya en el índice parcial lote_venc_activos_idx: solo lotes activos
    con cantidad > 0.
    """

    def test_el_reporte_solo_trae_lotes_con_stock_y_activos(self):
        vence_pronto = Lote.objects.create(
            producto_local=self.producto_local, cantidad=Decimal("5"),
            fecha_vencimiento=date(2026, 12, 2),
        )
        # Agotado: ya no importa que venza
        Lote.objects.create(
            producto_local=self.producto_local, cantidad=Decimal("0"),
            fecha_vencimiento=date(2026, 12, 1),
        )
        # Dado de baja: tampoco
        Lote.objects.create(
            producto_local=self.producto_local, cantidad=Decimal("9"),
            fecha_vencimiento=date(2026, 12, 3), activo=False,
        )

        por_vencer = Lote.objects.filter(
            activo=True,
            cantidad__gt=0,
            fecha_vencimiento__lte=date(2026, 12, 31),
        )

        self.assertEqual(list(por_vencer), [vence_pronto])

    def test_los_lotes_sin_fecha_no_aparecen_en_el_reporte(self):
        """`fecha_vencimiento__lte` excluye los nulos solo: no vencen nunca."""
        Lote.objects.create(producto_local=self.producto_local, cantidad=Decimal("5"))

        por_vencer = Lote.objects.filter(
            activo=True, cantidad__gt=0, fecha_vencimiento__lte=date(2026, 12, 31)
        )

        self.assertEqual(por_vencer.count(), 0)
