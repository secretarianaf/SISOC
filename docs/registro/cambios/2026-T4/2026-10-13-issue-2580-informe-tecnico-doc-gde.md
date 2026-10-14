# Issue #2580: tablas del Informe Técnico y descarga DOC para GDE

## Problema y alcance

Los Word adjuntos al issue contienen cuadros de prestaciones convertidos a
párrafos. Se reprodujo un mecanismo que produce ese defecto: htmldocx 0.0.6
dimensiona la tabla contando las celdas de la primera fila, sin considerar
`colspan`/`rowspan`; una fila posterior más ancha dispara `IndexError`. El
fallback del generador devolvía texto plano como un documento válido. Esto
demuestra el mecanismo, no el origen histórico exacto del informe 1271, para
el que falta la versión publicada de la plantilla o el log de generación.

La descarga para GDE también entregaba DOCX, aunque el issue pide DOC.
El usuario autorizó la corrección y precisó que el modelo funcional adjunto
no corresponde exactamente al mismo informe. No se reemplazan textos,
criterios, plantillas publicadas ni variantes usando ese modelo.

## Cambio

- Adaptación local de la conversión HTML para construir la grilla completa y
  combinar las celdas, preservando contenido y encabezados.
- Anchos proporcionales para los cuadros de prestaciones reconocibles de nueve
  columnas (20% tipo, 65% días, 15% total), evitando nombres cortados por una
  grilla uniforme; se aplica en la generación, no sobre tablas editadas.
- Las plantillas publicadas no se degradan a texto plano si falla la conversión.
  El flujo de finalización existente devuelve error y conserva la editabilidad.
- La descarga para GDE normaliza una copia del último DOCX y la convierte a DOC
  Word 97-2003 con LibreOffice Writer, ya instalado en la imagen Docker.
- Directorio y perfil temporales por solicitud, timeout de 120 segundos y
  comprobación de salida binaria; ante fallos se utiliza el mensaje de error
  de la descarga. No se registran stdout/stderr ni contenido del documento.
- El DOCX editable, los archivos históricos, permisos y estados se conservan.
  Sin migraciones ni dependencias nuevas de producción.

## Validación y aceptación

Regresiones en `src/backends/kernel/tests/test_informes_service_unit.py` para
tablas combinadas, variantes con contenido diferente, rechazo de tablas inválidas,
ausencia de fallback estructural y conversión DOC/fallos/limpieza de temporales.
La vista se cubre en `src/backends/sisoc_core/tests/test_admisiones_web_views_unit.py`
para formato/MIME, prioridad del editado, permisos y error de conversión.

Los tests de servicio se ejecutan también en un harness temporal aislado que
carga las clases reales por AST, sin inicializar los modelos ni usar base de datos.
Ese resultado no sustituye la suite Django. Se ejecutaron pruebas aisladas de
servicio y vista, conversión real DOC con LibreOffice en Windows, reconversión
para comprobar texto/cantidades/tablas e inspección visual de los PDF de prueba
de incorporación y renovación. Son documentos de prueba de formato, no la
plantilla funcional de otra variante ni una validación en GDE.

El intento de tests focalizados mediante pytest del proyecto no pudo inicializar
settings por `ModuleNotFoundError: dotenv` en el entorno local mínimo. Black y
`git diff --check` pasan. El verificador documental señala una referencia
preexistente en el mapa del repo a `kernel/tests/test_usuarios_simepi_scope.py`.
Pylint no está disponible en el entorno aislado. Comandos pendientes en el
entorno oficial:

```powershell
src/scripts/ai/codex_run.ps1 test src/backends/kernel/tests/test_informes_service_unit.py src/backends/sisoc_core/tests/test_admisiones_web_views_unit.py
src/scripts/ai/codex_run.ps1 pylint src/backends/sisoc_core/admisiones/services/informes_service/impl.py
src/scripts/ai/codex_run.ps1 pylint src/backends/sisoc_core/admisiones/views/web_views.py
```

## Riesgos y reversión

No se reconstruyen cuadros históricos que ya fueron aplanados. La conversión
puede variar la paginación y depende de fuentes y LibreOffice del runtime.
La aceptación final requiere importar un DOC de la variante correcta en GDE y
comprobar cuadros, totales e incisos sin cortes ni marcos negros. El PDF del
issue se inspeccionó como referencia, no como salida generada por este cambio.

La reversión es de código; no modifica datos ni exige revertir migraciones.
No se realizó despliegue ni se validó comprensión o aceptación humana.
