# #2641: fixtures e importación de ciudadanos después de C4

Estado: **corrección y validación locales; sin incorporación ni deploy**.
Continuación del pendiente secundario de #2641, sin crear otro corte.
No cambia la división aprobada de dominios, permisos, esquema ni dependencias.

## Preservación y alcance

Se leyó el handoff post-C4 y se verificaron rama `juanikitro/Migracion`, HEAD
`1cede84d2b3490f2ddb6bf933852408d9fd68bc7`, staging vacío y las **1902 entradas**
del manifiesto C4 sin diferencias. Los 1021 archivos del ZIP también coincidían.
Los respaldos C0–C4 permanecen intactos; no se creó otro checkout.

Se eligió revalidar el antecedente explícito de fixtures en DB vacía e importación
de ciudadanos con SQLite. No se separan dependencias runtime/dev ni se modifica
la topología. Espacios comunitarios, el importador con imagen completa del
migrador y rol propio, DB/storage/migrador compartidos y #2725 postergado se
conservan. Los pendientes operativos requieren sus autorizaciones particulares.

## Causa y cambio

En MySQL sintético recién creado y con el grafo completo migrado, la primera
ejecución de `load_fixtures` dejó ausentes los **526 departamentos IPI** de CDI.
Una segunda ejecución insertó los 526. El orden alfabético procesa
`cdi/.../departamento_ipi.json` antes de las provincias de `kernel/core`.
El comando resolvía dependencias dentro de cada archivo, pero descartaba sus
pendientes antes de llegar al siguiente; no era un fallo de importación SQLite.

- `kernel/core/management/commands/load_fixtures.py`: conserva los objetos
  pendientes y sus errores, reintenta entre archivos después de la primera
  pasada y termina cuando no reduce los pendientes. No vuelve a guardar objetos
  exitosos ni reevalúa tablas vacías para un archivo ya seleccionado y parcial.
  Los errores no recuperados se reportan al final. La llamada directa a
  `upsert_fixture` conserva su reporte inmediato.
- No cambia `--force`/`--overwrite`, la selección inicial de archivos, las
  transacciones por objeto, la tolerancia existente a errores ni los callbacks
  posteriores. No se deshabilitan FKs ni se introduce un orden fijo de dominios.
- `kernel/tests/test_load_fixtures_command.py`: cadena inversa de tres archivos,
  carga parcial y escrituras exitosas únicas, tanto normal como con force;
  padre irresoluble con salida finita y error visible; preservación de datos
  existentes sin force y reaplicación explícita con force.
- Guía de comandos, mapa de agentes, índice y pendiente histórico actualizados.

Las rutas anteriores son relativas a `src/backends/`.

## Evidencia

Scratch privado conservado:
`C:/Users/Juanito/AppData/Local/Temp/sisoc2641-c0-1nh_v_m2/`.
Los JSON `post-c4-*-command.json` contienen los argumentos exactos; los probes
temporales se conservan allí. Todo usó sólo el proyecto sintético autorizado
`sisoc2641c0-137b6c50`, `--env-file NUL`, fuentes RO, red interna sin puertos,
MySQL tmpfs, correo locmem e integración externa desactivada. Sin suites DB
simultáneas ni bootstrap que monte `.env`/dumps.

| Criterio | Evidencia local |
| --- | --- |
| Revalidar importación SQLite | `post-c4-sqlite.log`: **41 passed**, seis warnings; 38 casos de importación y los tres tests originales del comando. RENAPER sustituido por dobles de prueba; no acredita integración real |
| Reproducir dependencia entre archivos | `post-c4-fixtures-red.log`: los dos casos de la cadena fallan antes del cambio por falta del hijo; `post-c4-fixtures-resume.log`: 526 departamentos ausentes después de la primera carga real, presentes tras la segunda |
| Resolverla sin repetir éxitos, preservar force y errores | `post-c4-sqlite-recheck.log`: **52 passed**, seis warnings, 14.14 s; incluye catálogo, callbacks y territorio. `post-c4-mysql-tests.log`: **14 passed**, un warning, 18.45 s, con `--nomigrations` y DB de pytest separada |
| Carga completa en MySQL | `post-c4-fixtures-first.log`: migraciones completas sobre DB inicialmente sin tablas. Después del cambio, `post-c4-fixtures-fixed.log`: se vacía sólo esa DB sintética ya migrada con `flush`, se comprueba que departamentos y provincias están vacíos y se ejecuta `load_fixtures` dos veces. Primera y segunda terminan con **526 departamentos, cero errores de guardado/deserialización** |
| Calidad focalizada | Black sobre los dos Python; `post-c4-pylint-final.log`: **10/10** sobre comando y tests |

Los resultados no se suman como casos únicos ni sustituyen la suite completa.
El recheck final de MySQL tras la simplificación equivalente exigida por lint
se registra en `post-c4-mysql-tests-final.log`.
Resultado: **14 passed**, un warning, 20.20 s. Black final sobre los dos
Python y `git diff --check` aprobados. `post-c4-docs.log` conserva las mismas
dos referencias obsoletas previas (SIMEPI y script de fronts); el control
documental global no se declara aprobado.

El contador auxiliar inicial falló al tratar el diccionario de equivalencias
`celiaquia/fixtures/pais_a_nacionalidad.json` como fixture Django. Se corrigió
sólo el probe y se inspeccionó la DB resultante sin repetir migraciones.
El inventario bruto por PK tampoco equivale a integridad funcional: el catálogo
elimina subtipos vacíos y las migraciones de Organizaciones normalizan sus
entradas. Esas diferencias no se corrigieron ni se atribuyeron a este fallo.
El comando sigue avisando que ese diccionario no contiene modelos Django.

Una aserción nueva contaba signals anteriores al commit en SQLite; también
contaba intentos que luego revertían por FK diferida. Se ajustó el observador
del test a `transaction.on_commit`, manteniendo la exigencia de una sola
escritura confirmada por registro. No se modificó producción por ese detalle.
Pylint detectó una rama adicional; se simplificó el filtrado de pendientes y
el recheck quedó en 10/10.

## Límites y continuación

El cambio no reconcilia fixtures parcialmente poblados antes de esta invocación:
conserva la regla de seleccionar un archivo si alguno de sus modelos está vacío.
No altera el código de salida histórico ante errores ni convierte la carga en
una transacción global. Una FK irresoluble deja el registro pendiente y lo
reporta; los registros independientes permanecen cargados.

No hubo cambios de esquema, migraciones nuevas ni cambios en fixtures. La
reversa del código no requiere revertir datos; no se ensayó reversa de los
metadatos C1 ni se deben borrar sus ContentTypes. No se repitieron las pruebas
de OCR ni las 500 pruebas C4 porque esos componentes no cambiaron.

No se ejecutaron CI, suite completa, builds, deploys, entornos existentes,
RENAPER real ni aceptación funcional humana. Sin stage, commit, push, merge o
cierre de issue. Revisión local directa delegada; no se atribuye revisión de
Claude ni comprensión humana validada, y no se repiten los ejercicios declinados.

Skill aplicada: **systematic-debugging**, para reproducir antes de corregir y
separar el defecto real de los fallos del harness. Se consultó brainstorming:
se reutilizaron intención y límites ya aprobados, sin nueva arquitectura ni
entrevista. Las skills de frontend/orquestación no aportaban a este pendiente.

La salida conserva `post-c4-final-manifest.json`, `post-c4-final.zip`,
`post-c4-final.patch`, el control de preservación y el inventario de limpieza
del proyecto sintético, sin sobrescribir snapshots anteriores.
Se retiraron contenedores, red y MySQL tmpfs de las pruebas: inventario final
de ese proyecto con **cero contenedores, redes y volúmenes**. Las imágenes y
logs permanecen. De las 1902 entradas C4, 1898 siguen idénticas; los cuatro
cruces son documentación deliberada. Se agregan al respaldo los dos Python
de este fix y el presente registro: **1905 entradas, 1024 archivos existentes**.
