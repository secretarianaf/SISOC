# #2641: dependencias de runtime y desarrollo

Estado: **implementado y build limpio validado localmente; CI pendiente**.
Actualización posterior: el responsable habilitó continuar en Docker tras la
consulta de descargas. Los 14 targets y verificaciones de perfiles/arranque
pasaron en imágenes nuevas. La evidencia inicial de este documento conserva
el fallo offline; el resultado posterior está en
`docs/registro/cambios/2026-T4/2026-10-16-issue-2641-build-limpio-docker.md`.
La aprobación inicial de la propuesta conservadora y validación local offline
fue «apruebo»; entonces no habilitaba descargas, CI remota, incorporación o
deploy. La autorización posterior de descargas se describe arriba; CI remota,
incorporación y deploy siguen fuera de alcance. No se crea otro corte ni se
reabren las fronteras C0–C4.

## Cambio y motivo

`docker/django/Dockerfile` instalaba `requirements/all.txt` en la base de todas
las imágenes. Ahora base instala `requirements/base.txt` y el último target
`dev` agrega `all.txt`. `core`, `backend` y `migrator` conservan sus padres,
roles y composición de código. Compose de desarrollo/CI sigue eligiendo dev.

Se trasladan de dev.txt a base.txt, sin actualizar sus versiones:
`django-extensions`, `django-debug-toolbar`, `django-silk`, `gprof2dot`,
`autopep8` y `pycodestyle`. Extensions es app compartida incondicional;
DEBUG agrega Toolbar y ENABLE_SILK agrega Silk. La preview incluye URLs de
Toolbar. Silk requiere gprof2dot y ofrece autopep8 como extra de formato;
conservarlo con pycodestyle evita perder soporte ya disponible. La justificación
técnica provino del agente; el responsable aprobó conservar ese comportamiento.

Diecisiete pins directos de herramientas/tests quedan fuera de base: Black,
debugpy, djlint, isort, Pylint y sus dos plugins, coverage, execnet, factory_boy,
Faker, model-bakery y pytest con sus cuatro plugins. La unión de pins de
base+dev+test conserva exactamente las versiones anteriores. No se podan los
auxiliares históricos de tooling ya fijados en base, ni paquetes Debian, ni se
crean perfiles por vertical. No se modifican settings, rutas, permisos o datos.

`.github/workflows/tests.yml` extiende el job existente `service_images`:
construye también dev, ejecuta `pip check` en core/dev y comprueba versiones
de todos sus pins, ausencia de los 17 paquetes en core y presencia en dev.
Los checks de arranque, aislamiento y comandos de workers C3/C4 se conservan.
La base Python de las imágenes runtime es común; los demás dueños conservan
sus checks de arranque. No se disparó ese workflow remoto.

Archivos: Dockerfile, base.txt, dev.txt, workflow de tests, guía de verticales,
guía de backends, mapa, índice, pendiente histórico y este registro.

## Validación local y límites

Se verificó el snapshot `post-c4-final-manifest.json`: **1905 entradas** sin
diferencias; rama `juanikitro/Migracion`, HEAD
`1cede84d2b3490f2ddb6bf933852408d9fd68bc7`, staging vacío. No se restaura ni
sobrescribe trabajo previo. Los respaldos C0–C4 y del fix de fixtures permanecen.
Scratch: `C:/Users/Juanito/AppData/Local/Temp/sisoc2641-c0-1nh_v_m2/`.

| Criterio | Evidencia |
| --- | --- |
| No cambiar versiones/agregado de desarrollo | Comparación de pins con el estado previo y separación disjunta de perfiles; `deps-static-validation.json`. YAML/AST del nuevo step parseados; se ejecuta el mismo probe de metadatos de CI sobre la imagen local disponible |
| Preservar herramientas de dev | `deps-dev-profile.log`: versiones de base+dev+test presentes en la imagen checks existente; `deps-pip-check.log`: sin dependencias rotas. No es una imagen dev reconstruida |
| Detectar runtime contaminado | `deps-runtime-negative-control.log`: el probe rechaza correctamente la imagen checks por contener los 17 paquetes. Es un control negativo esperado, no una prueba runtime aprobada |
| Dependencias transitivas de base | `deps-offline-graph.log`: **146 distribuciones** resueltas desde metadatos instalados, verificando restricciones y extras Linux/Python 3.11, sin requerir los 17 paquetes. No es una instalación/resolución nueva ni prueba de ausencia física |
| Arranque y diagnóstico conservados | `deps-cold-results.json` y recheck: **ocho probes** en imágenes C3/C4 existentes (portal, Comedores, OCR y migrador; DEBUG false/true con Silk). Importaciones dev/test bloqueadas; Django checks sin DB, comandos de workers importados y URLs de preview resueltas en composición completa. No prueba imágenes nuevas ni operación funcional de cada comando |
| Selector y alcance operativo | `deps-selector-tests.log`: **43 passed**, 1.26 s. Cambios requirements/Docker/CI requieren completo + migrador; no se ejecutó deploy |
| Build con caché local | `deps-runtime-build.log` y su JSON de argumentos: `docker build --network=none --pull=false --target base ...` termina en APT con exit 100; no hay índices/capa reutilizable para los paquetes Debian. Falla antes de instalar Python o construir nuevas imágenes |

Todos los contenedores de inspección fueron efímeros, `--network none`, sin
`.env`, DB ni datos existentes. Se usaron fuentes/requirements RO cuando hacía
falta; correo locmem e integración externa desactivada en probes Django.
El build revisó `.dockerignore` y mantuvo red deshabilitada. No hubo descargas,
servicios DB, suites simultáneas, builds de otros entornos o cambios de Docker.

Cuatro probes iniciales omitieron `import config` antes de cargar settings del
vertical, por lo que no componían sys.path como manage.py/entrypoint. Se corrigió
sólo el harness y se repitieron esos cuatro casos con éxito; no se cambió
producción para ocultar un fallo. Los otros cuatro habían pasado.

## Pendiente, reversa y preservación

El siguiente párrafo describe el cierre inicial; el build local fue completado
en la actualización enlazada arriba. CI remota e incorporación siguen pendientes.

Falta reconstruir base, core, backends, migrador y dev con sus dependencias
disponibles, ejecutar `pip check`, confirmar ausencia física de tooling y el
arranque sobre esas imágenes nuevas. La caché actual no permite demostrarlo;
no se simula una base limpia reutilizando la imagen checks que contiene todo.
Las comprobaciones locales de metadatos/imports son evidencia parcial.
No se afirma ahorro de tamaño, velocidad, seguridad o capacidad medido.

No se ejecutaron CI, suite completa, migraciones, collectstatic, smoke humano,
deploy ni acciones en entornos existentes. No se repiten tests DB/OCR C4 por
este cambio de empaquetado. La reversa es sólo de requisitos/Dockerfile/CI;
no hay migraciones nuevas ni datos que revertir. Antes de incorporar se exige
el build limpio pendiente; no se recomienda incorporación con esta evidencia.

Se conserva Espacios comunitarios, el importador con imagen migrador completa
y rol propio, DB/storage/migrador compartidos y #2725 postergado. Sin stage,
commit, push, merge, cierre de issue o publicación. Revisión local delegada;
sin atribuir revisión de Claude ni comprensión humana validada o repetir los
ejercicios declinados.

Skills: brainstorming para encuadrar la decisión conservadora ya aprobada;
systematic-debugging para distinguir el límite de caché y sys.path del harness
de defectos en la separación. No se agregó una herramienta o dependencia.

Control final: **130 pins agregados conservados**, 113 directos de runtime y
17 de herramientas; sin solapamiento. Los demás jobs de CI y el step original
de aislamiento/arranque/workers se conservaron exactamente. `git diff --check`
aprobado. El control documental conserva las mismas dos referencias obsoletas
previas (SIMEPI y script de fronts); no se declara aprobado globalmente.
No se cambió Python productivo ni templates: no corresponde correr Black,
Pylint o djlint del proyecto por este diff; YAML y Python embebido se parsearon
y los probes indicados se ejecutaron. Sin suite completa por alcance y caché.

Comando exacto del build offline bloqueado, desde la raíz del workspace:

```powershell
docker build --network=none --pull=false --progress=plain --target base -t sisoc2641deps:runtime-base -f docker/django/Dockerfile .
```

Los argumentos de los probes se conservan en `deps-cold-commands.json`.
Respaldo final: `deps-final-manifest.json`, `deps-final.zip` y
`deps-final.patch`; ver `deps-preservation.json`. **1908 entradas y 1027
archivos existentes**, sin sobrescribir respaldos previos. De las 1905 entradas
recibidas, 1898 permanecen idénticas; los siete cruces son Dockerfile, workflow
y cinco documentos actualizados deliberadamente. Se agregan los dos manifiestos
de requisitos y este registro al snapshot. Inventario final del proyecto
sintético: cero contenedores, redes y volúmenes; imágenes previas conservadas.
