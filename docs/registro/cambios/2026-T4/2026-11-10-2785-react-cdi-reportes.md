# Cambio: pantalla de reportes CDI en React sobre G1 v1 (#2785, CDI08.02)

## Alcance

Primera pantalla del backend CDI que usa el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): el
módulo de reportes de Centros de Desarrollo Infantil
(`/centrodeinfancia/reportes/`), entrega CDI08.02 del contrato
`2026-10-28-2785-cdi-usuarios-reportes-documentacion.md` (pantalla resumen y
XLSX). Sigue el patrón del piloto de
[actas de Inspecciones](2026-11-10-2785-react-inspecciones-actas.md).

React solo muestra el resumen, los selectores y el botón de descarga; no
calcula nada. El XLSX sigue siendo la descarga nativa
(`/centrodeinfancia/reportes/descargar/`), sin cambios. No cambian las vistas,
servicios ni plantillas nativas. No activa React en producción.

Archivos:

- `src/backends/cdi/centrodeinfancia/web_api.py` y
  `src/backends/cdi/centrodeinfancia/web_api_urls.py`: API web.
- `src/backends/cdi/cdi_runtime/web_api_urls.py`: agrupa las rutas
  `/api/web/cdi/` del backend; lo incluye `src/backends/cdi/cdi_runtime/urls.py`.
- `src/backends/config/backends.json`: prefijo `api/web/cdi/` del backend
  `cdi`. `src/backends/config/url_registry.json` se regeneró con
  `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: la ruta nueva queda fuera del
  atajo HEAD de admindocs, como las demás `/api/web/`.
- `src/backends/cdi/centrodeinfancia/web_preview.py`: entrada React sin montar
  (`cdi_preview_patterns`), solo para un URLconf local.
- `src/frontends/apps/sisoc/src/routes/`: `cdiReportes.tsx` (ruta y pantalla) y
  `cdiFrame.tsx` (carga de sesión y datos, marco oscuro).
- Pruebas: `src/backends/cdi/centrodeinfancia/tests/test_web_reportes.py`,
  `src/backends/cdi/centrodeinfancia/tests/test_web_preview.py` y
  `src/frontends/apps/sisoc/src/routes/cdiReportes.test.tsx`.

## Comportamiento

`GET /api/web/cdi/reportes/` reutiliza `ReportesCDIView` para armar el contexto
y devuelve las migas, las provincias del alcance, la provincia pedida tal como
llegó, las variantes disponibles, las columnas y filas de la hoja Resumen (como
texto, igual que las muestra la plantilla), las URLs de la pantalla y de la
descarga y los mensajes pendientes. Solo lectura: no escribe en la base.
Responde JSON `private, no-store` con `Vary: Cookie`; otros métodos, 405.

- La provincia solo acota dentro del alcance; un valor inválido o ajeno no
  amplía nada y la pantalla vuelve a «Todas».
- La variante completa solo se ofrece a superusuario, SIMEPI - Administrador o
  SIMEPI - Equipo Nacional; el resto ve «Reporte disponible: Reducido (campos
  seleccionados).». Editar la URL de descarga no amplía la variante.

Acceso, en este orden: sesión y requisitos web (G1: 401/403 JSON, o la
constancia firmada en el runtime), después la regla nativa
`auth.role_reportes_cdi` o superusuario. `role_exportar_a_csv` no habilita.

Entrada React: en `/centrodeinfancia/reportes/` corre primero el mismo
`permissions_any_required` y el despacho de `ReportesCDIView`; recién después
devuelve el `index.html` congelado. Assets bajo `/centrodeinfancia/react/assets/`.

Pantalla React: marco oscuro (`includes/main.html`) con `SisocShell`, menú y
usuario de `/api/web/session/`. Agrega el botón «Consultas» que
`includes/header.html` muestra en toda ruta `centrodeinfancia` y la clase
`app-loaded` del `body`. El formulario sigue siendo un GET nativo: «Actualizar
resumen» recarga la pantalla y «Descargar reporte (XLSX)» usa `formaction` hacia
la descarga nativa.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo (20 de 23; las 3 restantes fijan la descarga
  nativa) y la entrada sin módulo; luego en verde. Con `test_reportes.py`,
  `test_web_gate`, `test_backend_proxy` y `test_servicios_backends`: 144 pasan.
- Frontend: prueba de ruta en rojo (8 de 8) y luego en verde; Vitest del
  workspace, `tsc`, ESLint y build de Vite.
- Visual (regla S13), nativo contra React, 6 estados en 1440x900 y 390x844:
  contenido y cabecera con el mismo texto, controles, estilos y orden de Tab,
  desvío máximo de 0,02 px y diferencia perceptual máxima de 0,082 %. Mismo
  recorrido de provincia, «Actualizar resumen», variante y descarga (mismo
  archivo, nombre y cabeceras). Anónimo y sin permiso responden igual (403).
- G1 de punta a punta: core y runtime CDI en dos contenedores gunicorn.

## Limitaciones

- Diferencia real en el menú lateral, del marco compartido `SisocShell`: el
  submenú de tercer nivel «Centro de Infancia» (Legajos > Centro de Infancia >
  Ver Centros de Infancia / Reportes) se dibuja como ítem de primer nivel, sin
  `nav-dot ms-2` ni hojas `ms-4`, y desplaza esos ítems hasta 52 px. En móvil el
  árbol abierto queda oculto en la versión nativa (menú móvil fuera de la
  comparación). Corregirlo toca `routes/SisocShell.tsx`, fuera de esta unidad.
- El logo tiene `aria-label` en React (diferencia ya registrada del marco).
- El botón «Consultas» se monta en la lista de la cabecera de `SisocShell`
  desde `cdiFrame.tsx`, porque el marco no tiene un lugar para ítems propios.
