# Cambio: rutas React de `apps/sisoc` por módulo (#2785)

## Alcance

Refactor sin cambio de comportamiento de la app React
`src/frontends/apps/sisoc`. `src/frontends/apps/sisoc/src/App.tsx` concentraba
la cadena de `if (pathname === …)` de todas las pantallas, el marco SISOC, el
arranque de sesión de negocio, el ruteo interno de insumos y categorías y los
marcos de identidad. Cada pantalla nueva obligaba a editar ese archivo y
`App.test.tsx`, por lo que dos unidades en paralelo chocaban siempre en los
mismos archivos. No modifica backend, estilos, textos, rutas públicas ni la app
`apps/pas`.

## Comportamiento

- `src/frontends/apps/sisoc/src/routes/index.ts` declara `ROUTES`, una lista
  tipada de `RouteDefinition` (`name`, `match(pathname)` que devuelve
  parámetros o `null`, y `render(params)`). `App.tsx` solo busca la primera
  coincidencia y la monta; sigue importando `shell.css` después de las
  pantallas, así que el CSS generado no cambia.
- Un módulo por unidad en `src/frontends/apps/sisoc/src/routes/`: `groups.tsx`,
  `inicio.tsx`, `login.tsx`, `requiredPassword.tsx`, `account.tsx`,
  `passwordChange.tsx` y `passwordReset.tsx`, en el mismo orden de precedencia
  que la cadena anterior. El último registro, `businessRoute` (`business.tsx`),
  acepta cualquier otra ruta y monta `BusinessApp.tsx`, que carga
  `/api/web/session/` como antes.
- Dentro del marco de negocio, `SHELL_ROUTES` reemplaza el ruteo fijo de
  insumos: `categorias.tsx` (todo lo que empieza con
  `/v2/sisoc/insumos/categorias/`, con los slashes exactos del circuito
  original) y `insumos.tsx` (formularios con slash final opcional y, para
  cualquier otra ruta, el listado). Cada uno declara su título, su ruta de
  listado para volver después de guardar o cancelar y su contenido. El marco
  conserva su propio estado de ruta, así que volver al listado sigue sin
  recargar la página.
- `SisocShell` pasa sin cambios de salida a `routes/SisocShell.tsx`: alias
  `/v2/sisoc/insumos` en el ítem activo, rama de Administración cerrada en
  `/grupos/`, enlaces de vista previa, orden de Tab del sidebar nativo y sin
  regla de foco propia.
- Los marcos de identidad (`legacyIdentityFrame`, cambio obligatorio, cuenta,
  confirmación, portada y grupos) pasan a
  `src/frontends/apps/sisoc/src/identityFrames.tsx`.
- Las pruebas de ruta salen de `App.test.tsx` a un archivo por módulo
  (`insumos`, `categorias`, `requiredPassword`, `groups`, `inicio`,
  `passwordReset`), sin cambiar sus aserciones; los datos compartidos están en
  `routes/testFixtures.ts`. `App.test.tsx` conserva el marco, el arranque de
  sesión y la tabla de operaciones por ruta de identidad. La prueba nueva
  `routes/index.test.ts` fija la precedencia del registro y la del ruteo
  interno.

Para agregar una pantalla se crea `routes/<unidad>.tsx` con su prueba y se
registra en `routes/index.ts`; ver
`docs/implementaciones/frontend_v2.md`, sección «Agregar una pantalla React en
`apps/sisoc`».

## Verificación

Copia aislada sobre el árbol con PAS01 (`953ab326`):

- Pruebas: las 202 pruebas de `apps/sisoc` pasan antes y después. Las pruebas
  movidas pasan también contra el `App.tsx` anterior (202 de 202), lo que
  confirma que verifican el mismo comportamiento. Con las 34 nuevas del
  registro quedan 236 en `apps/sisoc` y 344 en todo el workspace; las
  aserciones pasan de 680 a 689 (las 135 de `App.test.tsx` se conservan
  repartidas). TypeScript, ESLint y el build de Vite pasan; el CSS generado es
  idéntico byte a byte al de la base.
- Runtime sintético local, solo GET, comparando el build React de la base con
  el del cambio (no con la página original), en 1440x900 y 390x844, dos cargas
  por lado: 38 casos (listado, alias, alta, edición, baja y cancelar de
  insumos; listado, alta, edición, baja, cancelar y acceso denegado de
  categorías; login en `/` y `/login/`; cambio obligatorio; cuenta y
  confirmación; grupos con editor, lector, superusuario, modal de columnas,
  alta y edición; portada y tres encuestas; cambio voluntario y su
  confirmación; las siete pantallas de recuperación). Las 76 combinaciones
  de caso y tamaño dan capturas idénticas byte a byte, con la misma geometría,
  título, ruta final y clases del `body`. Al cancelar, ambos builds vuelven a
  la ruta de listado con el mismo título.
- Recorrido de 16 Tab en 16 pantallas y ambos tamaños, base contra cambio:
  mismo elemento, contorno y desplazamiento en cada paso. Solo cuenta y
  confirmación muestran variaciones de 1/64 a 3/64 px en la posición del botón
  «Guardar datos» y una franja de texto de 36 px; las mismas variaciones
  aparecen comparando la base contra sí misma en cargas sucesivas, así que son
  propias del render y no del cambio.

No hubo POST, errores de página ni solicitudes bloqueadas; dominio sintético
sin cambios. No constituye aceptación humana, CI ni despliegue.

## Riesgos y límites

- Marco compartido: el cambio mueve el código de todas las pantallas React de
  `apps/sisoc`; el comportamiento queda fijado por las pruebas movidas y por la
  comparación visual y de teclado descrita.
- `insumosRoute` y `businessRoute` aceptan cualquier ruta; deben seguir últimos
  en sus listas. `routes/index.test.ts` falla si eso cambia.
