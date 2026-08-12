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
D-003 — Movimientos vs. Diferencias de stock
D-004 — Despliegue por fases: Pi → VPS
D-005 — Módulo vs. submódulo
D-006 — inventario_app y drakkar son productos separados; reutilización por copia