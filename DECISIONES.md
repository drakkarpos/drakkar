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