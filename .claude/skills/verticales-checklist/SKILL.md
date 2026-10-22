---
name: verticales-checklist
description: >
  Recorre el checklist de verticales independientes de SISOC que corresponde al cambio: app en un
  vertical existente, vertical nuevo, pantalla del core con datos de un vertical o mover un modelo
  de app. Usar al crear o mover apps, modelos, URLs o recursos entre kernel, sisoc_core y
  verticales, o al revisar un PR que cruza servicios.
---

# Checklist de verticales independientes

Fuente: `docs/desarrollo/verticales_independientes.md`. Esta skill no agrega
reglas: elige el checklist de la guía y deja evidencia de cada ítem. Si algo de
acá difiere de la guía, vale la guía.

## 1. Clasificar el cambio

| Si el cambio... | Checklist |
|-|-|
| agrega una app a un vertical que ya existe | 1: app en un vertical existente |
| crea un backend/vertical con runtime propio | 2: vertical nuevo |
| muestra en el core (portal, Ciudadano 360, dashboard) datos de un vertical | 3: pantalla del core con datos de un vertical |
| mueve un modelo a otra app o cambia un app label | 4: mover un modelo de app (ver también la skill `migracion-app-label`) |
| solo toca código dentro de una app existente, sin imports nuevos entre servicios | ninguno: aplicar solo las reglas de `AGENTS.md` |

Antes de seguir, ubicar el dueño con la tabla "Dónde va un archivo" de la guía.

## 2. Recorrer el checklist

Copiar los ítems del checklist elegido en la descripción del PR o en el plan y,
por cada uno, anotar:

- **hecho**, con el archivo o comando que lo demuestra;
- **no aplica**, con el motivo;
- **pendiente**, con quién o qué lo destraba.

No marcar como hecho algo comprobado solo con `config.settings_all`: la
composición completa puede ocultar un import indebido o un registro faltante.

## 3. Validar

Comandos de la sección "Comandos y alcance de validación" de la guía, según lo
que toque el cambio:

- tests de arranque, registro y proxy del kernel;
- `generar_registro_urls` con `config.settings_all` si cambian URLs;
- `lint-imports` con el `PYTHONPATH` de `.github/workflows/architecture.yml`;
- `python src/scripts/operacion/deploy_targets.py --files <archivos>` para conocer el plan de deploy;
- `python src/scripts/ci/check_docs_paths.py --existencia <docs.md>` si se tocaron docs.

Informar lo que no se corrió (por ejemplo, `service_images` solo corre en CI).

## 4. Registrar

Si el cambio cruza servicios, registrar dueño, tablas, dependencias, permisos,
side effects y compatibilidad (skill `registro-cambios`).

Ejemplo completo: `ejemplo.md` en esta carpeta.
