# Cambio: Datos del Convenio en el legajo de Abordaje Comunitario (#2843)

## Alcance

El área pidió, para la sección "Datos del Convenio" de los comedores con
programa Abordaje Comunitario - Línea Tradicional y Línea Secos:

- quitar "Monto total conveniado" de la sección, para todos los programas;
- mostrar los campos en un orden fijo por línea, en la edición y en el legajo;
- aceptar solo números en los campos numéricos y mostrar los montos como
  `$100.000.000`, sin centavos;
- mejorar la UI, con los campos en formato listado.

Durante la revisión visual se acordó además aplicar a la edición el diseño del
alta de comedor y reorganizar el cuadro del legajo.

Código principal:

- `src/backends/comedores/comedores/forms/convenio_pnud_form.py`
- `src/backends/comedores/comedores/templates/comedor/comedor_convenio_pnud_form.html`
  y `_convenio_pnud_fila.html`
- `src/backends/comedores/comedores/templates/comedor/comedor_detail.html`,
  `_datos_convenio_legajo.html` y `_dato_convenio_legajo.html`
- `src/backends/comedores/comedores/views/comedor.py` (flag `convenio_ocupa_columna`)
- `src/backends/comedores/comedores/static/custom/js/convenio_pnud.js` y
  `static/custom/css/convenioPnud.css`

## Comportamiento

- "Monto total conveniado" no se muestra ni se carga desde la sección en ningún
  programa. El campo `ComedorDatosConvenioPnud.monto_total_conveniado` se
  conserva en el modelo, el admin y la API: no hay migración y los valores
  históricos no se pierden.
- Orden de los campos en la edición y en el legajo:
  - **Línea Tradicional**: Organización solicitante, Código de Proyecto, Número
    de Convenio, Estado General, Subestado, Nombre del Espacio Comunitario, ID
    Externo, Domicilio Completo, los dos montos por espacio, las cinco
    Prestaciones Financiadas Diarias, Personas Conveniadas y Total de personas
    declaradas en SIPH. La edición suma al final el cuadro de prestaciones por
    día; el legajo no lo muestra.
  - **Línea Secos**: los mismos ocho datos iniciales y los dos montos, Personas
    Conveniadas, Cantidad de Módulos Mensuales y Total de personas declaradas
    en SIPH.
  - Los demás programas que usan la sección mantienen sus campos: Prestaciones
    financiadas mensuales y Cantidad de Módulos Mensuales.
- El legajo ahora muestra "Total de personas declaradas en SIPH", que antes no
  aparecía.
- Las cantidades no admiten letras, signos ni decimales (filtro en el navegador
  y validación en el servidor). Los montos aceptan solo dígitos y puntos de
  miles, se formatean al salir del campo y aceptan un `$` pegado. Un valor con
  decimales, como `100,50`, se rechaza con un mensaje.
- Si un monto histórico tiene centavos y no se modifica, se conserva al
  guardar otro campo. Es el comportamiento vigente desde #2642.
- Edición: tarjetas de sección (Datos del Convenio, Montos, Prestaciones y
  Personas, Prestaciones por convenio) con el estilo de `comedorFormModerno.css`,
  botones fijos Cancelar y Guardar convenio, y un ancho máximo de cada caja
  según el dato.
- Legajo: cuando no se muestra "Mes de ejecución" (solo aparece en el programa
  con id 2), el cuadro ocupa toda la columna derecha y Transacciones se apila
  debajo de Asistencia. Los datos se agrupan en tres bloques (Convenio, Montos,
  Prestaciones y personas); Convenio y Prestaciones van en dos columnas.
  "Sin información" se ve atenuado y un 0 se muestra como dato. Los montos se
  muestran como `$18.889.752`, con el filtro existente `monto_sin_decimales`.

Criterios propuestos por el agente y aceptados en la revisión visual:

- reutilizar solo el CSS del alta, como `intervencion_form.html`, sin
  `comedorFormModerno.js`, porque ese script tiene fijas las secciones y los
  campos del alta;
- no incluir la barra de progreso del alta: la sección tiene datos de solo
  lectura y ningún campo obligatorio.

## Verificación

Local, en el contenedor `django`:

- `pytest src/backends/comedores/tests/test_issue_2843_datos_convenio.py`:
  16 passed. Cubre el campo quitado, el orden por línea en el form, la edición
  y el legajo, las cantidades solo enteras, los montos con `$`, el diseño de la
  edición, la columna completa del legajo, los bloques, "Sin información" y el 0.
- `test_issue_2642.py` se adapta: usa `monto_convenio_prestaciones_alimentarias`
  en lugar del campo quitado del form, con el mismo comportamiento probado.
  Pasa junto con `test_issue_2844_tope_nomina_web.py`.
- Los archivos de tests que ya renderizaban el legajo: 221 passed.
- Suite de `src/backends/comedores` con `-n auto`, antes de los ajustes de
  diseño: 2229 passed, 8 failed. Los 8 son ajenos a este cambio:
  - 7 de conteo de consultas en listados del admin (`test_admin_operaciones_*`).
    Se confirmó que fallan igual sin este cambio en
    `test_admin_operaciones_comedores.py`. No se comprobó contra el código
    original `test_admin_operaciones_flujos.py`.
  - `test_issue_2641_c2_http`, que tampoco se comprobó contra el código original.
- `makemigrations --check --dry-run`: sin cambios.
- black y pylint en los Python tocados; djlint en los templates tocados.
  `comedor_detail.html` ya no cumplía djlint antes del cambio; lo reformatea el
  autofix de CI.
- Verificación manual de la solicitante en el entorno local, con un comedor de
  cada línea: orden, campo quitado, validaciones, formato de montos y diseño.

Pendiente: CI y aceptación del área.


## Corrección de revisión: montos decimales pegados (2026-11-11)

El filtrado del evento `input` quitaba la coma de `100,50` y el formateo posterior
lo convertía en `10.050`. Eso evitaba el rechazo existente del formulario y podía
guardar un monto distinto del ingresado. Se elimina únicamente esa transformación:
los formatos inválidos se conservan para que `MontoConvenioField` los rechace.
Los enteros válidos siguen recibiendo puntos de miles al perder el foco; las
restricciones de los campos de cantidades no cambian.

La regresión nueva en `src/backends/comedores/tests/js/convenioPnud.test.js` ejecuta
el estático real siguiendo el patrón de VM/DOM del test de visualización de
rendiciones. Falló antes de corregirlo (`10.050` en vez de `100,50`) y pasa después.
También conserva la cobertura de enteros válidos y del pegado inválido en cantidades.
Se suma a la lista existente de tests JavaScript del workflow de CI, sin cambiar
permisos, secretos ni la política del gate.

Verificación: tests JavaScript focalizados y suite del gate ejecutados localmente;
se comprobó además el rechazo de `100,50` por la clase real de validación de Django
en aislamiento, sin base de datos. Los tests completos de vistas/formularios y el
recorrido real desktop/móvil/accesibilidad quedan pendientes: no está levantado
el entorno local completo. No hubo deploy ni acceso a datos reales.
