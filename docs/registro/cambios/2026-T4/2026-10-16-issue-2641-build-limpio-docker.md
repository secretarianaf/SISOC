# #2641: build limpio y validación local en Docker

Estado: **build y verificaciones locales completados; sin CI remota o deploy**.
El responsable respondió «si podes hacerlo en docker mejor» a la consulta
explícita para descargar los componentes previstos en el Dockerfile y completar
los builds locales. Se conservaron las restricciones de publicación, entornos
existentes, datos reales y operaciones Git.

## Entrada preservada y ejecución

Workspace y rama sin cambios: `C:/Users/Juanito/orca/workspaces/SISOC/Migracion`,
`juanikitro/Migracion`, HEAD `1cede84d2b3490f2ddb6bf933852408d9fd68bc7`.
Se verificaron las **1908 entradas** de `deps-final-manifest.json` sin diferencias
y staging vacío antes y después de los builds, antes de actualizar documentación.
No se modificó código productivo, requisitos, Dockerfile ni workflow en esta
validación. C0–C4 y los fixes posteriores conservan su implementación.

Se usó el Dockerfile real con `--pull=false`, sin sustituir su base por la imagen
checks. Docker reutilizó capas de Debian, Tesseract y locales de su caché;
la instalación Python de `base.txt` se ejecutó en la nueva base de runtime.
`dev` ejecutó adicionalmente la instalación de `all.txt`. Se descargaron paquetes
Python dentro del build; no se instalaron paquetes en el Python del host.
No se afirma reconstrucción de Debian sin caché ni reproducibilidad bit a bit.

Se construyeron **14 targets** con etiquetas nuevas, sin sobrescribir imágenes
anteriores: `sisoc2641clean20261016:{base,core,migrator,dev}` y
`sisoc2641clean20261016:backend-<dueño>` para los diez backends registrados.
Son imágenes locales de un árbol sin commit, no un release desplegado.

Scratch: `C:/Users/Juanito/AppData/Local/Temp/sisoc2641-c0-1nh_v_m2/`.
`clean-build-plan.json` conserva los comandos exactos; su status inicial indica
que estaba pendiente de autorización, superado por esta ejecución. Resultados:
`clean-build-base-result.json`, `clean-build-results.json` y los catorce logs
`clean-build-*.log`. `clean-all-image-ids.json` conserva tags, IDs SHA256, tamaños
y capas. Todos los targets comparten las capas de la base runtime verificada.

## Aceptación y evidencia

| Criterio | Resultado y evidencia |
| --- | --- |
| Construir imágenes reales | **14 builds exit 0**, incluyendo base, core, migrador, dev y diez backends. Código del dueño copiado dentro de cada imagen; generación del mapa por el Dockerfile real |
| Versiones y perfiles | Mismo probe de metadatos del job `service_images`: los **113 pins directos de runtime** coinciden en sus 13 targets (incluida base); los **17 pins de herramientas** están ausentes. Dev contiene el agregado de **130 pins**. `clean-base-validation.json` y `clean-profile-results.json` |
| Dependencias consistentes | **14 ejecuciones de `pip check` aprobadas**, una por target. `clean-base-pip-check.log` y `clean-profile-*.log`. No es un lock completo de transitivas |
| Ausencia física adicional | En core se comprueban módulos con `find_spec` y ejecutables con `shutil.which`, sin bloquear imports ni borrar metadatos. No aparecen pytest, Black, Pylint, coverage, factories ni los demás módulos excluidos. `clean-runtime-physical-absence.log` |
| Arranque y aislamiento | **16 probes exit 0**: normal de core, migrador y diez backends; DEBUG+Silk de core, migrador, Comedores y OCR. Django checks sin DB; apps esperadas y carpetas exactas según dueño; imports de dev/test bloqueados. `clean-cold-results.json`, comandos exactos en `clean-cold-commands.json` |
| Workers conservados | Los probes importan y construyen parsers de `process_ocr_jobs`, `process_mailing_jobs` y `process_user_import_jobs` donde corresponden. Migrador conserva el adaptador de importación registrado. PAS autodetecta `schedule_month`/`reconcile` y programación de beat con broker en memoria; no arranca workers ni beat |
| OCR nativo | Imagen OCR nueva: imports OpenCV/NumPy/Pillow/pdf2image, español disponible y modelo best presente; Tesseract reconoce **PRUEBA OCR 2641** en una imagen sintética generada en memoria. `clean-native-ocr.log` y JSON de comando. No procesa documentos reales ni lotes DB |
| Herramientas de desarrollo | En dev nuevo, CLI de pytest, Black, Pylint, coverage y djlint disponibles. **43 tests del selector passed**, 0.83 s, sólo fuentes RO y sin conftest/plugins Django. `clean-dev-clis.log`, `clean-dev-selector-tests.log`, comandos en `clean-extra-validation-commands.json` |

`clean-validation-summary.json` resume el resultado, sin sumar corridas repetidas
como casos únicos. No se usa la evidencia parcial de las imágenes C3/C4 anteriores
para acreditar las nuevas: esos ensayos se conservan como antecedentes.

## Condiciones y alcance pendiente

Los contenedores de prueba fueron efímeros, `--network none`, sin `.env`, sin
DB ni broker reales, sin puertos ni volúmenes de datos existentes. Sólo los
helpers de evidencia y el test del selector se montaron RO; el código de los
servicios se ejecutó desde las imágenes. Correo locmem, integraciones externas
desactivadas y configuración sintética explícita. El build revisó `.dockerignore`
y excluyó secretos, dumps y media. No se hicieron operaciones en otros stacks.

El registro de tareas y los parsers no prueban salud de workers en QA/HML/PRD,
concurrencia o entrega de jobs. El ensayo OCR no sustituye aceptación funcional
de lotes. No se ejecutaron CI remota, suite completa, migraciones, collectstatic,
smoke con usuario, deploy selectivo/rollback de entornos existentes ni mediciones
de CPU/RAM/rendimiento. Esas evidencias siguen pendientes; la validación local
de imágenes deja de estar bloqueada por APT.

La primera incorporación conserva el plan completo + migrador por cambios
compartidos de Docker/requisitos. No se recomienda ni ejecuta incorporación
por inferencia de estos resultados. Permanece el cuidado C1 sobre metadata y
ContentTypes al revertir; no se revierten con una imagen automáticamente.
DB/storage/migrador compartidos, importador con imagen completa y rol propio,
Espacios comunitarios y #2725 postergado se conservan.

Sólo se actualizan este registro, el registro de dependencias, la guía de
backends, el mapa de agentes, el índice y la fila histórica del pendiente.
No se repiten entrevistas ni ejercicios declinados, ni se atribuye comprensión
humana o revisión externa de Claude. Se reutilizó el workflow existente de
imágenes; no hacía falta una nueva skill de implementación para ejecutar sus
controles ya definidos. El criterio de systematic-debugging aplicado previamente
mantuvo separados el fallo offline y la validación real posterior.

## Control de salida

`git diff --check` aprobado. El control documental revisó 83 documentos y sigue
reportando las mismas dos referencias obsoletas anteriores: test SIMEPI en el
mapa y script de fronts en deploy_pwas. No se corrigieron ni se declara ese
control global aprobado. No hay Python productivo o templates nuevos que
justifiquen repetir Black/Pylint/djlint del proyecto.

`clean-final-docker-inventory.json`: **cero contenedores, redes y volúmenes**
del proyecto sintético. Imágenes nuevas y anteriores conservadas; no se hizo
prune ni se operó sobre contenedores de otros proyectos. Sin staging ni commits.

Respaldo: `clean-final-manifest.json`, `clean-final.zip`, `clean-final.patch`
y `clean-preservation.json`. **1909 entradas, 1028 archivos existentes**, ZIP
verificado por SHA256. De las 1908 entradas recibidas, 1903 siguen idénticas;
los cinco cruces son documentación actualizada, más este registro nuevo.
Los respaldos previos no se sobrescriben. El patch no sustituye el ZIP porque
el árbol conserva archivos sin rastrear.

## Actualización 2026-10-19

Se completaron migraciones, fixtures y smoke HTTP con usuarios sintéticos sobre
estas imágenes nuevas, más `collectstatic` aislado. Navegación, permisos/CSRF y
caída/recuperación local de Comedores aprobados, sin reiniciar el portal.
Evidencia y límites: `docs/registro/cambios/2026-T4/2026-10-19-issue-2641-smoke-http-docker.md`.
Esto actualiza sólo esos pendientes locales: aceptación humana, CI remota y
operaciones de entornos existentes siguen sin ejecutarse.
