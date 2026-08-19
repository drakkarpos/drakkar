# Día 4 — Diseño de datos: productos, stock y lotes

Documento de trabajo. Guardar en `C:\drakkar\` junto a `DECISIONES.md`.

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

## 7. Decisiones pendientes

- [ ] Precio base de la suscripción y precio del usuario adicional
- [ ] Tramos de descuento por cantidad de locales (marginales, nunca sobre el total)
- [ ] Proveedor de DTE a integrar — probar OpenFactura contra su ambiente de pruebas
- [ ] Consultar a Mercado Pago si existe API de boletas para integradores
- [ ] Dominio raíz
- [ ] Qué pasa cuando el stock cae bajo el mínimo: ¿solo alerta o lista de reposición?
