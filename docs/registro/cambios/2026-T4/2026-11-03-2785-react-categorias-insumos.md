# Cambio: API de categorías de insumos (#2785)

## Unidad backend separada (2026-11-05)

Esta unidad incorpora solamente la API de categorías, sus pruebas y los hunks
del router y registro de URLs. Incluye listado GET/HEAD y metadatos/POST para
crear, editar y eliminar bajo `/api/web/insumos/categorias/`. Reutiliza
`InsumoCategoriaForm`, servicios, permisos por acción, sesión y CSRF existentes.
No cambia modelos, dependencias, rutas HTML ni componentes React. El adaptador
propio de admindocs conserva HEAD para estas rutas dentro de la API; no modifica
el middleware upstream ni el administrador/Unfold.
La eliminación conserva archivos y aplica la regla SET_NULL existente.

La prueba visual y la aceptación de interfaz siguen pendientes; esta unidad
no las sustituye ni autoriza publicación. Las pruebas del árbol mínimo de esta
separación se registran por separado; los resultados que siguen pertenecen al
checkpoint completo histórico y no se afirman como una nueva ejecución.

## Verificación de esta unidad backend

En el árbol mínimo aislado se aprobaron 162 pruebas de categorías, lectura y
mutaciones INS-A, sesión, requisitos y navegación. Black, Pylint y referencias
documentales pasaron. Se usó la imagen local fijada, sin red, con fuente de
solo lectura y SQLite/media temporales sintéticos; no se repitió el frontend
ni el helper visual pendiente. Persisten siete advertencias previas.
El estado lógico del índice y los archivos vivos se conservaron; su hash físico
cambió durante la verificación, sin causa establecida ni cambios de blobs/modos.
Esta evidencia no constituye verificación visual, aceptación humana, CI ni deploy.

## Regresión HEAD con IP interna

La comprobación independiente reprodujo que admindocs interceptaba HEAD desde
una IP interna antes de los controles de sesión y permiso: devolvía 200 con
metadatos diagnósticos, sin datos de negocio ni mutaciones, en vez de 401/403.
La prueba nueva observó ocho fallos internos y ocho casos externos correctos
antes del ajuste. Tras añadir únicamente las cuatro rutas de categorías a la
excepción del adaptador existente, los dieciséis casos pasan y conservan cuerpo
vacío, cabeceras privadas y datos sin modificar. La suite focalizada completa
pasa con 162 pruebas; Black y Pylint incluyen el adaptador. Las rutas ajenas
siguen delegando en admindocs. Requiere revisión técnica por afectar guardas.

La comprobación independiente limitada confirmó las 32 peticiones GET/HEAD de
la matriz de acceso y 64 comparaciones directas del middleware contra el
baseline. Esas comparaciones no son una suite HTTP adicional: comprueban que
admindocs fuera del alcance y las excepciones sesión/INS-A conservan su salida.
No se repitió la suite completa ni se retomó el trabajo visual. Los dos blobs
corregidos coinciden con GREEN; otros cuatro Python son equivalentes tras
normalizar CRLF/LF, no idénticos byte a byte. La ejecución independiente usó
el archivo Git sin modificarlo. Runner finalizado sin OOM, datos preservados.

## Unidad React separada (2026-11-06)

Esta unidad agrega solamente la interfaz React de categorías sobre la API ya
incorporada. No modifica backend, rutas públicas, dependencias ni estilos.

- `App.tsx` reconoce `/v2/sisoc/insumos/categorias/`, `crear`, `<id>/editar` y
  `<id>/eliminar` sin cambiar sus slashes. Los títulos del documento coinciden
  con las plantillas originales. Guardar, eliminar y cancelar vuelven a
  `/v2/sisoc/insumos/categorias/`, equivalente local de `/insumos/categorias/`,
  con el aviso Toastr existente.
- `InsumosCategoriasList.tsx` y `InsumosCategoriaForm.tsx` reutilizan los
  helpers de `webAccess.ts`, `InsumosAccessError` y la paginación existente,
  extraída sin cambios a `insumosPagination.ts`. Los POST son URL-encoded y solo
  se acepta la confirmación con retorno fijo `/insumos/categorias/`. Un
  resultado incierto deshabilita el formulario y no se reintenta.
- El listado y los formularios vuelven a consultar la API en cada montaje. No
  hay caché persistente: tras la regla SET_NULL, INS-A obtiene opciones y datos
  actuales al volver a abrirse.
- Se conserva el alias exacto `/v2/sisoc/insumos` del marco INS-A y su prueba
  de regresión.

### Verificación de esta unidad React

Sobre HEAD más esta unidad, en una copia aislada: las pruebas nuevas de rutas,
títulos, retorno con aviso y cancelación fallaron antes de implementar (seis
casos de `App.test.tsx` y dos archivos de componentes sin módulo). Después
pasan las 86 pruebas frontend, TypeScript, ESLint y el build de Vite; el CSS
generado es idéntico al de INS-A.

La comparación visual usó el runtime sintético local, solo GET, con dos cargas
nuevas por lado, en 1440x900 y 390x844: listado (perfil de gestión y perfil
limitado), alta, edición y confirmación de eliminación, además del listado y el
alias de INS-A. En móvil, alta, edición, eliminación e INS-A son idénticas en
píxeles. Las diferencias restantes se clasificaron así:

- Flecha del sidebar en escritorio (76-80 píxeles): desaparece al cancelar las
  animaciones en ambos lados; es el mismo estado de render ya clasificado para
  INS-A, no geometría. Con animaciones canceladas, el alta de escritorio queda
  idéntica.
- Cifra del texto «Se encontraron N resultados» en el listado (56 píxeles):
  mismos caracteres y desplazamiento máximo de 0,015625 CSSpx, menor a un píxel
  y aprobado por la regla S2 existente.
- Menú móvil fuera de pantalla: «Comunicados» queda 45 px más abajo porque
  React mantiene abierto el submenú Insumos. No es visible y queda cubierto por
  la exclusión explícita del menú móvil.

No se usaron máscaras ni se ampliaron tolerancias. El dominio sintético quedó
sin cambios, sin errores de página, solicitudes bloqueadas ni POST. El recorrido
con mutación real y aviso no se ejecutó en el navegador; lo cubren las pruebas
de componentes y de aplicación. Esto no constituye aceptación humana, revisión
nativa, CI ni despliegue. Riesgo técnico: contratos compartidos del marco
(`App.tsx`), respuestas asíncronas y permisos por operación.

## Antecedente: circuito completo histórico

El contenido siguiente documenta la implementación local anterior, incluidos
frontend y tooling que NO forman parte de esta unidad backend.

### Alcance

Continuación local INS-B del contrato M2 aprobado. Implementa listado, alta,
edición y confirmación de eliminación mediante componentes React, sin
activar React en las rutas públicas originales. El seguimiento y las pruebas
de ese checkpoint se conservaron en el seguimiento local de la épica.

### Comportamiento

- Las cuatro rutas locales bajo `/v2/sisoc/insumos/categorias/` mantienen los
  slashes del circuito original. Cada entrada verifica su permiso de operación;
  alta, edición y eliminación no exigen además permiso de consulta.
- Los adaptadores en
  `src/backends/sisoc_core/insumos/web_categoria_api_views.py` reutilizan
  `InsumoCategoriaForm` y los servicios existentes. No cambian modelos ni reglas
  de validación. La API usa sesión y CSRF, rechaza JSON en las mutaciones y
  conserva la precedencia de requisitos de acceso.
- El listado presenta programa, nombre, orden y estado, con veinte filas por
  página. Los botones dependen de permisos independientes. Los formularios
  conservan los errores por campo y las opciones del programa actual inactivo.
- Guardar, eliminar y cancelar vuelven al listado de categorías. La confirmación
  informa el resultado; una respuesta incierta no provoca reintentos automáticos.
  Eliminar conserva los archivos y deja los insumos asociados sin categoría;
  volver a INS-A vuelve a consultar sus datos y opciones.
- El runtime sintético materializa el rol de gestión de categorías sin permisos
  implícitos de insumos. Los escenarios operativos se preparan por separado,
  sin alterar el conjunto original de lectura.

### Verificación

Observados localmente: RED de rutas API ausentes, rechazo de JSON en eliminación,
guardas de entrada y rol sintético; sus correcciones pasan las comprobaciones
focalizadas. También pasan los componentes de formulario/listado y el recorrido
de alta con retorno y mensaje en la aplicación. TypeScript y ESLint no informan
errores en el snapshot aislado.

La verificación propia de cierre pasa: 170 tests frontend; TypeScript, ESLint y
build SISOC; 175 tests backend y seis subtests; Black en los nueve archivos Python
modificados y Pylint. Se mantienen dos advertencias previas de VPSL y siete del
runtime backend. El registro conserva todas sus entradas anteriores y resuelve
las cuatro nuevas rutas API de categorías.

La matriz visual ejecutó catorce casos en desktop y móvil, con veintiocho
combinaciones y estado sintético independiente. No se observaron fallos
funcionales, de persistencia, recursos externos inesperados ni excepciones de
página. El recorrido de teclado conserva orden y foco visible. La prueba de
integración confirma SET_NULL, archivos conservados y selectores de INS-A
poblados y actualizados, sin la categoría eliminada.

No se afirma igualdad absoluta de píxeles: cuarenta de las cincuenta y seis
capturas iniciales/finales son idénticas. La posición neutral del puntero elimina
las diferencias mayores de hover y spinner; la pintura del texto de cantidad
conserva una diferencia de 56 píxeles, con un máximo geométrico por carácter de
0,015625 CSSpx, dentro del umbral S2 existente. Permanece la diferencia histórica
del chevron del sidebar. No se utilizaron máscaras ni se ampliaron excepciones.

La verificación independiente pasa cuatro probes públicos y un diferencial
contra el snapshot inmutable de la primera ola. Nueve respuestas INS-A conservan
estado, contenido y cabeceras seleccionadas; los rechazos conservan el estado de
datos, y la eliminación conserva los archivos y actualiza las opciones. Los
dieciocho hashes del candidato permanecen estables. No se encontraron bloqueos
causados por este candidato ni se necesitó una corrección.

Estos resultados no constituyen aceptación humana, revisión nativa, CI ni
despliegue. En ese checkpoint no se realizaron commits ni publicación.
Riesgo técnico: permisos, contratos compartidos, respuestas asíncronas y
configuración de rutas.

### Referencias

- Contrato M2 de Insumos aprobado en el plan local de la épica (referencia histórica).
- [Guía Front v2](../../../implementaciones/frontend_v2.md).
