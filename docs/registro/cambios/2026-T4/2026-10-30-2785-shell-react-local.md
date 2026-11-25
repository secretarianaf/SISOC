# Shell React local de SISOC (#2785)

## Alcance

Se agrega `src/frontends/apps/sisoc`, una app local Vite/React que prepara el
marco del piloto INS-A y obtiene el contexto web por sesión Django. Esta unidad
no habilita el módulo `/v2/sisoc/` en el backend, no añade APIs de negocio y no
implementa el listado/formulario de Insumos. No cambia templates Django ni
reglas de acceso.

## Comportamiento

- La app solicita una vez `GET /api/web/session/` mediante el cliente
  `@sisoc/api`, que conserva cookies de sesión y CSRF.
- El shell privado se representa solo si el contexto tiene forma válida,
  `access.state = ready`, usuario disponible y los nodos base esperados. Un
  error, 401, estado desconocido o payload inválido falla cerrado.
- Los estados de requisito muestran una acción local validada; no renderizan
  identidad, navegación ni contenido de negocio. Las capacidades recibidas solo
  reflejan el menú y no autorizan acciones. `can_view=false` no bloquea el shell
  global: los permisos por operación siguen siendo independientes.
- El proxy local reenvía rutas legacy fuera del namespace de React, API, static
  y recursos internos de Vite al backend sintético en loopback, preservando
  `Host`/origen para el flujo normal de sesión y CSRF. No cambia configuración
  del backend ni activa rutas globales.
- El menú usa el orden y la jerarquía proyectados por backend. Solo el destino
  Insumos se remapea al path local del piloto; la navegación del menú no es una
  nueva fuente de permisos.
- La cuenta se coloca arriba del menú principal como en la referencia aprobada;
  Mi cuenta usa Font Awesome, Comunicados Bootstrap Icons y las entradas Inicio,
  Legajos y Configuración de Comedores usan los SVG legacy existentes. Las
  tipografías Nunito y Montserrat se declaran con sus URLs legacy exactas.
- El shell replica los elementos estructurales legacy y carga CSS/fonts/assets
  existentes. Usa un drawer móvil con botón accesible y Escape; no integra MUI,
  Sentry, HTML Django embebido ni nuevos paquetes.
- Vite se monta localmente en `/v2/sisoc/` y limita sus proxies a loopback para
  API web, API Insumos y static. No toca `FRONTEND_V2_UPSTREAMS`.

## Verificación

RED observado: los seis tests públicos de `App` fallaron inicialmente porque
`App` no existía en el snapshot de validación. Tras implementar el shell, la
primera ejecución reportó tres errores de test: consulta de un `crearCliente`
que se inicializa al importar el módulo, acceso a un link dentro de un grupo que
debía abrirse por ruta activa y una aserción async mal parentizada. La ruta de
ancestro se corrigió para evaluar el href local proyectado recursivamente; las
aserciones se alinearon a la inicialización y al rechazo fail-closed del URL
externo.

La verificación independiente del primer candidate observó además que login,
logout y `/inicio/` devolvían 404 a través del Vite local; que sólo cargaba
Montserrat; y que la cuenta e iconos no correspondían a la referencia. Los
tests de regresión observaron RED para el proxy legacy ausente y para Cuenta en
el orden inferior. La corrección incorpora un proxy local que excluye rutas de
la app/API/static y runtime Vite, preserva el Host (`changeOrigin=false`), añade
los CSS remotos originales ya presentes en el cache público y reemplaza
caracteres aproximados por los iconos legacy.

GREEN: `node node_modules/vitest/vitest.mjs run apps/sisoc/src/App.test.tsx
apps/sisoc/src/localProxy.test.ts --reporter=dot` con Node 22.14.0, en la copia
aislada con dependencias ya instaladas, terminó con 8 tests aprobados. Las
pruebas incluyen los destinos legacy login/logout/inicio/cuenta/prerrequisito,
exclusión de las rutas React/API/static, preservación de origin, orden de la
cuenta, iconos, POST de logout con CSRF, errores 401 sin reintento y shell sin
`can_view`. `tsc -p tsconfig.json --noEmit` y `vite build --config vite.config.ts`
también terminaron correctamente con las dependencias existentes.

No se volvió a ejecutar el navegador ni se inició un servidor durante esta
corrección; el test de componentes/configuración no demuestra que el proxy POST
funcione contra Django ni que Nunito se descargue/renderice en navegador. El
build deja referencias a los CSS legacy `/static/...` para runtime. El padre
debe repetir el recorrido sintético limitado de login/logout/navegación y las
comprobaciones de fuentes antes de aceptar la corrección. La prueba no autoriza
datos reales, backend global, publicación o aceptación del piloto. Completar el
outlet de negocio queda para su tarea y no se afirma paridad visual.
