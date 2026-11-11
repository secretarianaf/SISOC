# Cambio: generar usuario referente de un centro CDF en React sobre G1 v1 (#2805, CDF04.03)

## Alcance

Tercera unidad de centros CDF, apilada sobre
[alta, edición y baja](2026-11-10-2805-react-cdf-centros-gestion.md): pantalla
«Generar usuario referente» (`/centrodefamilia/centros/<pk>/generar-usuario/`) y
su resultado con las credenciales. Contrato: CDF04.03 de
[CDF03/CDF04](../../../plans/2026-T4/2026-11-10-2785-cdf03-cdf04-contratos.md);
reglas de negocio y CR1 en
[CDF-E](../../../plans/2026-T4/2026-10-28-2785-cdf-usuarios-cabal-y-credenciales.md).

No cambian la vista `GenerarUsuarioCDFView`, el formulario, el servicio
`generar_usuario_delegado`, las plantillas ni la regla de acceso. No activa React
en producción.

Archivos:

- `src/backends/cdf/centrodefamilia/web_api_usuario.py`: API web; ruta en
  `src/backends/cdf/centrodefamilia/web_api_urls.py`.
- `src/backends/cdf/centrodefamilia/web_preview.py`: entrada de la pantalla.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/cdfCentroUsuario.tsx` (ruta, formulario y
  resultado) y su registro en `src/frontends/apps/sisoc/src/routes/index.ts`.
- Pruebas: `src/backends/cdf/tests/test_web_cdf_usuario.py` y
  `src/frontends/apps/sisoc/src/routes/cdfCentroUsuario.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/cdf/centros/<pk>/generar-usuario/` | Centro, grupo «CDF - Referente centro», cupo restante, `initial` y campos del formulario. Precarga nombre, apellido y correo del referente solo si el centro no tiene ningún `AccesoCDF` (activo o histórico) |
| `POST /api/web/cdf/centros/<pk>/generar-usuario/` | `form_valid` nativo: crea el usuario, el `AccesoCDF` y envía el correo. 201 con solo `usuario {username, email}`, `password`, `email_enviado`, `puede_generar_otro` y `message` («Usuario «{username}» creado correctamente.»); 400 con valores, `errors` y `non_field_errors` (incluye los `ValidationError` del servicio) |

Orden de acceso, igual que hoy: sesión y requisitos web (G1), `view_centro`
(403), centro inexistente o dado de baja (404) y después
`puede_generar_usuario_cdf`: delegación del grupo, territorio y cupo (403). Las
respuestas son `private, no-store`. El mensaje de éxito que encola la vista se
consume en la misma respuesta, como lo muestra hoy la página de resultado, y no
aparece en la página siguiente.

Pantalla React: mismos campos de crispy (`generar_usuario_cdf.html`), mismo
resultado (`usuario_cdf_generado.html`) con campos de solo lectura y «Generar
otro» si queda cupo. La contraseña temporal vive solo en la memoria del
componente: al recargar o salir se pierde y no se repite la creación. Cualquier
resultado que no sea 201 ni 400 muestra «No se pudo confirmar el resultado.
Verificá el estado antes de reintentar.» y no reintenta.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada; correo con el
backend en memoria.

- Backend: 10 pruebas nuevas en rojo sobre la unidad anterior y luego en verde
  (acceso en orden nativo, precarga solo del primer usuario, efectos persistidos,
  proyección CR1, correo fallido, cupo, error del servicio, CSRF y entrada).
  Suite CDF, pruebas de G1 y del proxy, registro de URLs al día, colección
  completa sin errores, `black`, `pylint` 10/10 y `makemigrations --check`.
- Frontend: prueba de ruta en rojo (módulo inexistente) y luego en verde (7);
  Vitest del proyecto sisoc (tres corridas), `tsc`, ESLint y build de Vite.
- Visual (regla S13): formulario con precarga, sin precarga, con errores y
  resultado, en 1440x900 y 390x844: diferencia perceptual 0 % y desvío máximo de
  0,02 px; orden de Tab igual dentro del contenido.
- G1 de punta a punta (core y runtime CDF en dos contenedores): formulario con
  precarga, error de correo, creación con aviso y contraseña, y recarga sin
  contraseña con el cupo descontado. Anónimo 401, sin CSRF 403, sin permiso 403,
  requisito pendiente 403 con `state`, inexistente 404.

## Limitaciones

- Mismas diferencias del marco compartido que las unidades anteriores (enlace
  del logo y menú móvil), fuera del contenido de la pantalla.
- Si una creación queda sin confirmar (504), la contraseña no se recupera desde
  React; el aviso por correo cubre la entrega, igual que al cerrar la página
  nativa después del POST.
