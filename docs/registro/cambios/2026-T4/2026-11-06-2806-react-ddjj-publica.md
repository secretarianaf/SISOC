# Cambio: DDJJ pública PAS en React sobre transporte JSON propio (#2806, P1)

## Alcance

Implementa el contrato
[DDJJ pública PAS](../../../plans/2026-T4/2026-10-27-2806-ddjj-publica-pas.md)
con la política P1 ya elegida
([decisión](../../decisiones/2026-10-27-2806-ddjj-pas-p1.md)): formulario de
cinco pasos, validaciones visibles, modales, errores 400, 404/410 y
confirmación, con el CSS, la marca y las fuentes propias de PAS. No cambia el
formulario `PasDeclaracionJuradaForm`, el servicio `presentar_ddjj`, las
plantillas, el JavaScript nativo, la descarga autenticada ni el bloqueo de
media. No activa React en producción.

Archivos:

- `src/backends/pas/pas/web_ddjj.py` y `src/backends/pas/pas/web_ddjj_urls.py`:
  transporte JSON, incluido desde `src/backends/pas/pas/urls.py`; nombres
  nuevos en `src/backends/config/url_registry.json` generados con
  `generar_registro_urls`.
- `src/backends/pas/pas/ddjj_preview.py`: entrada React sin montar
  (`ddjj_preview_patterns`), solo para un URLconf local de vista previa.
- `src/frontends/apps/pas/`: app React propia (`@sisoc/pas`, base `/v2/pas/`),
  registrada como proyecto de Vitest y como workspace en `package-lock.json`
  con las versiones existentes de React; no toca `apps/sisoc`.
- Pruebas: `src/backends/pas/pas/tests/test_web_ddjj.py`,
  `src/frontends/apps/pas/src/DdjjForm.test.tsx` y `App.test.tsx`.

## Comportamiento

Rutas JSON (elección técnica de esta unidad, a falta de definición en el
contrato): quedan bajo la URL canónica de la invitación, fuera de `/api/`, para
que los middleware de sesión web apliquen igual que en el formulario HTML. En
la composición dividida el core las reenvía al backend PAS por el prefijo
`pas/` existente, después de correr sus propios middleware.

| Ruta | Comportamiento |
|---|---|
| `GET /pas/ddjj/formulario/<token>/datos` | Disponible: 200 con los valores iniciales que renderiza el Form, banderas de datos existentes, etiquetas, provincias, municipios de la provincia inicial y URLs; fija la cookie CSRF. Inexistente: 404. Utilizada, revocada o vencida: 410 `{"detail": "Este enlace ya fue utilizado o se encuentra vencido."}` |
| `POST /pas/ddjj/formulario/<token>/enviar` | URL-encoded con los mismos campos del formulario nativo y CSRF obligatorio (también para visitantes anónimos). Inválido: 400 con `errors` y los valores ligados. Válido: `presentar_ddjj` y 200 `{"redirect": "/pas/ddjj/confirmacion"}`. No disponible, incluso si se pierde durante el envío: 410 sin escrituras |

Ambas respuestas son `private, no-store`. `/municipios` se reutiliza sin
cambios. Con sesión restringida (acceso web denegado, cambio de contraseña,
confirmación de datos o encuesta obligatoria) la entrada, los datos, los
municipios, el envío y la confirmación devuelven el mismo 403 o redirect que
el formulario nativo.

Entrada React: en la URL canónica, solo una invitación disponible recibe el
`index.html` congelado; una inexistente o no disponible y cualquier POST
reciben la respuesta nativa, por lo que 404/410 se ven idénticos. La
confirmación usa el mismo `index.html`. Los assets se sirven desde
`/pas/ddjj/react/assets/` (prefijo propio de PAS, sin enviar token ni cookie a
un servidor estático) con caché inmutable y `nosniff`; cualquier query o
archivo fuera del build devuelve 404. El router genérico `/v2/` no cambia.

La app React reproduce `pas_ddjj.js`: validación por paso con
`reportValidity`, preguntas condicionales deshabilitadas al ocultarse, resumen
con las etiquetas visibles, carga de municipios con los mismos textos de
espera, selección y falla, foco inicial de los modales y desplazamiento al
cambiar de paso. Un 400 muestra el primer paso con errores. El envío se hace
una sola vez: ante 404/410, sesión restringida, rechazo CSRF, error o pérdida
de respuesta, React navega con GET a la URL canónica y nunca repite el POST.
Si la carga de datos pierde disponibilidad, reemplaza la página por la URL
canónica, que entrega la respuesta nativa.

### Hallazgo para decisión de producto: respuestas invertidas tras un 400

Las preguntas visibles de gastos y divisas son la negación de los campos
`gastos_bajo_limite_smvm` y `no_accedio_mercado_cambios`, y `pas_ddjj.js`
intercambia los valores de esos radios. En el envío inicial la correspondencia
es correcta:

| Pregunta visible | Opción visible | Valor enviado | Dato guardado |
|---|---|---|---|
| ¿Gastos superaron 1 SMVM? | Sí | `gastos_bajo_limite_smvm=no` | `False` |
| ¿Gastos superaron 1 SMVM? | No | `gastos_bajo_limite_smvm=si` | `True` |
| ¿Accediste al Mercado de Cambios? | Sí | `no_accedio_mercado_cambios=no` | `False` |
| ¿Accediste al Mercado de Cambios? | No | `no_accedio_mercado_cambios=si` | `True` |

Defecto nativo comprobado en navegador: cuando el servidor responde 400,
Django marca el radio cuyo valor original coincide con el enviado y el script
vuelve a intercambiar los valores, de modo que ambas respuestas reaparecen en
la opción visible contraria. Si la persona corrige otro campo y reenvía sin
notarlo, se guarda la respuesta opuesta. React lo reproduce a propósito
(`answersAfterServerError` en `src/frontends/apps/pas/src/ddjj.ts`) para no
introducir un cambio funcional no pedido; corregirlo en ambas versiones
requiere decisión del responsable.

## Verificación

Copia aislada del árbol base `f0a36a9f`, imagen fijada, SQLite y datos
sintéticos (sin datos reales ni tokens emitidos):

- Backend: RED 10 fallos y 6 errores (sin rutas ni entrada); GREEN 16 tests
  propios. Suite PAS completa más `kernel/tests/test_servicios_backends.py`
  (incluido `test_registro_de_urls_al_dia`): 158 aprobados, 1 omitido. Black,
  Pylint 10/10 y `makemigrations --check --dry-run` sin cambios. Con
  `pas_runtime.settings` las rutas nuevas resuelven en el backend PAS y con
  `config.settings` el core las reenvía por `backend_proxy_pas_pas`.
- Comparación base contra candidato de 102 respuestas (rutas PAS sin
  parámetros para anónimo, usuario y superusuario; formulario, municipios,
  confirmación, descarga y media con invitaciones en todos sus estados; POST
  inválido, válido y reutilizado): sin diferencias fuera de `/datos` y
  `/enviar`. Exportación de tokens, panel y PDF difieren también entre dos
  ejecuciones del base (marcas de tiempo).
- Frontend: 15 tests de Vitest (RED con los módulos ausentes; una mutación que
  elimina la inversión hace fallar tres), `tsc`, ESLint y build de Vite.
- Visual: 28 casos del manifiesto PAS en escritorio 1440×900 y móvil 390×844,
  dos cargas por lado, nativo del base contra React del candidato. Todos con 0
  píxeles distintos, geometría idéntica y repeticiones estables, incluidos
  cinco pasos, ramas condicionales, ambas preguntas invertidas, modales,
  errores 400 (contacto, municipio tras cambiar la provincia), bloqueo de
  respuesta dependiente en cliente, carga y falla de municipios, 404, 410
  (utilizada, revocada, vencida), confirmación tras envío y directa, y las
  cuatro sesiones restringidas. El 404 se comparó con `DEBUG=False`: con
  `DEBUG=True` Django lista los patrones de URL, que difieren por diseño.

Límites: las fuentes de Google se bloquearon en ambos lados (sin red), por lo
que la comparación usa las fuentes de reserva del CSS. El 400 por respuesta
dependiente y por municipio de otra provincia no se alcanza desde la UI (la
validación del cliente y la recarga de municipios lo impiden); quedan cubiertos
por tests. No se probaron concurrencia entre envíos con base autorizada,
pérdida real de red, CI, prueba guiada ni aceptación humana.
