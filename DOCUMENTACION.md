# Estándar de documentación — Drakkar

## Docstring de módulo
Todo archivo .py empieza con un docstring que responde dos cosas:
qué hace y por qué existe. Sin excepciones.

## Comentarios
Solo en decisiones no obvias. Un comentario explica el POR QUÉ.
Si explica el QUÉ, sobra: el código ya lo dice.

## DECISIONES.md
Toda elección técnica importante se registra con su fundamento
y las alternativas descartadas. Antes de implementar, no después.

## CHANGELOG.md
Formato Keep a Changelog: Agregado / Mejorado / Corregido.
Se actualiza al cerrar cada funcionalidad, no al final del mes.

## requirements.txt
Fuente de verdad. Solo lo que la aplicación necesita para correr.
Nada de herramientas de desarrollo o empaquetado.

## Settings
Separados por entorno: desarrollo y producción. Nunca un solo archivo
con condicionales.