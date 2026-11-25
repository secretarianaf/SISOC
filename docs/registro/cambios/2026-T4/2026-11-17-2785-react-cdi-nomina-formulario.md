# Cambio: detalle del formulario de nómina CDI en React sobre G1 v1 (#2785)

## Alcance

Pantalla `/centrodeinfancia/<nómina>/nomina/formulario/` (`nomina_formulario_detail.html`), con el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md) y la decisión de
[acceso conservado](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md). Sigue después de
la [alta y edición de intervenciones](2026-11-17-2785-react-cdi-intervencion-form.md). No activa React
en producción ni cambia el comportamiento nativo. No se consulta ningún servicio externo.

Archivos: `web_api_nomina_formulario.py`, `web_api_urls_nomina_formulario.py`,
`web_preview_nomina_formulario.py`, `cdi_runtime/web_api_urls.py`, `routes/cdiNominaFormulario.tsx` con su
prueba, `admindocs.py` y `url_registry.json`.

## Comportamiento

La API ejecuta `NominaCentroInfanciaFormularioDetailView` (el número de la URL es el id de la nómina, no
el del centro): la ficha se filtra por alcance de provincia y fuera de él responde 404. Delante solo
agrega G1 y el permiso de la URL (`view_nominacentroinfancia`). Cada una de las 51 filas del template se
renderiza con su misma expresión (`default:"-"`, `yesno:"Sí,No,-"`, `date`), de modo que etiquetas de
opciones, fechas locales y booleanos salen idénticos; la pantalla solo dibuja la tabla. Solo lectura
(GET y HEAD).

## Verificación

Entorno sintético, sin red, imagen fijada.

- Backend: 10 pruebas nuevas (paridad de las 51 filas contra el HTML nativo, alcance y 404, lectura sin
  escrituras, 401, 403, requisito pendiente con cabecera falsificada, solo GET, runtime firmado, y la
  entrada de vista previa); black limpio, pylint 10/10; `url_registry.json` regenerado (solo 1 nombre
  agregado).
- Frontend: 3 pruebas de ruta; una corrida completa de `vitest`, `tsc`, `eslint` y `vite build`.
- G1 de punta a punta y visual (S13) escritorio y móvil: ver el resultado en la entrega de la unidad.

## Limitaciones

- La pantalla nativa no tiene encabezado de página (el bloque de título queda vacío); la de React tampoco.
