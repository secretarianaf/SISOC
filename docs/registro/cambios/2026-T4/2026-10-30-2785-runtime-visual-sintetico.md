# Runtime visual sintético de Insumos (#2785)

## Separación local (2026-11-05)

Esta unidad recupera el helper y sus pruebas sobre la API ya incorporada.
No ejecuta capturas, navegador ni recuperación visual pendiente. La prueba
actual del árbol mínimo se registra por separado; los resultados históricos
que siguen no equivalen a una nueva ejecución ni a aceptación de interfaz.

## Alcance

`src/scripts/frontends/insumos_visual_runtime.py` prepara una instancia descartable
del backend real para la referencia visual INS-A. No cambia settings, URLs,
permisos ni templates de la aplicación desplegada; no implementa INS-B.

## Comportamiento

- `prepare --root <directorio> --manifest <json>` exige un directorio vacío,
  directamente bajo el temporal del sistema y con prefijo
  `sisoc-insumos-visual-`, fuera del checkout. No existe un comando de borrado o
  reset: cada caso y cada lado usan un directorio nuevo.
- El proceso elimina su entorno heredado antes de importar Django, desactiva
  dotenv y proveedores y usa exclusivamente SQLite, archivos, caché y correo
  sintéticos locales. Bloquea conexiones salientes mediante el socket de Python;
  esto es una defensa adicional, no un sandbox del sistema operativo.
- Se construye el esquema descartable con el mismo patrón sin migraciones del
  preview existente. Esto no verifica migraciones de producción ni MySQL.
- Se materializan los roles INS-A, permisos individuales, programa, categorías y
  elementos del conjunto de lectura del manifiesto aprobado. Los perfiles están
  preparados para acceso web; no se crean encuestas. Las fechas de elementos
  provienen del manifiesto. Los IDs se resuelven por referencia y se guardan en
  `fixture-refs.json`, junto con huellas del manifiesto y archivo sintético.
- Los usuarios `visual_<rol>` tienen la contraseña pública de prueba
  `synthetic-visual-only`; nunca deben existir en un entorno compartido o real.
- Una segunda preparación rechaza el directorio sin modificar la base existente.
  Si una preparación falla, ese directorio queda incompleto: conservar la
  evidencia y usar otro directorio vacío, sin reutilizarlo silenciosamente.
- `serve --root <directorio> --port 8765` expone la aplicación y archivos estáticos
  en loopback. Dentro de Docker, `--container-listen` permite la interfaz del
  contenedor únicamente con publicación explícita
  `-p 127.0.0.1:8765:8765`; no publicar en interfaces externas.

El manifiesto de planificación corresponde al commit documental histórico
`e7824ad4c9e7240a4dd980c789567ceda08179ae`. Es una referencia del trabajo
original: el archivo de planificación no forma parte de esta unidad local ni es
requisito de sus pruebas autocontenidas.
No copiar `.env`, bases, archivos ni credenciales de otra instancia. Al comparar
revisiones, registrar por separado SHA de aplicación, huella del harness y
huella del fixture. No presentar la instrumentación como código del baseline.

## Verificación del árbol mínimo actual

Con la API de categorías ya incorporada, las dos pruebas originales pasan sin
cambiar el helper ni sus aserciones. Comprueban el rechazo de raíz no vacía,
materialización sintética, repetición rechazada sin cambiar bytes de SQLite,
acceso y denegaciones mediante Django test client y bloqueo del socket saliente.
Black, Pylint y referencias documentales pasan. Se ejecutó una sola vez en la
imagen local fijada, sin red y con código de solo lectura; no se inició servicio
TCP ni navegador, capturas o recuperación visual. Se conserva el resultado
fallido anterior, que carecía de la API requerida. El archivo Git se probó sin
modificaciones; sus bytes CRLF son equivalentes tras normalización a los blobs
LF, no idénticos. Esta prueba no acredita paridad visual, CI ni despliegue.

## Verificación histórica

Runner: imagen local fijada `a8e59c769a92`, montaje de código de solo lectura,
red desactivada, temporales descartables, entorno sintético:

```text
python -m unittest discover -s src/scripts/frontends -p test_insumos_visual_runtime.py
```

RED observado: herramienta ausente para el rechazo seguro; después no existía
`fixture-refs.json` para la preparación. GREEN inicial: rechazo sin efectos,
materialización sintética, rechazo de repetición conservando bytes de SQLite,
acceso Django al listado con consulta, denegación de alta, contexto listo y
bloqueo de conexión saliente. El test de aplicación usa el cliente HTTP Django,
no constituye un recorrido de navegador ni prueba de TCP publicado.

La verificación independiente ejecutó el manifiesto completo en dos lados
separados: 25 elementos, tres categorías, un programa y ocho roles INS-A,
comprobando campos, fechas, archivos, permisos y ausencia de efectos ante
repetición. Detectó un error al resolver el creador nulo de `insumo_024`; se
reprodujo con una regresión, se conservó el nulo sin tolerar referencias
desconocidas y el recheck independiente pasó. También verificó rechazo de raíces
inseguras y aislamiento frente a variables heredadas.

El recheck incluyó TCP real dentro del contenedor sin red externa: login,
listado, contexto y CSS estático accesibles; alta denegada para consulta.
Black y Pylint finales pasaron. No se inició una instancia persistente ni se
abrió un navegador para el usuario.

Pendientes: fixtures exclusivos de operaciones, navegador, capturas, comparación
React y aceptación humana. No hay baseline aceptado ni prueba de paridad visual.

Risk: items 2/5 (aislamiento del entorno local y bloqueo de conexiones).
