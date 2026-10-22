---
name: registro-cambios
description: >
  Crea la entrada de docs/registro/ (cambio, decisión o plan) siguiendo la convención spec-as-source
  de SISOC. Usar al cerrar un cambio funcional visible, una decisión de arquitectura o diseño, un
  cambio de seguridad/permisos o un trade-off importante, o cuando haya que justificar que no aplica.
---

# Registro de cambios (spec-as-source)

Fuente de la convención: `docs/registro/README.md`. Esta skill la aplica paso a
paso; si algo de acá difiere del README, vale el README.

## 1. ¿Hace falta registrar?

Registrar si el cambio incluye al menos uno de:

- comportamiento visible para usuarios o integraciones (pantalla, API, archivo exportado);
- decisión de arquitectura o diseño que condiciona trabajo futuro;
- seguridad, permisos o datos sensibles;
- trade-off relevante para mantenimiento.

Si nada aplica (por ejemplo, un typo o un refactor sin efecto observable), no
crear archivo y decir en la entrega por qué no se registró.

## 2. Elegir tipo y ruta

| Tipo | Ruta | Cuándo |
|-|-|-|
| Cambio | `docs/registro/cambios/AAAA-TN/AAAA-MM-DD-<tema>.md` | lo que se implementó y cómo se verificó |
| Decisión | `docs/registro/decisiones/AAAA-MM-DD-<tema>.md` (sin trimestre) | una elección con alternativas y consecuencias |
| Plan | `docs/plans/AAAA-TN/AAAA-MM-DD-<tema>.md` | trabajo por fases antes de implementar |

- `TN` es el trimestre de la fecha: T1 enero–marzo, T2 abril–junio, T3 julio–septiembre, T4 octubre–diciembre.
- `<tema>` en minúsculas con guiones; incluir el número de issue cuando exista (`2724-datacalle-...`, `issue-2641-c4-ocr`).
- Un cambio que además fija una decisión: registrar el cambio y la decisión por separado, enlazados.
- `docs/registro/prs/` y `docs/registro/releases/` los genera `.github/workflows/pr-docs.yml`; no escribirlos a mano salvo lo que indica el README.

## 3. Contenido

Cambio (ver `docs/registro/cambios/2026-T4/2026-10-19-2724-datacalle-programa-local-provincial.md`):

```md
# Cambio: <qué cambia> (#<issue>)

## Alcance
Qué se pidió y qué se implementó. Rutas de código principales.

## Comportamiento
Qué ve ahora el usuario o la integración; compatibilidad con datos y versiones previas.

## Verificación
Tests y comandos que corrieron, con su resultado. Lo que no se corrió y por qué.
```

Decisión: formato de `docs/registro/decisiones/README.md` (Estado, Contexto,
Decisión, Consecuencias, Referencias).

Reglas:

- Hechos verificables y rutas reales; nada de PII, secretos ni datos reales.
- No inventar motivos humanos: si la justificación la propuso el agente,
  decirlo (ver `docs/registro/decisiones/2026-10-16-c4-ocr-runtime.md`).
- Separar lo validado localmente de CI, deploy o aceptación humana.
- Si cambia una guía canónica (`docs/implementaciones/`, `docs/flujos/`,
  `docs/operacion/`), actualizarla y enlazarla desde el registro.

## 4. Cerrar

- `python src/scripts/ci/check_docs_paths.py --existencia <archivo.md>`.
- Enlazar el registro desde la descripción del PR.

Ejemplo completo: `ejemplo.md` en esta carpeta.
