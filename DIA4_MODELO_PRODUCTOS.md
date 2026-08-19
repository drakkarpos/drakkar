# Día 4 — Diseño de datos: productos, stock y lotes

Documento de trabajo. Guardar en `C:\drakkar\` junto a `DECISIONES.md`.

**Estado:** modelos escritos, migrados y verificados en `drakkar_dev` (2026-08-19).

---

## 1. Decisiones que sostienen este diseño

| # | Decisión | Motivo |
|---|---|---|
| 1 | El stock **no** es un campo de `Producto`: vive en los lotes | Permite total y desglose, y evita desincronización |
| 2 | El código de barras **no** identifica al producto | Los laboratorios cambian códigos; el historial no puede romperse |
| 3 | Catálogo por **empresa**, precio y stock por **local** | Habilita traspaso, consulta entre locales y reportes consolidados |
| 4 | Vencimiento es atributo del **producto**, no del rubro | En un minimarket la leche vence y el detergente no |
| 5 | Lote y vencimiento son campos **separados y opcionales** | El jamón tiene fecha pero puede no tener lote |
| 6 | Cantidades con **decimales** siempre | Venta por peso; la interfaz decide si los muestra |
| 7 | El campo `local` existe desde el día uno | Agregarlo después es la migración más cara del proyecto |

---

## 2. Estructura general

```
Empresa (el cliente)
   └── Local (paga suscripción, tiene stock propio)
         └── ProductoLocal (precio, stock mínimo)
               └── Lote (cantidad, vencimiento, precio oferta)

Producto (catálogo de la empresa)
   └── CodigoBarra (uno a muchos)
```

---

## 3. Modelos

### Empresa

| Campo | Tipo | Notas |
|---|---|---|
| `nombre` | CharField(200) | |
| `rut` | CharField(20) | único |
| `razon_social` | CharField(255) | |
| `giro` | CharField(255) | |
| `activo` | Boolean | |
| `creado_en` | DateTime | |

### Local

| Campo | Tipo | Notas |
|---|---|---|
| `empresa` | FK → Empresa | `related_name='locales'` |
| `nombre` | CharField(150) | |
| `direccion` | CharField(255) | |
| `slug` | SlugField(60) | único en todo el sistema — es la URL (ver §8.1) |
| `activo` | Boolean | |
| **Configuración operativa** | | |
| `maneja_vencimiento` | Boolean | si está en False, el tema no aparece en ninguna pantalla |
| `maneja_lotes` | Boolean | requiere `maneja_vencimiento` |
| `venta_por_medida` | Boolean | habilita unidades distintas de "unidad" |
| `permite_traspasos` | Boolean | solo tiene sentido con 2+ locales |
| `consulta_stock_otros_locales` | Boolean | apagado por defecto |
| `dias_alerta_vencimiento` | PositiveInteger | por defecto 30; en días, no en meses |

> Estos switches los controla el **admin del cliente**: afectan cómo trabaja, no lo que paga.
> Los que definen qué módulos tiene contratados los controla el superusuario y viven en la suscripción.

### Producto — catálogo de la empresa

| Campo | Tipo | Notas |
|---|---|---|
| `empresa` | FK → Empresa | |
| `nombre` | CharField(255) | |
| `descripcion` | TextField | opcional |
| `unidad_medida` | CharField(choices) | unidad / kg / g / l / ml / m |
| `controla_vencimiento` | Boolean | por defecto según perfil de rubro |
| `controla_lote` | Boolean | |
| `producto_padre` | FK → Producto (null) | para fraccionamiento por conversión |
| `factor_conversion` | Decimal(12,3) (null) | 1 caja = 30 unidades |
| `activo` | Boolean | |
| `creado_en` / `actualizado_en` | DateTime | |

**Identidad:** el `id` interno. Nunca cambia, nunca lo ve el usuario, y de él cuelga todo el historial.

**Cuidado con los dos campos que suenan igual:**

- `controla_vencimiento` (en `Producto`): ¿esta **cosa** vence? La leche sí, el
  detergente no. No cambia nunca.
- `fecha_vencimiento` (en `Lote`): ¿cuándo vence **este envase** que tengo? Del
  mismo producto puedo tener tres tandas con tres fechas distintas.

La regla va arriba, el dato va abajo.

### CodigoBarra

| Campo | Tipo | Notas |
|---|---|---|
| `empresa` | FK → Empresa | **denormalizado a propósito** — ver índices |
| `producto` | FK → Producto | `related_name='codigos'` |
| `codigo` | CharField(50) | |
| `principal` | Boolean | el que se muestra en la ficha |
| `activo` | Boolean | un código viejo se desactiva, no se borra |
| `creado_en` | DateTime | |

Restricción: `unique_together = ('empresa', 'codigo')`

Casos que resuelve:
- El laboratorio cambia el código → se agrega el nuevo a la misma ficha
- Códigos internos creados por el usuario (unidades fraccionadas)
- Un producto con varios códigos legítimos simultáneos

**Códigos internos:** deben empezar con `2`. El estándar EAN-13 reserva ese prefijo
para uso interno de cada tienda, así que nunca chocan con un producto real.

### ProductoLocal — qué maneja cada local

| Campo | Tipo | Notas |
|---|---|---|
| `producto` | FK → Producto | |
| `local` | FK → Local | |
| `precio` | Decimal(12,2) | precio por unidad de medida |
| `stock_minimo` | Decimal(12,3) | se compara contra la suma de todos los lotes |
| `dias_alerta_vencimiento` | PositiveInteger (null) | si es null, usa el del local |
| `activo` | Boolean | permite dejar de manejar un producto sin borrar historia |

Restricción: `unique_together = ('producto', 'local')`

> Cada local ve solo su lista, su precio y su stock. Lo único compartido es la
> **identidad** del producto.

### Lote — donde vive el stock

| Campo | Tipo | Notas |
|---|---|---|
| `producto_local` | FK → ProductoLocal | `related_name='lotes'` |
| `numero` | CharField(50), blank | opcional |
| `fecha_vencimiento` | Date (null) | opcional |
| `cantidad` | Decimal(12,3) | |
| `precio_oferta` | Decimal(12,2) (null) | para liquidar lo que vence pronto |
| `activo` | Boolean | |
| `creado_en` | DateTime | |

Cuando el local no maneja lotes, el sistema crea **un lote implícito** por producto,
sin número ni fecha. El usuario nunca sabe que existe.

> **Por qué:** si el stock viviera en `Producto` con lotes apagados y en `Lote` con
> lotes prendidos, habría dos caminos en el código para vender, ajustar, inventariar
> y reportar. Un solo camino, con la diferencia solo en la interfaz.

**Stock total** = suma de `cantidad` de los lotes activos. No es un campo: es un cálculo.

---

## 4. Índices — pensados para las consultas reales

| Índice | Para qué |
|---|---|
| `CodigoBarra (empresa, codigo)` único | **La consulta más caliente del sistema.** Cada escaneo de pistola. Por eso `empresa` va denormalizado: resuelve en una búsqueda directa, sin joins |
| `ProductoLocal (local, activo)` | Listar el catálogo de un local |
| `Lote (producto_local, fecha_vencimiento)` | FEFO al vender y alertas de vencimiento |
| `Producto (empresa, nombre)` | Buscador por nombre |
| `Lote (fecha_vencimiento)` parcial, solo activos | Reporte "qué vence en N días" en todos los locales |

Regla del proyecto: **agregar en la base, no en Python.** Los totales se calculan
con `Sum()` y `annotate()`, nunca recorriendo listas.

---

## 5. Reglas de negocio que el modelo debe sostener

**Venta y FEFO.** Al vender se descuenta del lote que vence primero. Si el cliente
lleva 5 y solo 3 están en el lote en oferta, la venta se parte en dos líneas con
precios distintos. Por eso cada línea de venta guarda **producto + lote + cantidad +
precio aplicado**: es la única forma honesta, y da trazabilidad total por lote.

**Código desconocido.** Al escanear algo no registrado, el sistema pregunta:

```
Código 6786869 no registrado.
  ¿Producto nuevo?                        → crear ficha
  ¿Otro código de un producto existente?  → buscar y asociar
```

Sin esa segunda opción, quien recibe mercadería crea productos duplicados porque
es el camino fácil.

**Fraccionamiento por conversión.** Un ajuste con dos efectos en un solo acto:
descuenta 1 de la caja y suma 30 a la unidad. No son dos registros sueltos.

**Venta a granel.** Es el mismo producto vendido en fracciones de su unidad de
medida. No hay conversión ni producto nuevo.

**Formato en pantalla.** La unidad de medida decide cómo se muestra el número:
`unidad` → sin decimales; `kg` → con decimales. En un local con `venta_por_medida`
apagado nunca aparece un decimal, aunque la base guarde `1,000`.

---

## 6. Perfiles de rubro

Son combinaciones de los mismos switches genéricos. **No hay código distinto por rubro.**

| Perfil | Vencimiento | Lotes | Venta por medida |
|---|---|---|---|
| Farmacia | Sí | Sí | No |
| Minimarket | Sí | No | Sí |
| Ferretería | No | No | Sí |
| Ropa | No | No | No |
| Genérico ("Otro") | Sí | Sí | Sí |

El perfil define **valores por defecto** al crear el local y los productos. El cliente
puede cambiar cualquier switch después.

> Escribir código específico por rubro obliga a probar cada cambio N veces y hace
> que cada error aparezca en un solo tipo de cliente. Con una sola desarrolladora,
> el techo llega rápido.
>
> **Regla:** configuración primero, módulo opcional cuando la configuración no
> alcanza, código a medida nunca.

---

## 7. Reparto en apps de Django

| App | Modelos | Qué responde |
|---|---|---|
| `usuarios` | `Usuario` | quién entra al sistema |
| `empresas` | `Empresa`, `Local` | quién es el cliente y dónde trabaja |
| `productos` | `Producto`, `CodigoBarra` | qué cosas conoce la empresa |
| `stock` | `ProductoLocal`, `Lote` | cuánto hay, dónde y a qué precio |

**Por qué `stock` va separado de `productos`:** el nombre de cada carpeta dice
exactamente lo que tiene. Además, cuando lleguen Movimientos (Día 15) y el
submódulo de Diferencias (D-003), esos modelos ya tienen su casa natural y no
hay que volver a discutir dónde van.

`Lote` no es parte de la ficha del producto: es el registro de lo que
físicamente hay en un local. Por eso vive en `stock`.

**`usuarios` existe desde hoy** aunque el Día 9 sea el de usuarios. Ver D-011:
en Django el modelo de usuario se declara antes del primer `migrate`, siempre.

---

## 8. Cambios al pasar de diseño a código

### 8.1 `Local.slug` — campo nuevo

No estaba en la tabla de campos original, pero ARQ-001 lo exige: un local =
una URL (`app.drakkar.cl/mariamarket1`). El slug es único en **todo el
sistema**, no por empresa, porque la URL es global.

### 8.2 `on_delete=PROTECT` como norma

Django obliga a decidir qué pasa con las filas hijas cuando se borra la madre.
La norma del proyecto es `PROTECT`: la base se **niega** a borrar una empresa
con locales, un local con productos o un producto con stock.

Es coherente con D-003: acá no se borra, se desactiva. El único `CASCADE` es
`CodigoBarra` → `Producto`, porque un código sin producto no significa nada.

Consecuencia práctica: para limpiar datos hay que ir de abajo hacia arriba —
lotes, productos-local, productos, locales, empresas.

### 8.3 Reglas de negocio en la base, no solo en el formulario

Un formulario se puede saltar: por el admin de Django, por un script de carga,
por el import de Excel. La base no. Tres reglas quedaron como `constraints`
(ver D-012):

| Constraint | Qué impide |
|---|---|
| `local_lotes_requiere_vencimiento` | manejar lotes con vencimientos apagados |
| `producto_padre_y_factor_juntos` | un producto padre sin factor de conversión (o al revés) |
| `un_solo_codigo_principal_por_producto` | dos códigos principales en la misma ficha |

Más las unicidades ya previstas: `(empresa, codigo)` en `CodigoBarra` y
`(producto, local)` en `ProductoLocal`. Se agregó también `(empresa, nombre)`
único en `Local`.

### 8.4 Orden FEFO explícito, con los sin fecha al final

`Lote.Meta.ordering` usa `fecha_vencimiento` ascendente con `nulls_last=True`.

**Por qué importa:** un lote sin fecha significa "no vence", no "vence ya". Si
quedara primero, el sistema vendería primero lo que no tiene ninguna urgencia y
dejaría vencer lo demás.

### 8.5 El índice de vencimientos es parcial

`lote_venc_activos_idx` indexa solo los lotes con `activo=True` y
`cantidad > 0`. Es el índice del reporte "qué vence en N días". Al año de uso,
la mayoría de los lotes van a estar agotados: no tiene sentido que el índice
cargue con ellos.

---

## 9. Verificación hecha

Cargando datos de ejemplo en `drakkar_dev`, la base rechazó las cinco
operaciones que debía rechazar:

- local con lotes y sin vencimientos
- código de barra repetido dentro de la misma empresa
- segundo código principal en un producto
- el mismo producto dos veces en el mismo local
- producto con padre pero sin factor de conversión

Y se comprobó lo que debía funcionar:

- stock total calculado con `Sum()` **en la base**, no recorriendo listas
- orden FEFO correcto, con el lote sin fecha al final
- cantidades guardadas con tres decimales (`4.000`, `6.000`)

Cuando una constraint salta, PostgreSQL informa su **nombre**. Por eso cada una
lleva un nombre descriptivo: dentro de seis meses, ese nombre es toda la pista
disponible para entender qué se rompió.

---

## 10. Pendientes que salieron de este día

- [ ] Crear el lote implícito automáticamente cuando el local no maneja lotes
      (hoy hay que crearlo a mano; corresponde al flujo de ingreso, Día 15)
- [ ] Método o propiedad para el stock total de un `ProductoLocal`
- [ ] Validar que los códigos internos empiecen con `2`
- [ ] Registrar las apps en el admin de Django (Día 13)
- [ ] Tests automáticos de estas reglas (Día 6)

---

## 11. Decisiones pendientes (de negocio)

- [ ] Precio base de la suscripción y precio del usuario adicional
- [ ] Tramos de descuento por cantidad de locales (marginales, nunca sobre el total)
- [ ] Proveedor de DTE a integrar — probar OpenFactura contra su ambiente de pruebas
- [ ] Consultar a Mercado Pago si existe API de boletas para integradores
- [ ] Dominio raíz
- [ ] Qué pasa cuando el stock cae bajo el mínimo: ¿solo alerta o lista de reposición?
