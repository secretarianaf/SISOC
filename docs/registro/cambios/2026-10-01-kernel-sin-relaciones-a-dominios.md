# Kernel sin relaciones ni señales hacia dominios

Segunda parte del corte del kernel (#1931, #2251, #2309). Viene después de
`2026-10-01-users-identidad-y-usuarios-core.md`. ADR:
`docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md`.

## Por qué

Un backend por vertical instala solo el kernel (`users`, `core`, `sentry`,
`ciudadanos`, `audittrail`). Además de los accesos PWA, el kernel declaraba
relaciones, señales y registros hacia `comedores`, `organizaciones`, `duplas`
e `intervenciones`, y por eso no arrancaba solo.

## Qué cambió

- **`Profile.duplas_asignadas`** pasa a declararse como
  `duplas.Dupla.coordinadores`.
  - Usa la misma tabla `users_profile_duplas_asignadas` y las mismas columnas.
  - `profile.duplas_asignadas` y `dupla.coordinadores` siguen funcionando
    igual, incluidos los filtros por ORM.
  - La señal de sincronización con `Dupla.coordinador` cambia solo su
    `sender`.
  - Migraciones solo de estado: `duplas.0004` y `users.0058`.
- **`core.Programa.organismo`** (FK a `organizaciones`) pasa a ser
  `organismo_id` entero en el estado de Django. La columna, el índice y la FK
  física siguen en la DB (migración `core.0010`, solo estado).
  - `programa.organismo` sigue disponible como property. Devuelve `None` en
    procesos sin `organizaciones`.
  - El formulario, el admin y el import/export siguen usando la organización
    por nombre.
  - El `SET_NULL` al borrar físicamente una organización lo hace ahora
    `organizaciones.programa_signals`.
  - Es transitorio: si `organizaciones` pasa al kernel para VAT, CDF y CDI,
    se puede volver a una FK con otra migración solo de estado.
- **Invalidación de cache:** las señales de `comedores.*` e `intervenciones.*`
  salen de `core.cache_utils` y pasan a `comedores/cache_signals.py` e
  `intervenciones/cache_signals.py`. Las claves y los helpers siguen en el
  kernel. La baja lógica de comedores se registra en el registro de soft
  delete.
- **Auditoría:** las definiciones de `audittrail` llevan su clave estática
  `(app_label, model_name)`. El visor filtra los logs sin importar el modelo,
  y cada proceso registra en `django-auditlog` solo sus modelos.

## Verificación permanente

`tests/test_kernel_arranca_solo.py` levanta un proceso con
`tests/settings_solo_kernel.py`, que tiene solo el kernel sin dominios. Ese
proceso corre `manage.py check` e importa los módulos del kernel que usan los
verticales. Si alguien vuelve a acoplar el kernel a un dominio, el test falla.

## Sin cambios

Comportamiento, URLs, permisos, datos y esquema de la DB.
