# 2026-11-16 - Alcance por programa de comedores por usuario

## Estado
- implementada en la rama `feat/alcance-programa-comedores` (pendiente de PR)

## Contexto
- Hay dos programas de negocio sobre `comedores.Programas`: **PNUD** (Abordaje
  comunitario, Línea Secos y Línea Tradicional) y **Alimentar comunidad**.
- Hace falta que un usuario pueda quedar acotado a uno de los dos, como eje
  independiente del territorio y de los equipos técnicos.
- Relevamientos, primer seguimiento, seguimiento PNUD, actas y adjuntos no
  tienen programa propio: cuelgan del comedor. Los formularios que se ofrecen
  dependen del programa del comedor, así que filtrar comedores alcanza.

## Decisión
- Modelo `comedores.AlcanceProgramaComedor` (`profile`, `programa` con valores
  `pnud` / `alimentar_comunidad`, único por par). Se guarda el grupo de negocio
  y no ids de `Programas`, así una línea PNUD nueva queda incluida sin tocar
  datos. Vive en Comedores porque el kernel no conoce ese dominio.
- Sin filas, o con las dos, el usuario no tiene restricción (como hasta hoy): no
  hay data migration y nadie pierde acceso al desplegar.
- Con un grupo tildado solo ve comedores de ese programa. Los comedores sin
  programa o de otro programa los ven solo los usuarios sin restricción.
- Solo el superusuario saltea el filtro. `auth.role_coordinador_general` sigue
  teniendo alcance global de rol/territorio pero **sí** queda filtrado por
  programa.
- En la API territorial el filtro de programa también acota los comedores
  asignados desde SISOC.
- Helper único: `comedores/services/alcance_programa.py`
  (`programas_visibles`, `apply_programa_scope`). Traduce grupos a ids por nombre
  normalizado con los helpers de `comedores/utils.py` y cachea el resultado en la
  instancia del usuario (una consulta por request).
- Configuración: card «Programas de comedores» en el formulario de usuario
  (alta y edición), con el mismo criterio de edición que el alcance territorial.

## Dónde se aplica (AND con el alcance existente)
- `ComedorService` (`get_filtered_comedores`, `get_scoped_comedor_queryset`,
  `get_scoped_comedor_or_404`, detalle): lo heredan listado, exportación, nómina,
  PWA, etc.
- Acompañamientos (`obtener_comedores_acompanamiento`) y destinatarios de
  comunicados (vía `comedores.api.acotar_ids_comedores_por_programa`).
- Vistas web de relevamientos, seguimientos, seguimiento PNUD, actas y descarga
  de adjuntos: validan el comedor con `ComedorAlcanceMixin` (404 fuera de
  alcance). Antes no validaban alcance; además el detalle de relevamiento ahora
  exige que el relevamiento sea del comedor de la URL.
- API `/api/territorial/` (listado, detalle, comedores-zona, comedor de la zona
  para altas/adjuntos/PNUD/actas) y `_scope_relevamientos_for_authenticated_user`.

## Fuera de alcance / riesgos
- El alta de comedor por la app territorial crea el comedor sin programa:
  para un usuario restringido ese comedor queda fuera de su vista.
  `_replay_is_authorized` no se filtra por programa por ese motivo.
- Los alcances de organizaciones para destinatarios de comunicados no se
  acotan por programa.
