# Módulo Farmacia — listado de precios de medicamentos

Documento de diseño. Guardar en `C:\drakkar\` junto a `DECISIONES.md`.

**Fecha:** 2026-08-19
**Estado:** diseñado, sin implementar.

> **Base normativa.** El formato de columnas de este documento está **validado
> por el ISP**. Tres condiciones que definen lo que hay que construir:
>
> - **Se actualiza a diario**, siguiendo el precio. Generar el listado tiene
>   que ser un acto de un clic, no un trámite.
> - **Puede exhibirse en papel o en pantalla.** Las dos salidas son válidas
>   ante la norma: la pantalla no es un lujo.
> - La información de la ficha no cambia. Lo único que cambia es el precio —
>   y con él, el precio por unidad, que se recalcula solo.

---

## 1. El problema

Las farmacias en Chile —y solo las farmacias— deben mantener un listado de
precios de todos sus medicamentos. El listado abarca lo que se catalogue como:

- Medicamentos
- Suplementos alimenticios
- Productos naturales
- Medicamentos veterinarios

Nada más. Perfumería, higiene y accesorios quedan fuera.

Formato objetivo (una fila por producto):

| Principio Activo | Dosis | Nombre | Laboratorio | Presentación | Precio Venta | Precio por Unidad | Bioequivalente |
|---|---|---|---|---|---|---|---|
| ACENOCUMAROL | 4 MG | ISQUELIUM 4 MG X 30 COM | SYNTHON | 30 COMPRIMIDOS | 8990 | 233 | Si |
| ACIDO ACETILSALICILICO | 500 MG | ASPIRINA 500 MG X 20 COM | BAYER | 20 COMPRIMIDOS | 1800 | 90 | REFERENTE |

---

## 2. Tres observaciones que definen el modelo

### 2.1 "Bioequivalente" tiene tres estados, no dos

En la planilla real aparecen `Si`, `No` y `REFERENTE`. Un referente no es "no
bioequivalente": es el producto original contra el cual se comparan los demás.
Modelado como booleano, ese tercer estado se pierde y el listado sale mal.

→ Campo con tres opciones, no un checkbox.

### 2.2 "Presentación" es un campo compuesto

`21` + `comprimidos` → "21 COMPRIMIDOS". Se guarda **separado** y se muestra
**junto**.

Si se guardara como texto libre convivirían "30 COMPRIMIDOS", "30 comp." y
"30 Comprimidos", y el precio por unidad dejaría de poder calcularse.

### 2.3 "Precio por Unidad" es un cálculo, no un dato

Es la misma regla que ya rige el stock: **un valor derivado no se guarda.** El
día que alguien cambie el precio y se olvide de recalcularlo, la planilla queda
mintiendo — y es una planilla fiscalizable.

| Forma farmacéutica | Cálculo | Verificación con datos reales |
|---|---|---|
| Contable (comprimidos, cápsulas) | precio ÷ cantidad | 8990 ÷ 30 = 233 ✓ |
| Medible (ml, gramos) | precio ÷ cantidad × 100 | crema 15 g → precio por 100 g |

El precio por unidad de una crema o jarabe se expresa **por cada 100 g o 100 ml**,
no por gramo. Por eso la forma farmacéutica tiene que saber a qué familia
pertenece: es lo que decide la fórmula.

---

## 3. La separación que ya existe y acá se paga sola

La ficha farmacéutica —principio activo, laboratorio, presentación,
bioequivalencia— **nunca cambia**, y es idéntica en todas las farmacias del
país. El precio cambia, y es distinto en cada local.

Eso ya está separado en el modelo del Día 4:

```
Ficha (fija, del producto)  →  cuelga del catálogo
Precio (variable, del local) →  vive en ProductoLocal
```

Consecuencia directa: cuando cambia el precio, el precio por unidad se
recalcula solo. No hay nada que mantener sincronizado.

---

## 4. Decisión: catálogo maestro compartido

Los medicamentos viven en una tabla **de Drakkar**, común a todos los clientes.
Una farmacia nueva escanea un código y la ficha completa ya está: solo pone su
precio.

### Por qué

- Una farmacia arranca en horas en vez de en semanas.
- Cada cliente que cargue un medicamento que no estaba **mejora la base para
  todos**. La farmacia número diez arranca con lo que cargaron las nueve
  anteriores. El activo crece solo.
- Una corrección de ficha se hace una vez, no una por cliente.

### Regla que no se negocia

> **El catálogo maestro NUNCA contiene precios ni stock.** Solo identidad y
> ficha técnica, que es información pública. Los precios son de cada local y
> son competitivamente sensibles: no se comparten jamás, ni siquiera de forma
> agregada o anónima.

### Un solo camino, también acá

Cuando el cliente carga un medicamento que no está en el maestro, **no** se
crea una ficha paralela en su catálogo. Se crea una entrada en el maestro
marcada como *propuesta*, visible solo para esa empresa. Cuando el superusuario
la revisa y la aprueba, pasa a ser global.

Así la ficha vive **siempre** en el mismo lugar. Lo único que cambia es quién
la ve. Si existieran dos lugares posibles para una ficha, habría dos caminos
en el código para leerla, exportarla y corregirla — el mismo error que se
evitó con los lotes en el Día 4.

---

## 5. Categorías

Las cuatro categorías que gatillan el listado legal son **fijas del sistema**.
El cliente puede crear todas las que quiera para lo demás (perfumería, higiene,
accesorios), pero no puede tocar ni inventar las reguladas.

**La categoría es obligatoria en todo producto.** Un producto sin categoría es
un producto que puede faltar en un reporte que fiscalizan.

**Y el listado no se arma buscando la palabra "medicamento".** La categoría
lleva una marca —*entra en el listado de precios*— y el reporte pregunta por
esa marca. Si dependiera del nombre, bastaría que alguien escribiera
"Medicamentos" en plural para que un producto desapareciera del listado sin
que nadie se entere.

Subcategorías: libres, definidas por la empresa. Sirven para ordenar la
góndola, no para cumplir la ley.

---

## 6. Estructura propuesta

```
CATÁLOGO MAESTRO (de Drakkar, sin empresa, sin precios)
  ProductoMaestro
    ├── FichaFarmaceutica (1 a 1)
    │     ├── principio_activo    → tabla
    │     ├── dosis               → texto ("4 MG", "5%")
    │     ├── laboratorio         → tabla
    │     ├── cantidad            → número (30)
    │     ├── forma_farmaceutica  → tabla (comprimidos / ml / gramos...)
    │     └── bioequivalente      → Si / No / Referente
    └── códigos de barra

CATÁLOGO DE LA EMPRESA
  Producto
    ├── categoria  → FK obligatoria
    ├── maestro    → FK al ProductoMaestro (null si no aplica)
    └── ...lo del Día 4

STOCK DEL LOCAL
  ProductoLocal → precio  ← lo único que cambia
```

**Por qué tablas y no texto libre** para principio activo, laboratorio y forma
farmacéutica: se repiten miles de veces y se usan para filtrar y agrupar. En
texto libre convivirían "MINTLAB", "Mintlab" y "MINT LAB" como tres
laboratorios distintos. Dosis sí queda como texto: "4 MG" y "5%" no comparten
formato y no se usan para agrupar.

**Por qué `FichaFarmaceutica` es un modelo aparte** y no campos dentro de
`Producto`: una ferretería no tiene principio activo. Como modelo separado,
existe solo para los productos que lo necesitan y el módulo se puede apagar
entero. Es exactamente la regla del Día 4 — *configuración primero, módulo
opcional cuando la configuración no alcanza, código a medida nunca*.

---

## 7. Salida

La norma acepta **papel o pantalla**, así que las dos salidas cumplen:

1. **Exportación a Excel/PDF** con el formato exacto de la planilla. Es lo que
   se imprime y se exhibe en el mesón.
2. **Pantalla consultable** por nombre o principio activo, para exhibir en un
   computador del local.

La exportación primero, porque es la que sirve aunque se caiga la red. La
pantalla después, y es la que gana: se actualiza sola con el precio, mientras
que el papel hay que reimprimirlo cada vez que cambia algo.

**Como el listado se actualiza a diario, generarlo tiene que costar un clic.**
Si exportar implica elegir filtros, esperar y revisar, la farmacia lo va a
hacer una vez al mes y va a estar en falta los otros veintinueve días. El
diseño de esta pantalla se juzga por eso, no por cuántas opciones ofrece.

---

## 8. Impacto sobre lo ya construido

| Cambio | Tamaño | Cuándo |
|---|---|---|
| `Producto.categoria` (FK obligatoria) | chico — migración con valor por defecto | conviene hacerlo pronto |
| `Producto.maestro` (FK nullable) | chico | junto con el maestro |
| App del catálogo maestro | día completo de trabajo | módulo propio |
| Exportación e importación | día completo | después del maestro |

Nada de esto rompe lo del Día 4. La separación catálogo / precio / stock ya
sostiene el módulo entero: es el primer caso en que ese diseño se paga solo.

---

## 9. Pendientes

- [ ] Subir el Excel validado por el ISP, para construir el importador y la
      exportación contra el formato real
- [ ] Definir la lista de formas farmacéuticas y a qué familia pertenece cada
      una (contable / medible), porque decide la fórmula del precio por unidad
- [ ] Decidir cómo se resuelve una ficha del maestro que un cliente considera
      incorrecta: ¿la corrige y queda pendiente de aprobación, o solo reporta?
- [ ] Formato de la base de datos existente de medicamentos, para el importador
- [ ] Qué pasa con un producto propuesto por un cliente y rechazado por el
      superusuario: ¿sigue funcionando para esa empresa?
