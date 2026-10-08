# Rollback del release de la modularización (#2665)

Procedimiento para volver al `main` previo al release que trae la estructura
`src/backends` (#1931, #2251, #2309, #2639) y las migraciones de SIIS y CDI.
Aplica a HML y PRD. Una vez aplicado ese release en un entorno, este documento
deja de ser necesario para los deploys siguientes.

## Por qué no alcanza con volver el código

`deploy_verified.sh` restaura el checkout anterior y recrea el stack, pero
**no revierte migraciones**. El código anterior no funciona bien sobre la base
migrada:

- `users.0060` agrega `acceso_web` y `acceso_siis` NOT NULL. Django quita el
  default de la columna después de crearla, así que el código anterior falla
  con `IntegrityError` al crear un `Profile` (alta de usuarios, PWA, SIIS).
- `centrodeinfancia.0050` y `0051` agregan columnas NOT NULL a CDI: falla el
  alta de `AccesoCDI` y de nómina.
- `pwa.0025`, `catalogo_intervenciones.0001` y `gestion_organizaciones.0001`
  mueven content types de app (`users`→`pwa`, `intervenciones`→
  `catalogo_intervenciones`, `organizaciones`→`gestion_organizaciones`): los
  permisos que el código anterior busca con la etiqueta vieja dejan de
  resolverse.

Por eso el orden es: **primero revertir migraciones con la imagen nueva,
después volver el código**.

## Antes del deploy

1. Backup de la base y del `.env` (`backup_prod_configs.sh`).
2. Anotar el SHA de `main` desplegado (`git -C "$APP_ROOT" rev-parse HEAD`):
   es `<sha_anterior>` en lo que sigue. El SHA del release es `<sha_nuevo>`.

## Procedimiento

Si el rollback automático ya corrió, el checkout está en `<sha_anterior>` con
el stack anterior arriba: empezar igual por el paso 1. La imagen
`sisoc/migrator:<sha_nuevo>` sigue en el host porque las imágenes llevan el
SHA en el tag.

1. Cortar el tráfico de escritura (página de mantenimiento en Nginx o bajar
   `django`) para que nadie cree usuarios ni registros CDI en el medio.
2. Cuentas creadas por SIIS: con el código anterior no existe el bloqueo de
   `acceso_web`, así que podrían entrar a la web. Revisarlas y desactivarlas
   si corresponde (`Profile.source = "siis"`).
3. Revertir las migraciones con la imagen nueva, que tiene el grafo completo
   (`config.settings_all`). La base es la del `.env`:

   ```bash
   cd "$APP_ROOT"
   migrar() {
     docker run --rm --env-file .env "sisoc/migrator:<sha_nuevo>" \
       python manage.py migrate "$@"
   }
   migrar pwa 0024_backfill_representantes_pwa_permissions
   migrar users 0057_merge_usuarios_secciones_y_roles_territoriales
   migrar centrodeinfancia 0048_issue_2417_respuestas_no_sabe
   migrar admisiones 0082_caratula_borrador
   migrar intervenciones 0007_intervencion_admision_backfill
   migrar catalogo_intervenciones zero
   migrar gestion_organizaciones zero
   migrar organizaciones 0022_issue_2445_territoriales_abordaje_comunitario
   migrar duplas 0001_squashed_0003
   migrar core 0009_renaper_consulta_rate_limit
   migrar --plan   # no debe quedar nada del release aplicado
   ```

   `docker run --env-file` no quita comillas de los valores como sí lo hace
   Compose: si el `.env` las usa, o si la base corre dentro de la red de
   Compose (agregar `--network <proyecto>_default`), probar antes con
   `migrar --plan`.

   Django revierte también las migraciones que dependen de cada objetivo, así
   que el orden de arriba es seguro aunque alguna ya haya quedado revertida.
   Si la base no llegó a migrar (falló antes), los comandos no hacen nada.
4. Si el checkout todavía no está en `<sha_anterior>`:
   `git -C "$APP_ROOT" reset --hard <sha_anterior>`.
5. Recrear el stack anterior con su propio script, **sin** `--diff-base` (el
   de `main` no lo conoce):

   ```bash
   SISOC_ROOT_DIR="$APP_ROOT" bash "$APP_ROOT/scripts/operacion/deploy_refresh.sh" \
     --yes --skip-pull --expected-revision <sha_anterior> --without-mobile
   ```

6. Verificar: `docker compose -f docker-compose.deploy.yml -f
   docker-compose.produccion.yml exec -T django python manage.py migrate
   --check`, `scripts/infra/healthcheck_prod.sh` y un login web.

## Qué se pierde al revertir

- `acceso_web` y `acceso_siis`: las habilitaciones cargadas después del deploy.
- `campos_verificados_renaper`, `estado` y `es_responsable` de CDI: las
  verificaciones RENAPER y los estados de accesos cargados después del deploy.
- `datos_organizacion_snapshot` de admisiones.

Los datos de negocio que no dependen de esas columnas quedan intactos: el
resto de las migraciones del release solo cambian el estado de Django, no
tablas.
