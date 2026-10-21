---
name: cambio-guiado
description: >
  Flujo completo para implementar un pedido en SISOC cuando quien pide puede no saber programar:
  entender el problema, ubicar al dueño, seguir un patrón existente, cambio chico con tests,
  autorrevisión de calidad y armonía, y PR explicado en lenguaje simple. Usar en cualquier pedido
  de funcionalidad, reporte, filtro, pantalla o corrección que cambie comportamiento.
---

# Cambio guiado

Aplica `AGENTS.md` ("Responsabilidades del agente"). Vos sos responsable de la
calidad: quien pide decide **qué** quiere, vos decidís **cómo** hacerlo bien.
Si algo de acá difiere de `AGENTS.md`, vale `AGENTS.md`.

## 1. Entender el pedido

Antes de abrir código, confirmar en lenguaje simple:

- qué pasa hoy y qué debería pasar;
- quién lo usa y en qué pantalla o reporte;
- cómo se va a dar cuenta de que funciona (el resultado observable).

Si falta algo de eso, preguntar. No adivinar reglas de negocio, permisos ni nombres de campos.

## 2. Ubicar dónde va

- Dueño del cambio: tabla "Dónde va un archivo" de `docs/desarrollo/verticales_independientes.md`.
- Mapa del código: `docs/ia/AGENT_REPO_MAP.md` (buscar la app, no leerlo entero).
- Guías por tema: `docs/implementaciones/`, por ejemplo `docs/implementaciones/filtros_avanzados.md`
  para filtros y favoritos.
- Si el cambio cruza servicios, mueve apps o modelos: skill `verticales-checklist`.

## 3. Buscar el patrón existente

Encontrar al menos un caso parecido que ya funcione en el repo (otro filtro, otro
reporte, otra pantalla del mismo dominio) y copiar su forma: archivos, nombres,
services, templates y tests. Anotar cuál es para el PR. Si no hay ninguno, decirlo:
es una señal de que el cambio necesita revisión técnica.

## 4. Implementar en chico

- Una sola intención. Si el pedido es grande, proponer partes y hacer la primera.
- Lógica en `services/` de la app; views delgadas; templates sin reglas.
- Sin dependencias, modelos, settings ni permisos nuevos salvo que sean imprescindibles; si lo son, explicarlo en el PR.
- Zonas delicadas (migraciones, permisos, settings, `src/backends/config/`, `src/backends/kernel/`,
  workflows, `docker/`, dependencias): implementar, pero marcar el PR como "Requiere revisión técnica".

## 5. Tests

- Un test por comportamiento: caso feliz, caso inválido y permisos si aplica (`docs/ia/TESTING.md`).
- Cada test **afirma** el resultado esperado; no alcanza con ejecutar las líneas.
- Ponerlos junto a los tests existentes del dueño, con el mismo estilo.
- CI (`quality_gate`) exige tocar tests y 80% de cobertura de las líneas cambiadas.

## 6. Autorrevisión de armonía

Antes de abrir el PR, revisar el diff completo contra esta lista y corregir:

- [ ] Sigue el patrón citado en el paso 3; no inventa una forma nueva de hacer lo mismo.
- [ ] Nombres en español, del dominio, con el mismo estilo que el archivo (`docs/ia/STYLE_GUIDE.md`).
- [ ] Reutiliza helpers y services existentes; no duplica código que ya está en `src/backends/kernel/core/`.
- [ ] Respeta permisos y alcance existentes; no abre endpoints ni datos por defecto (`docs/ia/SECURITY_AI.md`).
- [ ] Mensajes al usuario en español y sin detalles internos; logs sin datos personales (`docs/ia/ERRORS_LOGGING.md`).
- [ ] Sin código muerto, `print`, comentarios que repiten el código ni archivos sin uso.
- [ ] Sin cambios fuera del pedido (formateo masivo, renombres, "mejoras" no pedidas).
- [ ] Imports respetan los boundaries: el kernel no importa verticales; un servicio no importa otro.
- [ ] Tests que fallarían si el comportamiento se rompe.
- [ ] Formato y lint de los archivos tocados (comandos en `CLAUDE.md`).

## 7. PR y registro

- Completar `.github/pull_request_template.md`, incluida la sección en lenguaje simple.
- Registrar si corresponde (skill `registro-cambios`).
- No mergear ni desplegar. No poner el label `excepcion-calidad`.

Ejemplo completo: `ejemplo.md` en esta carpeta.
