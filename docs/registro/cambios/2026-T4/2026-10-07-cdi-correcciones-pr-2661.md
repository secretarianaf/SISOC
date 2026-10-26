# CDI: correcciones de identidad RENAPER y responsable del centro

Correcciones de revisión del PR #2661, sobre la rama `Renaper_CDI`.

## Identidad del niño/a en el alta

El botón por bloque envía `renaper_token_nino`; el alta antes solo leía el
token de la búsqueda inicial (`renaper_prefill_token`). La tarjeta podía
mostrar una identidad verificada que luego se guardaba sin bloqueo.

El alta ahora consume también el token del botón, usando la validación de
firma, usuario, bloque y vencimiento existente. Conserva el token y los campos
bloqueados si el formulario tiene errores. La reconsulta que determina la
validación del ciudadano toma esa misma identidad. Un token para otro DNI no
sustituye al ciudadano local seleccionado. El token anterior sigue soportado.

No cambia la política existente ante un token inválido o una reconsulta fallida:
la ficha puede guardarse como manual. Tampoco se actualiza un ciudadano local
ya existente al crear su ficha de nómina.

## Responsable inicial y recuperación

Generar el primer usuario desde la pantalla manual ahora lo asigna como
responsable si el CDI no tiene uno activo. La decisión se toma bajo el bloqueo
del centro para serializar las altas simultáneas.

Guardar una ficha con accesos históricos pero sin responsable activo recupera
el referente. Para la misma persona se busca primero su cuenta por el email
anterior; cambiar solo el email no debe crear otra cuenta. Se conserva la regla
de sincronizar el email únicamente si la cuenta todavía debe cambiar su
contraseña. Los usuarios siguientes no desplazan al responsable vigente.

## Asignaciones concurrentes

`asignar_responsable()` bloquea la fila del CDI antes de leer y desmarcar los
responsables anteriores. El bloqueo sobre el centro también protege el caso
en que no existe ningún responsable. Todos los callers de la asignación usan
la misma exclusión. Se conserva la auditoría individual de cada acceso y el
acceso activo del responsable anterior.

El provisionamiento automático y el alta manual toman el bloqueo del CDI antes
de insertar el acceso, para evitar promover simultáneamente los bloqueos
compartidos de la FK durante la asignación.

La regresión con transacciones concurrentes sobre MySQL reprodujo dos
responsables antes del cambio. Tras el fix queda uno solo, tanto con
responsable previo como sin él. El test usa eventos para coordinar las
transacciones; no depende de sleeps y se omite en SQLite.

## Validación y operación

- Regresiones de endpoint y formulario en `test_nomina_renaper_validacion.py`:
  POST alterado, token inválido/ajeno/vencido, errores del formulario y
  ciudadano seleccionado con un DNI diferente.
- Regresiones de gestión en `test_gestion_usuarios_cdi.py`: primer usuario,
  recuperación desde activo/baja y conservación de cuentas temporales y
  cuentas ya modificadas al cambiar el email.
- Regresión `mysql_compat` en `test_accesos_cdi_concurrencia.py`, con
  transacciones y conexiones independientes sobre MySQL real.
- Validación focalizada en imágenes Docker existentes, SQLite de prueba y
  MySQL desechable sin puertos publicados ni volúmenes con datos reales.
- Resultado local final: 108 tests focalizados pasan en SQLite y 2 regresiones
  concurrentes pasan en MySQL. Black de los siete archivos modificados y el
  check de rutas documentadas pasan; pylint de los archivos de código alcanza
  10/10.
- Se mantienen pendientes la validación de RENAPER real en homologación y
  los checks requeridos de CI sobre el HEAD final.

No hay nuevas dependencias, modelos ni migraciones. El rollback de estas
correcciones consiste en revertir sus commits de código; no exige revertir
las migraciones 0050/0051 del PR original. Un rollback reintroduce los tres
errores corregidos y no deshace las asignaciones ya guardadas.
