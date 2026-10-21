# Ejemplo: checklist 1 con DataCalle dentro de Dispositivos

Caso real recorrido en `docs/desarrollo/verticales_independientes.md`: la app
`datacalle` vive dentro del vertical `dispositivos`, con un solo servicio
`backend_dispositivos`.

## Clasificación

Agrega una app a un vertical que ya existe → **checklist 1**. No es un vertical
nuevo: comparte runtime (`dispositivos_runtime`) y contenedor.

## Recorrido (plantilla de cómo queda en el PR)

La columna "Evidencia" dice dónde mirarlo en el repo; en un PR real se completa
con el resultado de los comandos que se corrieron.

| Ítem | Estado | Evidencia |
|-|-|-|
| Pertenece al mismo servicio y solo depende de su dueño/kernel | hecho | imports de `src/backends/dispositivos/datacalle/`; `lint-imports` |
| App en `src/backends/<vertical>/<app>/`, con recursos y tests junto al dueño | hecho | `src/backends/dispositivos/datacalle/` y `src/backends/dispositivos/tests/` |
| Agregada a `apps` del vertical en `src/backends/config/backends.json`, no a `CORE_APPS` | hecho | entrada `dispositivos`: `apps` = `dispositivos`, `datacalle` |
| URLs en el runtime y en la composición completa; prefijos nuevos solo si hace falta | hecho | `url_prefixes` `datacalle/` y `api/datacalle/`; `urlconf` `dispositivos_runtime.urls` |
| Contratos de imports actualizados y `url_registry.json` regenerado | hecho | `generar_registro_urls`; `test_registro_de_urls_al_dia` |
| Runtime aislado, permisos, recursos, tests y `service_images`; plan de deploy | pendiente | `service_images` corre en CI; `deploy_targets.py --files <archivos>` |

## Lo que no se marca

- "Verificado en local con `settings_all`" no alcanza para el ítem de runtime
  aislado: queda pendiente hasta que corra `service_images`.
- No se agrega un segundo contenedor por app: la guía lo indica para este caso.

## Contraejemplo

Un cambio que solo agrega un filtro en una vista de `datacalle`, sin imports ni
URLs nuevas, no necesita checklist: alcanza con las reglas de `AGENTS.md` y los
tests de la app.
