# Cambio: importar titulares PAS en React sobre G1 v1 (#2785)

## Alcance

Pantalla «Importar titulares» (`pas/titulares/importar`, `pas/titulares_import.html`), según el
[contrato PAS05-PAS06](../../../plans/2026-T4/2026-11-10-2785-pas05-pas06-contratos.md)
(`GET/POST /api/web/pas/titulares/importar/`). No cambia vistas, formularios, servicios ni
plantillas nativas, ni activa React en producción.

Quedan fuera, con motivo:

- DDJJ pública (`/pas/ddjj/formulario/<token>` y `/pas/ddjj/confirmacion`): ya la sirve `apps/pas` (#2806,
  `ddjj_preview.py`, ver [registro](2026-11-06-2806-react-ddjj-publica.md)); no se toca ni se agrega acceso anónimo al G1.
- `/pas/crear` y `/pas/<pk>/editar`: otra entrega.
- `.../datos`, `.../enviar` y `.../municipios` de la DDJJ: JSON/POST sin página.

Archivos:

- `src/backends/pas/pas/web_api_titulares_import.py` y la ruta en `src/backends/pas/pas/web_api_urls.py`.
- `src/backends/pas/pas/web_preview_titulares_import.py`: entrada local del GET.
- `src/backends/config/middlewares/admindocs.py` y `src/backends/config/url_registry.json` (una ruta nueva).
- `src/frontends/apps/sisoc/src/routes/pasTitularesImportar.tsx` y su registro en `routes/index.ts`.
- Pruebas: `test_web_pas_titulares_import.py`, `test_web_pas_titulares_import_preview.py` y `pasTitularesImportar.test.tsx`.

## Comportamiento

- Acceso: G1 y después la regla nativa `permissions_any_required(["pas.add_paspersona"])`.
- `GET`: migas de pan y etiqueta/`accept` del campo del formulario nativo; `private, no-store`.
- `POST` (multipart `archivo`): `PasTitularesImportForm` y `importar_titulares_csv` (atómica). 200
  `{"resultado": {total, creados, duplicados, errores}}`; 400 `{"errors": {"archivo": [...]}}` con los textos
  nativos (extensión, 10 MB, columnas faltantes, codificación).
- React: mismo encabezado, texto, campo y botón; resumen «Procesados: … · Nuevos: … · Duplicados omitidos: … ·
  Errores: …» y lista de errores; tras cada envío el campo queda vacío y la página vuelve arriba sin foco.
  Un resultado ilegible o un corte muestra el texto G1 de resultado incierto y no reintenta.

## Verificación

- Backend (imagen fijada, sin red): 8 pruebas nuevas en rojo contra la base (7 fallan, la nativa pasa) y luego
  en verde, más 2 de la entrada local; `src/backends/pas` completo y `web_gate`, `backend_proxy`,
  `servicios_backends` (379 en verde, 1 omitida); `black`; `pylint` 10/10 en los archivos nuevos.
- Frontend: Vitest de `sisoc` completo (1853 de 1855; fallaron `admisionesTemplatesForm` y
  `comedorValidacion` por tiempos bajo carga, ambos verdes aislados), `tsc`, ESLint y `vite build`.
- G1 de punta a punta: anónimo 401 (GET y POST), sin permiso 403, requisito pendiente 403, encabezado falsificado
  ignorado, POST sin CSRF 403, GET 200; importación 200, repetición con duplicado, extensión inválida 400.
- Visual (S13, 1440x900 y 390x844): formulario, resultado (duplicado más dos errores) y archivo rechazado: 0,000 %
  de píxeles distintos, desvío 0,00 px, mismo orden de Tab; guardas anónimo, lector y sin permiso iguales (403).

## Limitaciones

- La importación es síncrona hasta 250.000 filas; por G1 el corte es de 60 s y un 504 no se reintenta solo
  (repetir es seguro: los DNI y CUIT existentes se omiten).
- El caso «Nuevos > 0» no está en la comparación visual (la segunda pasada vería duplicados); lo cubren Vitest y G1.
- Exenciones del marco: menú móvil y nombre accesible del logo.
