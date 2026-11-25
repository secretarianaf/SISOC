# Cambio: alta y edición de titulares PAS en React sobre G1 v1 (#2785, PAS06.02)

## Alcance

Formularios `pas/crear` y `pas/<pk>/editar` (`persona_form.html`), según el
[contrato PAS05-PAS06](../../../plans/2026-T4/2026-11-10-2785-pas05-pas06-contratos.md).
No cambia vistas, formularios, servicios, plantillas ni JavaScript nativos, ni activa React en
producción. Como en el contrato, el alta no tiene enlace nuevo (solo URL directa).

Fuera de alcance, sin migrar:

- `/pas/formacion/personas`: fragmento JSON del scroll incremental (AJAX); el área de formación ya
  lo consume por `/api/web/pas/formacion/personas/`.
- `/pas/ddjj/formulario/<token>` y `/pas/ddjj/confirmacion`: ya tienen entrada React sin montar
  (`ddjj_preview.py`) y la valida otro frente; sin cambios.
- `/pas/titulares/importar`: lo toma otro frente.

Archivos:

- `src/backends/pas/pas/web_api_persona_form.py` y rutas en `web_api_urls.py`.
- `src/backends/pas/pas/web_preview_backoffice.py`: entradas locales de `pas/crear` y
  `pas/<pk>/editar` (solo el GET; un POST llega a la vista nativa).
- `src/backends/config/middlewares/admindocs.py` y `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/pasPersonaForm.tsx`, registro en `routes/index.ts`; ajustes
  aditivos en `pasSelect2.tsx` (`invalid`) y `pasCambioEstado.tsx` (avisos iniciales del panel).
- Pruebas: `test_web_pas_persona_form.py`, `test_web_pas_preview.py` (la ruta que se usaba como
  «sigue nativa» pasó a `pas/titulares/importar`) y `pasPersonaForm.test.tsx`.

## Comportamiento

| Ruta | Efecto |
|---|---|
| `GET /api/web/pas/personas/opciones/?provincia=` | provincias, municipios de esa provincia, estados, avisos por estado y géneros, de los querysets del formulario (`add` o `change`) |
| `POST /api/web/pas/personas/crear/` | `PasPersonaCreateForm` + `registrar_persona` en una transacción; 201 `{id, message}` o 400 `{errors}` |
| `GET /api/web/pas/personas/<pk>/` | datos iniciales y opciones; 404 si no existe (`change_paspersona`) |
| `POST /api/web/pas/personas/<pk>/editar/` | `PasPersonaUpdateForm` (sin estado ni avisos); 200 `{id, message}` o 400 |

Acceso: G1 y después la regla nativa de cada ruta. React envía solo los campos que dibuja la plantilla.
El contrato nombraba `POST /personas/` y `.../editar/`; el alta usa `personas/crear/` porque
`personas/` ya es el listado (otra regla de acceso).

## Verificación y limitaciones

Ver el informe de la entrega. Un POST nunca se reintenta; ante un resultado no confirmado la pantalla
lo dice y no guarda dos veces. Quedan las diferencias del marco compartido (menú móvil y nombre
accesible del logo).
