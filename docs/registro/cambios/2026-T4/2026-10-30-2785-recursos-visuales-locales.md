# Cambio: cache local aislada de recursos públicos para INS-A (#2785)

## Alcance

Se agregó `src/scripts/frontends/insumos_visual_assets.py` para descargar y cachear
recursos CSS/JavaScript públicos referenciados por las plantillas heredadas
`includes/base.html` y `scripts/mainscripts.html`. El cache recorre imports y
`url()` de CSS únicamente en `fonts.googleapis.com`, `fonts.gstatic.com`,
`cdn.jsdelivr.net`, `cdnjs.cloudflare.com` y `cdn.datatables.net`; excluye la
plantilla anidada de replay de Sentry y no modifica templates ni assets de
producción. El único destino de escritura es `--output`, obligatorio y fuera del
checkout.

## Comportamiento

La descarga usa Python estándar, sin cookies, autenticación ni proxies del
entorno, con User-Agent Chromium fijo registrado en el manifiesto. Rechaza URLs
con host/puerto/credenciales no permitidos, incluidos redirects, conserva los
bytes originales y registra URL, origen, SRI, Content-Type, tamaño y SHA-256.
URLs duplicadas comparten una descarga; el cache existente se verifica antes de
reutilizarse. Archivos corruptos o conflictivos no se reparan ni sobrescriben en
silencio. Fallos de captura dejan un manifiesto `partial` con errores explícitos.

Corrección R4-001: antes de almacenar una respuesta se comprueba que los bytes
recibidos coincidan con `Content-Length`, cuando está presente. Un EOF prematuro
no se convierte en un archivo válido por el solo hecho de calcular su hash.
La regresión reprodujo `complete` incorrecto con 4 de 20 bytes y luego verificó
`partial`, sin almacenar bytes; una respuesta completa conserva su resultado.
El formato local pasa a versión 2 para rechazar explícitamente caches anteriores
sin esta comprobación. Conservar el cache histórico y capturar en un directorio
nuevo; no convertir ni reutilizar automáticamente sus archivos.

## Verificación

- `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s src/scripts/frontends -p test_insumos_visual_assets.py -v`: **9 tests aprobados**; incluye allowlist/redirect, CSS recursivo, deduplicación, bytes originales, SRI, reutilización, corrupción y captura parcial.
- Black (`--check`) para ambos archivos Python: sin cambios pendientes.
- Captura autorizada: `python src/scripts/frontends/insumos_visual_assets.py --output C:\Users\Juanito\AppData\Local\Temp\sisoc-insa-public-assets-20261030-112435` produjo `complete`, 643 URLs únicas, 0 errores y 14.011.087 bytes. SHA-256/tamaño verificados para los 643 archivos. El cache y su manifiesto permanecen en ese directorio temporal externo.

## Límites

El cache facilita futuras capturas aisladas; no inicia servidores, instala
dependencias, renderiza páginas, crea una referencia aceptada ni demuestra
paridad visual. La aceptación humana del baseline y la comparación antes/después
siguen pendientes.
