# Cambio: ficha de un trabajador del centro CDI en React sobre G1 v1 (#2785, CDI05)

## Alcance

Primera entrega de la lane C5 (formularios institucionales y trabajadores) sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): la ficha de
solo lectura de un trabajador (`/centrodeinfancia/<centro>/trabajadores/<trabajador>/`,
`centrodeinfancia_trabajador_ver`), parte de CDI05 del contrato
`2026-10-28-2785-cdi-formularios-trabajadores-m2.md`. El alta y la edición del
trabajador y los formularios institucionales siguen nativos. No activa React en
producción y no cambia el comportamiento nativo. No se consulta RENAPER ni ningún
servicio externo.

Archivos:

- `src/backends/cdi/centrodeinfancia/web_api_trabajador_detalle.py` y
  `web_api_urls_trabajadores.py`; `cdi_runtime/web_api_urls.py` solo agrega el include.
- `src/backends/cdi/centrodeinfancia/web_preview_trabajadores.py`: entrada de vista previa.
- `src/backends/config/middlewares/admindocs.py` y `url_registry.json`.
- `src/frontends/apps/sisoc/src/routes/cdiTrabajadores.tsx` y su prueba, más el
  registro en `routes/index.ts`.
- Pruebas: `tests/test_web_trabajador_detalle.py` y `tests/test_web_preview_trabajadores.py`.

## Comportamiento

`GET /api/web/cdi/centros/<pk>/trabajadores/<trabajador_id>/` ejecuta
`TrabajadorCentroInfanciaDetailView`: el trabajador sale del alcance del actor y del
centro anidado, y cualquier par fuera de él responde 404. Cada campo de
`trabajador_detail.html` se renderiza con la misma expresión del template
(`{{ expresión|default:"—" }}`) y una prueba compara todos los pares etiqueta y valor con
el HTML nativo. El CUIT muestra «No posee CUIL» con la casilla marcada y las listas de
insignias (capacitaciones, grupos, lenguajes, tipo de discapacidad) solo aparecen si hay
valores, con la clase de contenedor del template (`mt-3`, `mb-3` o ninguna).

Acceso: G1 y después `centrodeinfancia.view_trabajador`, como la URL nativa (sin
cambios, ver la decisión de brechas de acceso conservadas). Solo GET y HEAD. El enlace
Editar y el botón Eliminar siguen `change_trabajador` y `delete_trabajador`; la baja es
el endpoint existente `/api/web/cdi/centros/<pk>/trabajadores/<id>/eliminar/`, que ejecuta
`TrabajadorCentroInfanciaDeleteView` con el veto de auditoría CDI-A3, la baja lógica y el
mensaje «Trabajador eliminado correctamente.» en la ficha del centro.

La pantalla dibuja las tarjetas plegables del marcado nativo (encabezado con
`role="button"`, `tabindex="0"`, `aria-expanded`, Enter y Espacio) y el modal de baja en
su posición nativa con la trampa de Tab.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 14 pruebas nuevas (paridad con el HTML nativo, secciones e insignias, enlaces
  por permiso, alcance e ids anidados, lecturas sin escritura, 401, 403, requisito
  pendiente, cabecera falsificada, métodos, admindocs, runtime firmado) y 4 de vista
  previa; escritas junto con la implementación, sin corrida previa en rojo. black y
  pylint 10/10; `makemigrations --check` sin cambios; `url_registry.json` regenerado.
- Frontend: 10 pruebas de ruta; una corrida completa de `vitest`, `tsc`, `eslint` y
  `vite build`.
- G1 de punta a punta y visual (regla S13): ver la entrega.

## Limitaciones

- El plegado no anima como el colapso de Bootstrap: alterna la clase `show`.
- Mismas diferencias del marco compartido que el
  [listado](2026-11-12-2785-react-cdi-centros-listado.md).
