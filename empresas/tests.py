"""
Tests de Empresa y Local.

QUÉ ES ESTO
Cada método que empieza con `test_` es una prueba. Django las busca solas,
las corre, y dice cuáles pasaron.

Antes de correr las pruebas, Django crea una base de datos NUEVA y VACÍA
(se llama test_drakkar_dev), y al terminar la borra. Tu base de desarrollo
no se toca nunca. Por eso los tests pueden crear y romper lo que quieran.

CÓMO CORRERLOS
    python manage.py test empresas       (solo esta app)
    python manage.py test                (todo el proyecto)

CÓMO SE LEE UN TEST
    setUp()     → se ejecuta ANTES de cada prueba, para dejar el escenario listo
    test_algo() → una prueba: una situación, una comprobación
    assert...   → la comprobación. Si no se cumple, el test falla
"""

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from .models import Empresa, Local


class LocalConstraintsTest(TestCase):
    """
    Las reglas que la BASE DE DATOS debe hacer cumplir.

    No probamos el formulario: probamos que la base se niegue, porque los datos
    también entran por el admin, por scripts y por el import de Excel (D-012).
    """

    def setUp(self):
        """Una empresa base para todas las pruebas de esta clase."""
        self.empresa = Empresa.objects.create(
            nombre="Mariamarket",
            rut="76.111.111-1",
            razon_social="Maria SpA",
        )

    def test_no_se_pueden_manejar_lotes_sin_vencimiento(self):
        """
        Regla: maneja_lotes=True exige maneja_vencimiento=True.

        `assertRaises` dice: "lo de adentro TIENE que fallar con este error".
        Si no falla, el test falla — que es lo que queremos detectar.

        El `transaction.atomic()` es necesario: en PostgreSQL, un error deja la
        transacción rota, y sin envolverlo no se podría seguir usando la base
        después. Es un detalle técnico, no una regla de negocio.
        """
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Local.objects.create(
                    empresa=self.empresa,
                    nombre="Sur",
                    slug="sur",
                    maneja_vencimiento=False,
                    maneja_lotes=True,
                )

    def test_si_se_pueden_manejar_lotes_con_vencimiento(self):
        """
        El lado positivo de la regla anterior.

        Tan importante como el test que falla: una constraint mal escrita puede
        bloquear TODO, incluido lo válido. Sin este test, no nos enteraríamos.
        """
        local = Local.objects.create(
            empresa=self.empresa,
            nombre="Centro",
            slug="centro",
            maneja_vencimiento=True,
            maneja_lotes=True,
        )
        self.assertTrue(local.maneja_lotes)

    def test_dos_locales_de_la_misma_empresa_no_pueden_llamarse_igual(self):
        Local.objects.create(empresa=self.empresa, nombre="Centro", slug="centro-1")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Local.objects.create(empresa=self.empresa, nombre="Centro", slug="centro-2")

    def test_dos_empresas_distintas_si_pueden_tener_un_local_con_el_mismo_nombre(self):
        """
        "Sucursal Centro" es un nombre común. La unicidad es POR empresa,
        no global — solo el slug (la URL) es único en todo el sistema.
        """
        otra = Empresa.objects.create(
            nombre="Otro Market", rut="77.222.222-2", razon_social="Otro SpA"
        )
        Local.objects.create(empresa=self.empresa, nombre="Centro", slug="mariamarket-centro")
        local2 = Local.objects.create(empresa=otra, nombre="Centro", slug="otro-centro")

        self.assertEqual(Local.objects.filter(nombre="Centro").count(), 2)
        self.assertEqual(local2.empresa, otra)

    def test_el_slug_es_unico_en_todo_el_sistema(self):
        """El slug va en la URL: si se repitiera, dos locales competirían por ella."""
        otra = Empresa.objects.create(
            nombre="Otro Market", rut="77.333.333-3", razon_social="Otro SpA"
        )
        Local.objects.create(empresa=self.empresa, nombre="Centro", slug="centro")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Local.objects.create(empresa=otra, nombre="Norte", slug="centro")


class ProteccionAlBorrarTest(TestCase):
    """
    on_delete=PROTECT: la base se niega a dejar huérfanos.

    Es coherente con D-003: acá no se borra, se desactiva.
    """

    def setUp(self):
        self.empresa = Empresa.objects.create(
            nombre="Mariamarket", rut="76.111.111-1", razon_social="Maria SpA"
        )
        self.local = Local.objects.create(
            empresa=self.empresa, nombre="Centro", slug="centro"
        )

    def test_no_se_puede_borrar_una_empresa_con_locales(self):
        with self.assertRaises(ProtectedError):
            self.empresa.delete()

    def test_si_se_puede_borrar_una_empresa_sin_locales(self):
        """Para limpiar hay que ir de abajo hacia arriba: hijos primero."""
        self.local.delete()
        self.empresa.delete()

        self.assertEqual(Empresa.objects.count(), 0)
