---
name: usuario-no-tecnico
description: >
  Lleva de punta a punta una tarea pedida por alguien que no sabe programar: rama nueva desde
  origin/development, entender el pedido, implementar con cambio-guiado, verificación visual guiada
  en el entorno local, commits y PR completo, y seguimiento de CI. Usar cuando quien pide no es
  técnico o invoca /usuario-no-tecnico al empezar una tarea en SISOC.
---

# Usuario no técnico

Aplica `AGENTS.md` ("Antes de empezar" y "Responsabilidades del agente"); si algo
de acá difiere, vale `AGENTS.md`. Quien pide decide **qué** quiere; vos respondés
por **cómo** se hace. Hablale siempre en español y sin términos técnicos.

Si no te dieron el pedido, pedí: número de issue (o "sin issue"), qué pasa hoy,
qué debería pasar, quién lo usa y en qué pantalla o reporte.

## 1. Preparar la rama

- `git status`. Si hay cambios sin commitear que no son tuyos, parar y avisar:
  no borrarlos, ni stash, ni reset.
- `git fetch origin` y rama nueva desde `origin/development`:
  `git switch -c <tipo>/<issue>-<descripcion-corta> origin/development`
  (`feat`, `fix`, `docs` o `refactor`; por ejemplo `feat/2718-descarga-actas`).
- Nunca trabajar ni commitear directo en `development`, `homologacion` ni `main`.

## 2. Entender el pedido

- Devolver en 3 a 5 líneas qué entendiste: qué pasa hoy, qué va a pasar y cómo
  se va a ver que funciona. Esperar confirmación.
- Si falta algo (reglas de negocio, permisos, nombres de campos), preguntar y
  esperar. Si el pedido es grande, proponer partes y hacer solo la primera.

## 3. Implementar y testear

Seguir la skill `cambio-guiado` (pasos 2 a 6): ubicar al dueño, copiar un patrón
existente, cambio chico, tests que afirman el comportamiento y autorrevisión de
armonía. Correr los tests del módulo y `black`, `pylint` y `djlint` sobre los
archivos tocados (comandos en `CLAUDE.md`); `makemigrations --check` si cambian
modelos. Lo que no se pudo correr se dice; no se da por pasado.

Si el cambio toca una zona delicada, avisarlo ahora en simple, no recién en el PR.

## 4. Verificación visual con quien pidió

Antes de cualquier commit o PR. Solo entorno local: nunca QA, homologación ni
producción.

1. Levantar el entorno: `docker compose up -d`. El arranque aplica migraciones,
   fixtures y usuarios de prueba (`docs/operacion/instalacion.md`); el primero
   puede tardar varios minutos. Confirmar que responde en http://localhost:8001
   (o el `DOCKER_DJANGO_PORT_FORWARD` del `.env`) y revisar
   `docker compose logs django --tail 50`.
2. Guiar de a un paso por vez, en simple:
   - el link exacto a abrir;
   - con qué usuario entrar: uno de prueba de
     `src/backends/kernel/users/management/commands/create_test_users.py` (solo
     existen con `DEBUG=True`) con los permisos que hagan falta;
   - qué hacer (dónde hacer clic, qué completar) y qué tendría que ver;
   - un caso que **no** debería funcionar (dato inválido o usuario sin permiso)
     y qué tendría que ver.
3. Después de cada paso, esperar que cuente qué vio. Si no coincide con lo que
   pidió, corregir, volver a correr los tests y repetir la verificación.
4. No pasar al paso 5 hasta que diga explícitamente que es lo que quería.

Si el entorno no levanta, explicar en simple qué pasa y no saltear el paso en
silencio: el PR dice que la verificación visual no se hizo y por qué. La base
local puede tener datos reales de personas: no van capturas ni datos personales
en el PR.

## 5. Commits y PR

- Commits en español con Conventional Commits: `feat(<app>): <qué hace>`.
- Registro en `docs/registro/` si corresponde (skill `registro-cambios`), o
  decir por qué no hace falta.
- Push de la rama y PR contra `development`:
  `gh pr create --base development --title "<tipo>(<app>): <resumen>" --body-file <archivo>`
- El cuerpo sigue `.github/pull_request_template.md` con **todas** las secciones
  completas: issue vinculado, resumen, cambios, pruebas automáticas, pruebas
  manuales (los pasos de la verificación visual y que quien pidió los
  confirmó), lenguaje simple, patrón seguido, zonas sensibles, checklist y
  metadata para documentación.
- No mergear, no desplegar, no aprobar y no poner el label `excepcion-calidad`.

## 6. Cierre

- Esperar los checks: `gh pr checks <número> --watch`. Si uno falla, leer el log,
  explicar la causa en simple y corregir en la misma rama.
- Entregar: link del PR, qué cambia para el usuario, cómo probarlo paso a paso,
  qué podría romperse y qué no se pudo verificar.

Ejemplo completo: `ejemplo.md` en esta carpeta.
