# Cambio: alta y edición de Dispositivos en React sobre G1 v1 (#2785, DS03)

## Alcance

Alta (`/dispositivos/crear`) y edición (`/dispositivos/<pk>/editar`) del backend
`dispositivos`, con la misma URL, permisos y mensajes que las vistas nativas
(`DispositivoCreateView` y `DispositivoUpdateView`). Sigue el patrón de
[listado, legajo y mapa](2026-11-11-2785-react-dispositivos-consulta.md) y de los
formularios de CDI. No activa React en producción.

Sin migrar, por no ser pantallas: `/dispositivos/<pk>/ubicacion/`
(`DispositivoLocationView`, consulta JSON que ya usan el mapa y el editor de pin) y
`/dispositivos/ubicacion/previsualizar/` (POST JSON). La baja
(`/dispositivos/<pk>/eliminar`) queda para otra unidad.

Archivos:

- `src/backends/dispositivos/dispositivos/web_api_dispositivo_form.py` y
  `src/backends/dispositivos/dispositivos/web_api_urls.py`: API web (`crear/` y
  `<pk>/editar/`).
- `src/backends/dispositivos/dispositivos/web_preview_dispositivo_form.py`: entradas
  React sin montar, solo para un URLconf local.
- `src/backends/config/middlewares/admindocs.py`: las rutas nuevas quedan fuera del
  atajo HEAD de admindocs. `src/backends/config/url_registry.json` se regeneró con
  `generar_registro_urls`.
- `src/frontends/apps/sisoc/src/routes/`: `dispositivoForm.tsx` (ruta y pantalla),
  `dispositivoFormCampos.tsx` (campos, grupos, adjuntos y reglas del script),
  `dispositivoFormMapa.tsx` (editor de pin), `dispositivoFormTextos.ts` (títulos de
  las nueve secciones) y su registro en `index.ts`.
- Pruebas: `test_web_dispositivos_formulario.py`,
  `test_web_dispositivos_formulario_preview.py` y `dispositivoForm.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/dispositivos/crear/` | Corre `DispositivoCreateView`. Campos del template (etiqueta, widget, valor, opciones, errores), grupos de casillas, cinco adjuntos y migas |
| `GET /api/web/dispositivos/<pk>/editar/` | Igual con el dispositivo en alcance; fuera de alcance o inexistente, 404 |
| `POST` en ambas | Cuerpo `multipart/form-data` o urlencoded (otro formato, 415). Guarda con el formulario nativo; el alta o el cambio devuelven `{"ok": true, "redirect": <legajo>}` y el mensaje queda en cola para el legajo. Un formulario inválido devuelve 400 con el mismo cuerpo que el GET |

Acceso, en este orden: sesión y requisitos web (G1), después el mismo permiso que
la ruta nativa (`add_dispositivo` o `change_dispositivo`) y la regla de alcance
territorial del formulario. Respuestas `private, no-store`; CSRF obligatorio.

En pantalla se reproducen los scripts nativos: progreso por sección, secciones
plegables (ratón y teclado), campos «Otro», solo números en CUIT, DNI y teléfono,
municipios y localidades por AJAX, previsualización de ubicación y editor de pin, y
los adjuntos (vista previa, quitar, marcar para eliminar y añadir hasta cinco).
Tras un rechazo, la página vuelve arriba como la recarga nativa.

## Verificación

Pruebas del backend y del front con RED antes de las rutas; comprobación G1
(anónimo 401, sin permiso 403, CSRF 403, cabecera falsificada ignorada, camino
feliz) y paridad visual contra la página nativa.

## Límites

La baja y el listado de adjuntos guardados dependen de `/media/`, que el front sirve
tal cual. Sin cambios de modelo ni de migraciones.
