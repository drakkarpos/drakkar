# DECISIONES.md — Drakkar

Registro de decisiones técnicas y su fundamento.
Cada entrada es inmutable: si una decisión cambia, se agrega una nueva que la
reemplaza y se marca la vieja como superada. No se borra historia.

---

## D-001 — Repositorio privado en GitHub
**Fecha:** 2026-08-12
**Decisión:** El código vive en un repo privado de GitHub, commits atribuidos a
drakkar.pos@gmail.com.
**Contexto:** Drakkar es un producto comercial por suscripción, no un proyecto
abierto. Soy principiante y dependo de documentación y foros para resolver
problemas.
**Alternativas descartadas:**
- *GitLab:* mejor CI integrado, pero comunidad mucho menor. Priorizo encontrar
  respuestas rápido cuando algo falle.
- *Repo público:* es mi producto comercial.
**Consecuencias:** Cuando haya clientes pagando, evaluar mover el repo a una
Organización de GitHub para separar el activo del negocio de mi cuenta personal.

## D-002 — PostgreSQL en dev y prod

## D-003 — Movimientos vs. Diferencias de stock
**Fecha:** 2026-08-12
**Decisión:** Los cambios de stock se registran en dos lugares distintos según
si la causa es conocida o desconocida.

*Movimientos de stock* (módulo propio) registra ingresos y egresos que requieren
documentarse y tienen causa justificada:
- Ingresos: por factura o por traslado desde otro local.
- Egresos: baja por calidad, vencimiento, producto defectuoso, uso interno,
  uso personal, traslado a otro local.

*Diferencias de stock* (submódulo de toma de inventario) registra descuadres
entre el stock físico y el que arroja el sistema, detectados sin causa aparente.
No es un ajuste consciente: es una alerta que dispara investigación interna
(¿error de ingreso? ¿venta no registrada? ¿pérdida real?).

Una diferencia nunca se convierte en un movimiento. Al detectarla se aplica el
ajuste numérico y queda en el histórico de diferencias. Si la investigación
encuentra la causa, el ajuste se revierte y la diferencia se marca como resuelta
con su motivo. Si no aparece explicación, se confirma y persiste como pérdida.

**Contexto:** Todo cambio de stock se venía registrando junto. Mezclar ajustes
justificados con descuadres inexplicados hace imposible auditar unos y alertar
sobre los otros: quedan sumados en la misma tabla dos hechos que significan
cosas distintas. Un ingreso por factura es contabilidad; un faltante de tres
unidades es un problema a investigar.

**Alternativas descartadas:**
- *Un solo módulo con un campo "motivo":* más simple de implementar, pero se
  pierde la pregunta que más importa — "¿cuánto stock se me fue sin explicación
  este mes?". Con todo mezclado, esa cifra hay que reconstruirla filtrando, y
  las alertas dejan de ser alertas.
- *Convertir la diferencia resuelta en un movimiento:* borraría el rastro de que
  hubo un descuadre. Justamente el dato que sirve para detectar productos
  problemáticos.

**Consecuencias:**
- Las diferencias tienen estado: **abierta** (detectada, ajuste aplicado, sin
  explicación), **resuelta** (causa encontrada, ajuste revertido) y
  **confirmada** (investigada sin explicación, la pérdida es real).
- Las resueltas guardan el motivo, y se distinguen al menos dos: *se contó mal*
  (falla el proceso de conteo) y *se encontró el artículo* (falla el
  almacenamiento). Son problemas distintos con soluciones distintas; si se
  guardan juntos, se pierde la posibilidad de saber cuál se tiene.
- Los ajustes se revierten con un registro nuevo que anula al anterior. **Nunca
  se borra.** Un producto que generó cinco descuadres —aunque los cinco se hayan
  resuelto— está diciendo algo, y borrar hace invisible ese patrón.
- Las estadísticas separan bajas justificadas (Movimientos) de pérdidas sin
  causa (Diferencias confirmadas). No se suman.
- El módulo de Movimientos tiene que existir para que la base de datos se llene
  con ingresos reales. Sin él, el stock del sistema nunca es confiable y las
  diferencias pierden sentido.
D-004 — Despliegue por fases: Pi → VPS
D-005 — Módulo vs. submódulo
D-006 — inventario_app y drakkar son productos separados; reutilización por copia
---

## D-007 — El producto se llama Drakkar

**Fecha:** 2026-08-18

**Decisión:** El nombre del producto es **Drakkar**. Se abandona "Control Stock",
que queda solo como referencia histórica de la app de toma de inventario previa.
El nombre aparece de forma consistente en el repositorio, las bases de datos
(`drakkar_dev`, `drakkar_demo`, `drakkar_prod`), el correo del proyecto y el
dominio.

**Contexto:** Los dos nombres convivían: la documentación decía "Control Stock",
mientras el repositorio, el correo y las bases ya usaban "drakkar". Un nombre
duplicado se multiplica solo — carpetas, dominios, textos en pantalla — y aparece
en lugares caros de cambiar después.

**Alternativas descartadas:**
- *Mantener "Control Stock":* es el nombre de la herramienta personal de toma de
  inventario, que sigue existiendo como programa aparte. Reutilizarlo para el
  software de ventas confundiría dos productos distintos.
- *Drakkar como empresa y Control Stock como producto:* agrega una marca más
  que administrar sin ningún beneficio hoy, con un solo producto.

**Consecuencias:**
- Corregir las instrucciones del proyecto, que todavía decían "Control Stock".
- Todo nombre nuevo —bases, servicios, subdominios— usa el prefijo `drakkar`.

---

## D-008 — Settings separados por entorno en archivos distintos

**Fecha:** 2026-08-18

**Decisión:** La configuración se divide en un paquete `config/settings/` con
tres archivos: `base.py` (lo común), `dev.py` (desarrollo) y `prod.py`
(producción). El entorno se elige con la variable `DJANGO_SETTINGS_MODULE`,
no con condicionales dentro del código.

**Contexto:** Django genera un único `settings.py`. La forma habitual de adaptarlo
a producción es agregar condicionales del tipo `if DEBUG:`. Eso deja la
configuración de producción a merced de que una variable tenga el valor correcto
en el momento correcto.

**Alternativas descartadas:**
- *Un solo settings.py con condicionales:* si `DEBUG` queda mal calculado, el
  servidor arranca en modo desarrollo y cualquier error muestra el código fuente
  y las credenciales en pantalla a quien lo provoque. El riesgo no está en que
  sea probable, sino en que la falla es silenciosa: nada avisa que ocurrió.
- *Un archivo por servidor con la config completa:* obliga a repetir todo lo
  común. Cualquier cambio general hay que aplicarlo en varios lugares, y tarde
  o temprano uno queda desactualizado.

**Consecuencias:**
- `manage.py`, `wsgi.py` y `asgi.py` apuntan a `config.settings.dev` por defecto,
  usando `setdefault`: el servidor puede imponer `config.settings.prod` mediante
  una variable de entorno, sin tocar el código.
- Producción no puede cargar configuración de desarrollo por accidente: son
  archivos distintos elegidos por el entorno, no una rama de un `if`.
- Migrar de la Raspberry Pi al VPS no requiere modificar ninguna línea de código.

---

## D-009 — Credenciales fuera del código, en un `.env` propio de cada servidor

**Fecha:** 2026-08-18

**Decisión:** Contraseñas, `SECRET_KEY` y dominios permitidos se leen de un
archivo `.env` mediante variables de entorno. El `.env` está en `.gitignore` y
se escribe a mano una vez en cada máquina. Las variables obligatorias se leen
con `os.environ[...]` sin valor por defecto.

**Contexto:** Django deja la `SECRET_KEY` escrita en el código. Cualquier secreto
que entre a Git queda en el historial para siempre, aunque después se borre del
archivo — y el repositorio puede cambiar de manos o volverse público.

**Alternativas descartadas:**
- *Secretos en el código:* además de quedar en el historial, obliga a que
  desarrollo y producción compartan credenciales o a editar archivos en cada
  despliegue.
- *Valores por defecto para las variables obligatorias:* una `SECRET_KEY` de
  respaldo hace que un servidor mal configurado arranque igual, en silencio y
  de forma insegura. Es preferible que falle al arrancar con un error claro.

**Consecuencias:**
- Las credenciales de producción no existen en la máquina de desarrollo ni en
  GitHub: viven únicamente en el servidor.
- Cada entorno tiene su propia contraseña de base de datos. Filtrar una no
  compromete a las demás.
- Hay que documentar qué variables necesita un `.env` para que montar un
  servidor nuevo no dependa de la memoria.

---

## D-010 — Demo y producción son instancias separadas en la misma Raspberry Pi

**Fecha:** 2026-08-18

**Decisión:** En la Pi conviven dos instalaciones del mismo repositorio,
separadas en tres niveles:

| | Demo | Producción |
|---|---|---|
| Carpeta | `/home/pi/drakkar-demo/` | `/home/pi/drakkar-app/` |
| Base de datos | `drakkar_demo` | `drakkar_prod` |
| Puerto (Gunicorn) | 8001 | 8000 |
| Subdominio | `demo.drakkar.(dominio)` | `app.drakar.(dominio)` |

Ambas usan `config.settings.prod`. Lo único que las diferencia es su `.env`.

**Contexto:** Se necesita un entorno para mostrarle el sistema a clientes nuevos
y, al mismo tiempo, un entorno real donde el cliente de prueba trabaja con sus
datos. Las dos cosas en el mismo hardware.

**Alternativas descartadas:**
- *El demo como un local más dentro del multitenant:* un demo se ensucia por
  diseño — cada persona a la que se le muestre va a registrar ventas falsas y
  borrar productos. Restaurarlo tiene que ser trivial. Si comparte base con el
  cliente real, cada restauración es una operación de riesgo sobre datos ajenos.
- *Compartir base entre demo y producción:* elimina justamente la separación que
  se busca.
- *Compartir puerto:* dos procesos Gunicorn no pueden escuchar en el mismo
  puerto; el segundo no arranca.
- *Un `settings/demo.py`:* la diferencia entre demo y producción es de datos y
  dominio, no de configuración. Un archivo más sería duplicación sin motivo.

**Consecuencias:**
- Restaurar el demo se reduce a borrar y recargar datos de ejemplo. Conviene
  crear un comando `python manage.py cargar_demo` con fixtures de Django.
- Al migrar al VPS, se traslada solo la instancia de producción, con la misma
  estructura de carpeta, base y puerto. El demo queda en la Pi.
- Tres bases con el mismo esquema y datos distintos: `drakkar_dev` (local),
  `drakkar_demo` y `drakkar_prod`.
  - **Pendiente:** definir y registrar el dominio. La estructura de subdominios
  (`app.` y `demo.`) sí está decidida; el dominio raíz no. Hay que resolverlo
  antes del Día 29, porque el túnel de Cloudflare y `DJANGO_ALLOWED_HOSTS`
  dependen de él.

  
**Contexto:** Demo y app conviven en la misma Raspberry Pi (D-010). Demo cumple
el rol de entorno de pruebas: ahí se valida cada cambio antes de que lo vea un
cliente. Sin una regla explícita, es fácil terminar editando código directamente
en el servidor porque "es un cambio chico".

**Alternativas descartadas:**

- *Editar el código directamente en la carpeta de demo:* los cambios existirían
  solo en la Pi, sin versionar. Además Git bloquea el `git pull` cuando hay
  modificaciones locales sin commitear, lo que convierte cada actualización
  posterior en un enredo. El repositorio deja de ser la fuente de verdad.
- *Copiar archivos por SFTP hacia los servidores:* no queda registro de qué
  cambió ni forma de volver atrás. Es exactamente lo que Git existe para evitar.
- *Una sola rama para todo:* funciona hoy, con una sola persona y sin producción,
  pero apoya la separación en la memoria: basta un `git pull` hecho por
  curiosidad en app para llevarse cambios a medio probar. Con dos ramas ese
  error deja de ser posible, no solo improbable.
- *Despliegue automático al hacer push:* quita el control sobre cuándo se
  actualiza un sistema que un cliente está usando. El despliegue a producción
  tiene que ser un acto deliberado.

**Consecuencias:**

- Subir a GitHub no despliega nada. Los servidores se actualizan solo cuando se
  ejecuta `git pull` en ellos.
- Las ramas `main` y `develop` se crean **el día que exista la instancia de app**
  (Día 29). Antes de que haya producción, dos ramas son ceremonia sin beneficio.
- Si hay cambios de modelos, después de cada `git pull` hay que correr `migrate`
  en esa instancia. Cada base es independiente.
- **Pendiente:** definir dónde se desarrolla una vez que la Pi esté funcionando.
  Opciones evaluadas: seguir en Windows, usar WSL2 (Linux dentro de Windows, más
  parecido a producción y sin costo de rendimiento) o una tercera carpeta de
  desarrollo en la propia Pi. La Pi como máquina de desarrollo es la opción menos
  recomendable: es lenta para editar y le resta recursos a las dos instancias que
  deben estar disponibles. La decisión se toma cuando Windows empiece a estorbar,
  no antes.

  ## ARQ-001: Arquitectura de múltiples locales por cliente

**Fecha:** [Hoy]  
**Estado:** DECIDIDO  
**Impacto:** Alto (determina URL, permisos, aislamiento de datos)

---

### Problema
Un cliente (ej. María) puede tener múltiples almacenes/locales. ¿Cómo accede a cada uno?
¿Una URL por local? ¿Un selector dentro de una URL? ¿Cómo evitar que un vendedor entre por error al almacén equivocado?

### Alternativas consideradas

**Opción A: Un local por URL (elegida)**
- Cada local = URL propia: `app.drakkar.cl/mariamarket1`, `app.drakkar.cl/mariamarket2`
- María (dueña) puede acceder a ambas URLs.
- Vendedores acceden solo a la URL/local que les corresponde.
- Protección: tabla `UsuarioAccesoLocal` valida qué locales puede ver cada usuario.

**Opción B: Múltiples locales en una URL**
- Una sola URL con selector de local dentro: `app.drakkar.cl/mariamarket` + dropdown.
- Más sofisticado, María maneja dos locales en un login.
- Mayor complejidad de codificación.

### Decisión
**Opción A: Un local por URL + tabla de permisos `UsuarioAccesoLocal`**

### Razonamiento
1. **Simplicidad:** Cada local es una "entrada" independiente. Menos lógica especial.
2. **Seguridad clara:** Si Juan intenta `app.drakkar.cl/mariamarket2` pero no tiene permiso, Django lo bloquea (403).
3. **Para el dueño:** María abre dos pestañas, una por cada local. Cómodo.
4. **Para vendedores:** Entran a su local, no pueden "errar" en el otro.

### Implicaciones
- **URLs:** Cada local requiere su propia URL (subdominio o path).
- **Permisos (Día 10-11):** Implementar `UsuarioAccesoLocal(usuario, local, rol)`.
- **Validación (Día 24):** Tests para garantizar que nadie ve datos de locales ajenos.
- **DNS/Cloudflare:** Configurar wildcard o múltiples subdominos.

### Nota técnica
Django siempre filtra por `local_id` en las consultas. Si un usuario no tiene permiso en `UsuarioAccesoLocal`, no accede a la URL; si accede, Django filtra sus datos por su `local_id` asignado.

---