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
- Alta/edición de comedor por la app territorial (hoy la app no tiene pantalla
  de alta: es una defensa en el servidor). `POST` y `PATCH` de
  `/api/territorial/comedores/` aplican el alcance por programa: un usuario
  restringido que manda un programa fuera de su alcance recibe 400 en
  `programa` («El programa no está dentro de su alcance.»); si no manda
  programa y sus programas visibles son una sola fila se asigna esa, y si son
  varias (PNUD = dos líneas) recibe 400 («Seleccione el programa del
  comedor.»). Sin restricción, igual que antes (programa opcional). El replay
  idempotente por `client_uuid` responde antes de validar, sin cambios; no
  se filtra por programa en `_replay_is_authorized`.
- Organizaciones de comunicados: con restricción de programa quedan solo las que
  tienen al menos un comedor visible (fachada
  `comedores.api.acotar_ids_organizaciones_por_programa`); las sin comedor
  quedan fuera para el usuario restringido.
- `acotar_ids_comedores_por_programa` sigue materializando ids cuando hay
  restricción (contrato de tupla de ids de la fachada); cambiarlo a subquery
  es invasivo y queda para otro PR.

## Quién puede editar el alcance (formulario de usuario)
- Superusuario: sin límites.
- Un actor no superusuario no puede cambiar su propio alcance (campo
  deshabilitado, no se guarda).
- Actor sin restricción: asigna cualquier combinación.
- Actor restringido: solo ofrece sus grupos, la selección es obligatoria y se
  valida en `clean()` que sea subconjunto de los suyos.
- Admisiones (listado técnico, detalle, edición y chequeos de dupla) y
  comunicados (campo de comedores, «para todos», listado de gestión) aplican el
  mismo filtro. Los ids de `Programas` por grupo se cachean a nivel de módulo
  y se invalidan por `post_save`/`post_delete` de `Programas`.
