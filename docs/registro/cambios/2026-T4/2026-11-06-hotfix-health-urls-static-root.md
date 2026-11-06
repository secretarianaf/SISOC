# Hotfix: /health/urls/ no recorría las URLs en producción

Rama `hotfix/health-urls-static-root`, desde `main`.

## Síntoma

`/health/urls/` en producción mostraba:

```
{"generado": "2026-11-06T06:00:00-03:00", "error": "El usuario del chequeo no llega a inicio (status 500): no se recorrieron las URLs."}
```

## Causa

Verificada en prd-old (`logs/2026-11-06/error.log`):

```
ValueError: Missing staticfiles manifest entry for 'custom/img/sisoc_logo.ico'
[2026-11-06 06:00:00,315] chequear_urls ERROR django: health/urls: falló el chequeo
```

- En producción los estáticos usan `ManifestStaticFilesStorage`, que necesita
  `static_root/staticfiles.json`. Lo genera el migrador con `collectstatic`.
- Los servicios web de `docker-compose.deploy.yml` montan
  `./static_root:/sisoc/static_root:ro`. El `health_urls_worker`, declarado en
  `docker-compose.produccion.yml`, montaba solo `./logs`: dentro del contenedor no
  existía el manifest (`docker exec ... ls /sisoc/static_root/staticfiles.json` →
  `No such file or directory`).
- El chequeo renderiza `inicio.html`; el primer `{% static %}` lanza `ValueError`, la
  respuesta es 500 y `_verificar_acceso` corta el recorrido.

## Solución

`health_urls_worker` monta `./static_root:/sisoc/static_root:ro`, igual que el resto
de los servicios que renderizan templates. No cambia código de aplicación.

## Verificación

- Test nuevo `test_health_urls_worker_lee_el_manifest_de_estaticos`
  (`kernel/tests/test_deploy_workflow.py`): fallaba antes del cambio, pasa después.
- El cambio en compose dispara despliegue completo (`deploy_targets.py`), así que el
  worker se recrea con el volumen.
- Pendiente tras el deploy: que la corrida siguiente (6, 12 o 18 h) muestre el
  resumen en `/health/urls/` en lugar del error.
