# Cambio: alta, edición y baja de Duplas en React sobre G1 v1 (#2785, DU01.02)

## Alcance

Alta (`/equipo-tecnico/crear/`), edición (`/equipo-tecnico/<pk>/editar/`) y
baja lógica (`/equipo-tecnico/<pk>/eliminar/`) de equipos técnicos, del
[contrato de Duplas](../../../plans/2026-T4/2026-10-28-2785-duplas-equipo-asignaciones-m2.md)
(DU01.02). Se apoya en el
[listado y la ficha](2026-11-10-2785-react-duplas-listado.md) (DU01.01). La
asignación a un comedor (`dupla_asignar`) queda afuera.

No cambia vistas, formularios, señales ni plantillas nativas. No activa React
en producción.

Archivos:

- `src/backends/comedores/duplas/web_api.py` y
  `src/backends/comedores/duplas/web_api_urls.py`: rutas `crear/`,
  `<pk>/editar/` y `<pk>/eliminar/`.
- `src/backends/comedores/duplas/web_preview.py`: entradas sin montar de las
  tres pantallas.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/`: `duplasFormRoute.tsx` (ruta),
  `duplasForm.tsx` y `duplasSelect2.tsx`.
- Pruebas: `src/backends/comedores/duplas/test_web_duplas_form.py`,
  `src/backends/comedores/duplas/test_web_duplas_preview.py` y
  `src/frontends/apps/sisoc/src/routes/duplasForm.test.tsx`.

## Comportamiento

| Ruta | GET | POST |
|---|---|---|
| `/api/web/comedores/duplas/crear/` | Campos de `DuplaForm`: etiquetas, opciones (técnicos del grupo «Tecnico Comedor», abogados de «Abogado Dupla», sin filtro de activos; grupo faltante, lista vacía), valores y errores | Corre `DuplaCreateView.post`. Válido: `{"ok": true, "redirect": "/equipo-tecnico/"}` y el mensaje «Equipo técnico creado correctamente.» queda para el listado. Inválido: 400 con errores y «Error al crear el Equipo técnico.» |
| `/api/web/comedores/duplas/<pk>/editar/` | Igual, con los valores actuales y el coordinador en solo lectura | Corre `DuplaUpdateView.post`. Sin mensaje de éxito, como hoy |
| `/api/web/comedores/duplas/<pk>/eliminar/` | Nombre en mayúsculas y vista previa de la cascada (`cascade_preview`) | Corre `DuplaDeleteView.post`: `delete(user, cascade=True)` y «Equipo técnico dado de baja correctamente.» |

- El coordinador no es campo del formulario: se asigna desde Usuarios. Las
  señales de `duplas/signals.py` actúan igual porque el guardado es el del
  ModelForm nativo. Las pruebas comparan contra la vista HTML el resultado
  completo: campos, técnicos, coordinador, `coordinadores`, `deleted_at`,
  `deleted_by` y el comedor asociado.
- Un id que no está entre las opciones (abogado fuera del grupo, coordinador
  como técnico, id inexistente) se rechaza con 400.
- Acceso: el mismo de DU01.01 (G1 y `auth.role_admin`), más CSRF de la sesión
  en cada POST. Un equipo inexistente o ya dado de baja responde 404. PUT,
  PATCH y DELETE responden 405.
- Pantalla React: mismo marcado que `dupla_form.html` (crispy: errores bajo el
  campo, `aria-invalid`) y `delete_confirm.html`. Hace un solo POST. Si la
  respuesta no confirma el resultado, muestra «No se pudo confirmar el
  resultado» y no reenvía. El selector de técnicos reproduce Select2 4.1
  múltiple: chips con cruz, búsqueda sin acentos, «Sin resultados», Enter sobre
  una opción ya elegida solo cierra, Backspace quita el último y deja su texto,
  y se cierra al elegir.

## Diferencia con la página nativa

Hoy un alta inválida en la página nativa responde 500: `DuplaCreateView.post`
no fija `self.object` antes de `form_invalid` (`AttributeError`). La API lo fija
como hace `CreateView.post` de Django, así que el alta inválida muestra los
errores y el aviso general que describe el contrato. La página nativa no se
toca. Una prueba fija el 500 actual. La corrección nativa queda para otro
cambio. La validación del navegador (`required`) frena antes los campos
vacíos en las dos versiones.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas en rojo (13 de 18) y luego en verde. Suite de Duplas,
  `test_web_gate`, `test_backend_proxy` y `test_servicios_backends`: 153 pasan.
  `black`, `pylint` 10/10, `makemigrations --check` y `check` sin cambios.
- Frontend: prueba de ruta en rojo (sin módulo) y luego 8 de 8. Vitest del
  workspace (421), `tsc`, ESLint y build de Vite.
- Visual (regla S13), 4 estados (alta, edición con coordinador, edición con
  varios técnicos, confirmación de baja) en 1440x900 y 390x844: 0 % de píxeles
  distintos, desvío máximo 0,02 px. Recorrido nativo contra React (16 pasos
  iguales): Select2 (abrir, buscar, Enter, «Sin resultados», Backspace, cruz),
  edición inválida (mismos errores; 0 % de píxeles), alta con redirección y
  aviso, y baja con aviso y ficha 404 después.
- G1 de punta a punta: core y runtime de Comedores en dos contenedores gunicorn
  sobre una red interna. Listado, ficha, alta, edición y baja por core →
  compuerta → runtime, con los avisos esperados. Anónimo 401, sin rol 403,
  requisito pendiente 403 con `state`, POST sin CSRF 403 y el header del
  cliente descartado. Contra el runtime directo, una constancia faltante,
  falsa, alterada, de otro destino, audiencia o usuario, vencida (61 s) o
  futura responde 403, y una de 58 s responde 200. En las pruebas del runtime,
  una constancia firmada para GET no habilita un POST.

## Limitaciones

- Las opciones del `<select multiple>` oculto (recortado a 1 px, como lo deja
  Select2) quedan 23 px más arriba dentro de esa caja en la edición inválida.
  No se ven y los píxeles son iguales.
- El desplegable abierto de Select2 se comparó por recorrido, no por captura.
- El clic sobre una opción ya elegida la quita (comportamiento de Select2 4.1
  con el mouse). No se comparó en el recorrido.
