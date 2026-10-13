# 2026-10-08 - Usuarios: SIMEPI Administrador gestiona solo usuarios de CDI

## Contexto
- Los usuarios con "SIMEPI - Administrador" recibían 404 al editar usuarios desde `/usuarios/`
  y no podían restablecer contraseñas.
- Causa: el listado les daba visibilidad global (todos los usuarios del sistema), pero la
  edición y la baja usan el alcance delegable, que para este rol era solo
  "SIMEPI - Equipo Nacional". Cualquier otro usuario visible daba 404.
- Producto definió que SIMEPI Administrador debe ver y editar solo a los usuarios de CDI.

## Decisiones
- SIMEPI Administrador delega (y por lo tanto ve, edita y da de baja) a: SIMEPI Equipo Nacional,
  EGP, Analista de datos, Auditoría, CDI Referente centro y CDI Trabajador. No incluye a otros
  SIMEPI Administrador.
- Se quita a SIMEPI Administrador de la visibilidad global del listado: lo que ve es lo mismo que
  puede editar.
- Un usuario es "de CDI" si todos sus grupos son de CDI/SIMEPI. Los que además tienen grupos de
  otros programas, los que no tienen grupos y los superusuarios quedan fuera.
- Los roles SIMEPI nacionales ya no alcanzan a usuarios sin grupos (antes cumplían el filtro de
  subconjunto por tener el conjunto vacío).
- SIMEPI Equipo Nacional conserva la visibilidad global del listado; no fue parte del pedido.

## Cambios aplicados
- `kernel/core/constants.py`: `GROUP_DELEGATION` de SIMEPI Administrador.
- `kernel/users/services.py`: `USUARIOS_NACIONALES_CON_VISIBILIDAD_GLOBAL` solo con Equipo
  Nacional.
- `kernel/users/services.py`: el alcance administrable excluye usuarios sin grupos para
  los roles SIMEPI nacionales, conservando la excepción del propio actor y del superusuario.
  Este límite se aplica en el core aunque el backend CDI no esté instalado; el scope de
  `cdi/centrodeinfancia/access.py` sigue siendo responsable del alcance territorial de CDI.
- Tests: `cdi/tests/test_usuarios_simepi_admin.py` (nuevo) y ajuste en
  `kernel/tests/test_users_regressions.py`.
- Regresión de servicios y vistas: `kernel/tests/test_usuarios_simepi_scope.py`, ejecutable
  con `config.settings` (core aislado) y `config.settings_all`. Cubre listado, rechazo de
  GET/POST de edición y baja de cuentas sin grupos, acceso permitido a CDI y excepciones
  de superusuario y de gestores de otros programas.

## Riesgos y rollback
- Sin migraciones. La delegación ampliada también habilita a SIMEPI Administrador a asignar esos
  grupos al crear o editar usuarios.
- Rollback: revertir el commit.

## Validación de la corrección de aislamiento (2026-10-13)
- Docker sin red, checkout montado en solo lectura y SQLite efímero: 9 tests de
  `test_usuarios_simepi_scope.py` pasaron con `--ds=config.settings`.
- Con `config.settings_all`: 77 tests pasaron entre ese archivo,
  `cdi/tests/test_usuarios_simepi_admin.py` y `kernel/tests/test_users_regressions.py`.
- Black en los tres Python afectados y pylint en los dos archivos de producción
  pasaron (pylint 10/10). No se usaron bases reales ni se validó una sesión web en QA.
