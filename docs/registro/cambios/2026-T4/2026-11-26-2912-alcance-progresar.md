# Cambio: alcance explícito en Progresar Curso (#2912)

## Alcance

Se agrega una configuración única que vincula el tablero de Progresar Curso con una entrada de catálogo. La política explícita está desactivada por defecto; sin activación deliberada se conserva la política anterior. No se crean ni migran concesiones reales.

## Comportamiento

Con la política activa, el acceso por URL directa, por la vista genérica, por la API web y desde el menú utiliza la concesión del tablero vinculado. La respuesta BI filtra las filas y la fecha de carga por provincias autorizadas o permite el total nacional solo cuando hay concesión nacional. Un CDI no autoriza datos provinciales agregados. Las rutas alias se normalizan antes de decidir su visibilidad. La configuración activa no puede eliminarse mediante los métodos ordinarios del modelo o queryset; una vinculación con ruta incorrecta deniega acceso.

Las solicitudes HEAD de las rutas `/dashboard/<slug>/` llegan a sus guards, en lugar de ser interceptadas por XViewMiddleware antes de la autorización. La respuesta de Progresar se sirve sin caché compartida.

## Verificación

Pruebas con datos sintéticos cubren políticas antigua y nueva, ruta directa, menú, API web, alias, unión y revocación, fecha de carga y HEAD. La revisión independiente identificó bypasses en borrado, alias y HEAD; se añadieron pruebas de regresión y correcciones. Las pruebas SQLite y una selección en MySQL 8 sintético pasaron, al igual que pylint. La demo sintética se comprobó por HTTP con un usuario autorizado y otro sin concesión. El navegador automático no estuvo disponible; el usuario confirmó visualmente los casos permitido y denegado en la demo sintética.

## Limitaciones

La configuración no se activa automáticamente ni existe aún una interfaz para gestionarla. Desactivarla deliberadamente vuelve a la política heredada y puede ampliar accesos: antes de hacerlo debe compararse el acceso efectivo y acordarse una reversión. Los embebidos externos, CDI real, otros tableros, permisos de administración y transición integral requieren trabajo adicional y coordinación con Datos. No se consultaron datos reales ni se publicó o desplegó el cambio.
