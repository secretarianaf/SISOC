# #2641: smoke HTTP sintético con las imágenes nuevas

Estado: **validación local aprobada; aceptación humana, CI y deploy pendientes**.
El responsable inició Docker Desktop y pidió continuar. Se ejecutó el pendiente
local sobre las imágenes del build del 16 de octubre, sin cambiar código
productivo ni repetir C4. Se conservaron C0–C4, sus decisiones y restricciones.

## Entrada y aislamiento

Mismo workspace `C:/Users/Juanito/orca/workspaces/SISOC/Migracion`, rama
`juanikitro/Migracion`, HEAD `1cede84d2b3490f2ddb6bf933852408d9fd68bc7`.
Las **1909 entradas** de `clean-final-manifest.json` se verificaron idénticas
antes de editar documentación; staging vacío.

Sólo proyecto `sisoc2641c0-137b6c50`, Compose independiente con `--env-file NUL`,
red interna, sin puertos publicados, pulls, builds ni `.env`. MySQL 8.4 nuevo
en tmpfs, con DB sintética `sisoc2641_smoke_20261019`. Migrador completo para
migraciones y fixtures; portal y seis backends desde sus imágenes propias.
Los IDs de las imágenes SISOC coinciden con `clean-all-image-ids.json`.
Sólo helpers montados RO;
código ejecutado desde las imágenes. Correo locmem e integraciones externas
desactivadas. No se accedió a entornos existentes ni datos reales.

## Criterios y evidencia

| Criterio | Resultado observado |
| --- | --- |
| Base nueva y datos mínimos | Migración del grafo completo y `load_fixtures` exit 0; sin errores de guardado/deserialización. Usuarios con y sin privilegios, programa y ciudadano sintéticos |
| Sesión compartida y navegación | Login HTTP real; **13 rutas en 200** por el portal: health, admin, Comedores, CDI, CDF, VAT, PAS, OCR, listado/detalle de Ciudadano, favoritos y dos admins del dueño |
| Permisos | Anónimo no obtiene el formulario (302/403); usuario sin permisos recibe **403** en creación de Montos |
| CSRF y escritura | POST sin token recibe **403**, sin crear monto. POST válido recibe **302**; ORM confirma desayuno 12.34 y registro de Historial |
| Caída parcial | Sólo Comedores detenido: su listado responde **503**. Health, login, listado/detalle de Ciudadano y PAS siguen en **200** |
| Recuperación | Se arranca sólo Comedores; las mismas **13 rutas vuelven a 200**. ID, imagen y StartedAt del portal idénticos antes, durante y después |
| Recursos estáticos | `collectstatic` en migrador nuevo, `--network none`, destino temporal dentro del contenedor: **456 archivos**, consultas SQL prohibidas por guard. CSS del admin presente y recursos de Comedores/Rendiciones idénticos a sus fuentes |

Los 13 controles repetidos al recuperar no se cuentan como rutas únicas nuevas.
`collectstatic` conserva avisos de destinos duplicados y la prioridad existente
del primer archivo; no demuestra entrega por Nginx ni apariencia en navegador.

La primera pasada usó URLs supuestas como `/comedores/` y falló con 404.
La URL real es `/comedores/listar`; también se contrastaron las otras rutas.
Se corrigió únicamente el helper mediante `reverse()` y se agregó preflight
de nombres antes de migrar. La segunda pasada completa pasó. Se aplicó
**systematic-debugging** para separar el error del ensayo de un fallo de la
aplicación; no hubo fundamento para modificar rutas productivas.

## Artefactos y salida

Scratch: `C:/Users/Juanito/AppData/Local/Temp/sisoc2641-c0-1nh_v_m2/`.
Corrida final: `http-smoke-20261019-ibjgwxfs/`, con `result.json` success true,
`commands.json`, logs de fases, `portal-state.json` y copias SHA256 de helpers.
La pasada fallida queda en `http-smoke-20261019-n37inmf0/`.
Estáticos: `clean-collectstatic-20261019.log` y su JSON de comando.
Preservación de entrada: `http-smoke-entry-preservation-20261019.json`.

`down --volumes --remove-orphans` retiró el proyecto; inventario posterior:
**cero contenedores, redes y volúmenes** propios. Imágenes conservadas, sin prune.
Sólo cambian este registro y sus referencias en índice, mapa, análisis y registro
del build. Sin staging, commit, acciones Git externas ni publicación.

No se ejecutaron suite completa, CI remota, workers de jobs, pruebas de carga,
mediciones de rendimiento, despliegue/rollback en entornos existentes ni smoke
humano. La aceptación humana permanece abierta; no se atribuye comprensión
validada o revisión externa. DB/storage/sesión/migrador compartidos, importador
con imagen completa y rol propio, Espacios comunitarios y #2725 postergado
se conservan.

Respaldo de salida: `http-smoke-final-20261019-manifest.json`,
`http-smoke-final-20261019.zip`, `.patch` y `-preservation.json`, con las
entradas anteriores, cambios nuevos y archivos sin rastrear. Los respaldos
previos se conservan. El patch por sí solo no incluye todos esos archivos.
