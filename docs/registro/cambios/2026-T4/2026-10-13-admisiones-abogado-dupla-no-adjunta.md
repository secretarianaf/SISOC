# Admisiones: el abogado de la dupla no adjunta ni elimina documentación (#2654)

En `comedores/admisiones/tecnicos/editar/<pk>`, la cuenta "Abogado Dupla"
podía adjuntar, eliminar y enviar a validar documentos como si fuera el
técnico. El rol Abogado Dupla tiene `comedores.view_comedor`,
`admisiones.view_admision` y `acompanamientos.view_informacionrelevante`, y los
templates habilitaban esos controles a cualquiera con alguno de esos permisos.

Comportamiento esperado: el abogado solo acepta o rectifica los documentos que
el técnico deja en "A Validar Abogado".

Cambios:

- `AdmisionService.es_abogado_dupla_sin_rol_tecnico(user)`: abogado de dupla
  sin rol ni grupo técnico. Los superusuarios tienen todos los roles y no
  quedan alcanzados; un usuario con ambos roles conserva los permisos de técnico.
- `subir_archivo_admision`, `crear_documento_personalizado` y
  `eliminar_archivo_admision` responden 403 para ese usuario.
- Filtro `puede_gestionar_documentacion_admision` (`admisiones_tags`): mismo
  criterio que antes usaban los templates, excluyendo al abogado. Reemplaza la
  condición repetida en `includes/documento_row.html` (Adjuntar, Eliminar y
  selector "Documento adjunto / A Validar Abogado") y en la fila de
  "Documentación adicional" de `admisiones_tecnicos_form.html`. El abogado ve
  el estado como badge.

Sin cambios: el selector Aceptado/Rectificar del abogado y el endpoint
`actualizar_estado_archivo`.

Tests: `src/backends/sisoc_core/tests/test_admisiones_abogado_dupla_documentacion.py`.
