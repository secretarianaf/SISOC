# Cambio: listado de centros CDI en React sobre G1 v1 (#2785, CDI09.01)

## Alcance

Tercera entrega del backend CDI sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): el
listado de Centros de Desarrollo Infantil (`/centrodeinfancia/listar`), primera
parte de CDI09.01 del contrato `2026-10-28-2785-cdi-centros-y-credenciales.md`.
Ficha, alta, edición, baja, RENAPER y credenciales siguen nativos. No activa
React en producción y no cambia el comportamiento nativo.

Archivos:

- `src/backends/cdi/centrodeinfancia/web_api_centros.py` y `web_api_urls.py`: API.
- `src/backends/cdi/centrodeinfancia/web_preview.py`: entrada de vista previa.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/cdiCentros.tsx` y su prueba; registro en
  `routes/index.ts`.
- Pruebas: `src/backends/cdi/centrodeinfancia/tests/test_web_centros_lista.py` y
  un caso en `test_web_preview_cdi.py`.

## Comportamiento

`GET /api/web/cdi/centros/` ejecuta `CentroDeInfanciaListView` (alcance, búsqueda,
filtros avanzados, orden por nombre, páginas exactas de 10 y preferencias de
columnas) y proyecta su contexto: migas, configuración de filtros, columnas,
filas con el texto y el valor de orden de cada celda (`partials/rows.html`),
paginación con el prefijo de enlaces nativo, `can_export` y, solo para
superusuarios y EGP SIMEPI, las provincias del modal «Descargar nómina de niños».
Una página inválida responde 404 como la nativa.

Acceso, en este orden: G1 y después `centrodeinfancia.view_centrodeinfancia`
(con el bypass de superusuario), igual que la URL nativa. Solo GET y HEAD.

La pantalla React reproduce el marcado nativo: barra de búsqueda con filtros,
tabla `table-comedor-moderno` con orden local (`listSort.js`), «Configurar
columnas», acciones Ver, Editar y Eliminar hacia las páginas nativas,
paginación «Volver» y «Continuar», botón «Exportar búsqueda» (navegación al CSV
con la consulta y el orden) y el modal de nómina de niños.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 22 pruebas nuevas en rojo (17 fallaban sin el código; las 5 restantes
  son rechazos de la puerta G1 que ya existían) y luego en verde, incluidas las
  que comparan cada celda con el HTML nativo. Suite de CDI, `test_web_gate`,
  `test_backend_proxy`, `test_servicios_backends` y `config`: 1096 pasan y 3 se
  omiten; `makemigrations --check` sin cambios; black y pylint 10/10.
- Frontend: pruebas de ruta en rojo (módulo inexistente) y luego en verde; una
  corrida completa de `vitest` (673), `tsc`, `eslint` y `vite build`.
- G1 de punta a punta (core y runtime con gunicorn): anónimo 401, sin permiso
  403, CSRF 403, cabecera falsificada ignorada y camino feliz.
- Visual (regla S13), escritorio y móvil, listado, página 2 y lector con
  alcance: diferencia de píxeles de 0,003 % como máximo, mismo texto, controles
  y geometría fuera del menú lateral.

## Limitaciones

- Diferencia ya conocida del marco compartido: en el orden de tabulación el
  logotipo de `SisocShell` tiene otro nombre accesible, y el menú móvil difiere.
- El modal de columnas y el de nómina de niños no se compararon píxel a píxel.
- La diferencia del menú lateral de tercer nivel registrada en
  [reportes](2026-11-10-2785-react-cdi-reportes.md) también aparece acá.
