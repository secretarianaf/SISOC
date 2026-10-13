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
- `cdi/centrodeinfancia/access.py`: `aplicar_scope_usuarios_cdi` excluye usuarios sin grupos para
  los roles SIMEPI nacionales.
- Tests: `cdi/tests/test_usuarios_simepi_admin.py` (nuevo) y ajuste en
  `kernel/tests/test_users_regressions.py`.

## Riesgos y rollback
- Sin migraciones. La delegación ampliada también habilita a SIMEPI Administrador a asignar esos
  grupos al crear o editar usuarios.
- Rollback: revertir el commit.
