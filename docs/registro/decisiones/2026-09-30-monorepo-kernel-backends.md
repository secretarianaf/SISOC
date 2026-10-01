# 2026-09-30 — Desplegables independientes: kernel, backends por vertical y Django como proxy

## Estado

Aceptada. Implementación por olas (ver "Plan"). Reemplaza, para las épicas
#1931, #2251 y #2309, el alcance de extracción definido en
`2026-08-27-dispositivos-servicio-independiente-monorepo.md` (PR #2365).

## Contexto

- Se pidió terminar rápido la migración a desplegables independientes. La
  prioridad es menos prolijidad a cambio de velocidad.
- #2309 exigía, para un solo vertical, JWS, gateway de identidad, schema y
  storage propios (Etapa B) y migración de datos con reversa. A ese ritmo no se
  termina.
- Hoy el deploy baja y levanta todo el stack (`deploy_refresh.sh`). Además,
  todos los contenedores montan el checkout completo (`.:/sisoc/`), así que
  actualizar el código para un vertical cambia el código de todos.
- Las PWA satélite muestran que se puede desplegar de forma independiente en
  el mismo servidor. También muestran lo que cuesta tener repos separados:
  el contrato queda partido, hay una clave SSH por repo y cada cambio necesita
  dos PRs.

## Decisión

Las definió el responsable técnico (juanikitro). Las marcadas como
*recomendación del agente* surgieron de la propuesta del agente y fueron
aceptadas.

1. **Monorepo y mismo servidor.** No se crean repos por vertical.
2. **Estructura del repo:**

   ```
   frontends/apps/<modulo>/   front React de cada módulo
   backends/<vertical>/       back de cada vertical: app Django, settings,
                              urls, wsgi, compose, Dockerfile y tests propios
   backends/sisoc_core/       cluster de Comedores (se mueve en la última ola)
   kernel/                    código común: core, users, iam, ciudadanos,
                              audittrail y settings base
   ```

3. **El core solo tiene código del core, y cada backend solo el suyo más el
   kernel.** Cada backend tiene su propio `settings.py`, que hereda del base del
   kernel y declara su `INSTALLED_APPS`. La imagen de un backend copia
   `kernel/` y su carpeta; la del core no incluye verticales. El kernel es una
   librería compartida, no una copia de un vertical.
4. **Imports sin reescritura** (*recomendación del agente*). Las carpetas
   `kernel/` y `backends/<vertical>/` se agregan al `sys.path`, así que se
   mantienen `import core`, `import pas`, los app labels, las migraciones y los
   nombres de tareas de Celery. En runtime el único punto que lo configura es
   `config/__init__.py`. El tooling estático lo declara en `.pylintrc`,
   `pytest.ini` y `architecture.yml`.
5. **Ruteo por Django.** Django core hace de proxy por prefijo hacia cada
   backend, con el mismo mecanismo que `/v2/` para los fronts. Cada vertical
   pasa a tener un prefijo propio (`/<vertical>/`, `/api/<vertical>/`,
   `/media/<vertical>/`). Las URLs viejas redirigen con 301 **solo por
   compatibilidad** con favoritos y links ya enviados; el código nuevo no debe
   usarlas.
6. **Sesión Django compartida.** Se elimina la decisión de #2309 de "no
   compartir sesiones Django" y la identidad firmada con JWS. Los backends
   autentican con la misma sesión, guardada en la misma DB y firmada con el
   mismo `SECRET_KEY`.
7. **Se pospone la Etapa B.** No hay schema ni storage propio por vertical.
   Cada tabla tiene un único escritor y los boundaries los controla
   import-linter.
8. **Deploy por servicio.** Cada imagen lleva el código construido desde el
   SHA, sin montar el checkout en deploy. El CI elige qué desplegar según los
   paths:
   - si el cambio es solo en `backends/<x>/**` o `frontends/apps/<x>/**`, se
     despliega solo ese vertical;
   - si toca `kernel/`, `config/`, templates o static compartidos, o
     requirements, se despliega todo.

   El rollback de un vertical es volver a desplegar su imagen del SHA anterior.
9. **Migraciones: un único job de migración** (revisado el 2026-10-01). Las
   migraciones del kernel dependen de migraciones de dominio (por ejemplo,
   `users.0031` depende de `centrodefamilia.0014`), así que un backend no
   puede cargar el grafo sin el cluster. Con la DB compartida, el grafo real
   es uno solo: un job *migrador*, con todo el repo y `config.settings_all`,
   corre antes de actualizar cualquier servicio. Los servicios web nunca
   migran. Reemplaza "cada backend migra solo su app".
10. **Datacalle entra en el backend de Dispositivos**, por velocidad. Comparten
    deploy.
11. **Media por vertical.** Los archivos nuevos se suben a
    `media/<vertical>/`. Los existentes se migran con un comando idempotente
    con `--dry-run`, que también actualiza las rutas en la DB. En PRD solo se
    ejecuta con autorización explícita, fuera de horario.
12. **Producción.** Ningún cambio, deploy ni migración se aplica en PRD sin
    autorización explícita de juanikitro y fuera del horario de uso.

13. **`kernel/users` es identidad y permisos** (2026-10-01). La gestión de
    usuarios (pantallas, formularios, importación masiva y API de login de
    las PWAs) es del core y vive en la app `usuarios`. Los accesos PWA
    (`AccesoComedorPWA`, `AccesoOrganizacionPWA`, `AuditAccesoComedorPWA`,
    `CoordinadorEquipoTecnicoPWA`) y su lógica pasan a `pwa`. Conservan sus
    tablas `users_*` y la migración es solo de estado. Sin esto, cualquier
    backend que instale `users` necesitaba `comedores`, `organizaciones` y
    `duplas`.

14. **Implementación de la Ola 1** (2026-10-01, *recomendación del agente*).
    Los nombres de URL entre servicios se resuelven con un registro generado
    (`config/url_registry.json`), así `reverse()` funciona sin tocar
    templates. Los ítems del menú que aporta una app del core se registran
    (`core.services.sidebar_items`). Los estáticos los recolecta el core y
    los backends los leen en modo solo lectura. Detalle operativo:
    `docs/operacion/backends_por_servicio.md`.

15. **Datos maestros compartidos al kernel** (2026-10-01, *recomendación del
    agente*). CDI y CDF necesitan `organizaciones` y los catálogos de
    intervenciones. En vez de duplicarlos o de que esos backends instalen el
    cluster de Comedores, `organizaciones` pasa a `kernel/organizaciones` y
    los catálogos a `kernel/catalogo_intervenciones`. Lo que se relaciona con
    comedores (pantallas de organizaciones y `Firmante`) queda en el core, en
    `gestion_organizaciones`. Las migraciones son solo de estado y conservan
    tablas y content types.

## Deuda aceptada (revisar en el futuro)

- **El aislamiento es de proceso, no de datos.** Una sola base MySQL y un solo
  schema. Una migración defectuosa o una caída de la DB afecta a todos los
  verticales. Revisar cuando algún vertical necesite ventanas de mantenimiento
  propias, tenga carga desigual sobre la DB o requiera una disponibilidad
  distinta. La salida es la Etapa B de #2309: schema y cuenta propios por
  vertical.
- **La sesión compartida** acopla la autenticación de todos los backends al
  core. Revisar si algún backend necesita exponerse fuera del dominio o del
  proxy.
- **El proxy de Django es un punto único de entrada.** Si se cae el core, se
  caen los verticales. Revisar si hace falta aislar fallas de entrada, por
  ejemplo con ruteo directo en Nginx.

## Alternativas descartadas

- **Repo por vertical.** Contradice el monorepo, parte los contratos y duplica
  la configuración de deploy.
- **Correr SISOC completo en cada contenedor y elegir el vertical con una
  variable de entorno.** Es más rápido de armar, pero multiplica código y
  memoria, y no deja una frontera real. Lo rechazó el responsable técnico.
- **Reescribir los imports a `kernel.core...` y `backends.pas...`.** Genera
  diffs enormes sin beneficio funcional y choca con la migración del front
  que está en curso.
- **Mantener el alcance completo de #2309.** No es compatible con el plazo.

## Plan

- **Ola 0:** este ADR, actualización de los issues y movimiento de
  `core`, `users`, `iam`, `ciudadanos` y `audittrail` a `kernel/`.
- **Ola 1:** settings base del kernel, proxy completo compartido con `/v2/`,
  imagen por servicio, deploy selectivo. Piloto con Dispositivos y Datacalle en
  QA y HML. Cortar las dependencias de `core` hacia `comedores`,
  `organizaciones` y otras, para que el kernel no arrastre el cluster.
- **Ola 2:** VPSL, PAS, VAT y Celiaquía (#2633). CDI y CDF quedaron para
  la Ola 3, porque antes había que pasar `organizaciones` y los catálogos de
  intervenciones al kernel (decisión 15).
- **Ola 3:** CDI y CDF, con `organizaciones` y los catálogos al kernel.
- **Ola 4:** mover el cluster de Comedores a `backends/sisoc_core/` y cerrar
  #2309, #2251 y #1931.

## Criterios de aceptación

- Un cambio solo en un vertical despliega solo ese vertical. Los demás
  contenedores mantienen su uptime.
- Un cambio en `kernel/` despliega todo.
- La imagen del core no contiene código de verticales, y CI lo verifica.
- Las URLs viejas redirigen a las nuevas con prefijo. Los tests y permisos
  actuales pasan.
- Cada backend se revierte a su SHA anterior sin tocar a los demás.
- En PRD no se aplica nada sin autorización y fuera de horario.
