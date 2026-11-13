# Cambio: el legajo de organización completo en React (#2785, O05.01)

## Alcance

El legajo deja de montar un fragmento HTML nativo: todo el contenido es React, con
el mismo marcado, clases, textos y orden que la plantilla. Entregas:

| Entrega | Parcial | Sección |
|---|---|---|
| O2-U2 | `legajo/region.html` | `region` |
| O2-U3 | `legajo/proyectos.html` | `proyectos` |
| O2-U4 | `legajo/comedores.html` | `comedores` |
| O2-U5 | `organizacion_detail.html` | encabezado, selector de programa, «Datos de la Organización», avisos, franja, pestañas y orden de los bloques |

No cambia vistas, formularios, plantillas, servicios, modelos ni URLs nativas, y no
activa React en producción. El acceso sigue siendo el de hoy (ver
[brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)).
Son bloques de solo lectura: cualquier edición sigue yendo a
`/organizaciones/editar/<id>#abordaje-card`, ya en React.

## Cómo funciona

`web_api_legajo.py` registra un constructor por parcial con `seccion(...)`
(`web_api_secciones.py`). Recibe el contexto del parcial (variables de `with`
incluidas) y devuelve JSON; React lo monta en el marcador
`data-legajo-seccion` con `organizacionLegajoDatos.tsx`. Los textos por defecto
(`-`, vacíos), el permiso de edición (`puede_gestionar_organizaciones`) y la
etiqueta del territorial (`etiqueta_territorial`) salen de la misma lógica nativa.

- **Región** (`region`): región y subzona (o «Faltan Región y Subzona.» con el
  enlace «+ Completar región» solo para quien gestiona) y los territoriales
  anteriores sin proyecto.
- **Proyectos** (`proyectos`): título (con el programa), total de proyectos
  activos, código, territoriales (o «Sin territorial») y estado «Activo»; el
  enlace «Editar proyectos» solo para quien gestiona. Los proyectos dados de baja
  no llegan, como en el parcial.
- **Comedores** (`comedores`): nombre con enlace al comedor y la insignia
  CARITAS, tipo, código de proyecto y programa (según el bloque), ubicación,
  dirección (`-` y `S/N` por defecto), referente y estado de validación
  (Validado, No Validado o Pendiente). Los valores por defecto se calculan en la
  API con la misma regla que el filtro `default` de la plantilla.

### O2-U5: marco del legajo

- `web_api_legajo_pagina.py` sigue el flujo de `organizacion_detail.html` sobre el
  contexto de `OrganizacionDetailView` (más `ver_historial`) y devuelve
  `{header, selector, datos, blocks, css}`. Cada bloque que es una sección lleva el
  JSON de su constructor (`web_api_secciones.construir`), llamado con el contexto y
  los argumentos `with` de la plantilla; los demás son datos de aviso, franja,
  pestañas y tarjetas de rendiciones.
- Los textos y valores por defecto (`Sin información`, `-`), la localización de fechas
  (`d/m/Y`, `d/m/Y H:i` en hora local) y el estado Vigente/Vencido (comparación con
  la fecha de hoy) se calculan con los mismos filtros de Django; los plurales con
  `pluralize`.
- El `<style>` de la plantilla se lee de su fuente y viaja como `css` (la plantilla
  no tiene etiquetas de plantilla dentro del estilo), así que el CSS conserva un único
  dueño mientras exista la página nativa.
- `organizacionLegajoPagina.tsx` dibuja la página; `organizacionesLegajo.tsx` solo la
  carga. Desaparecen `html`, `sections`, `scripts`, los marcadores y el mecanismo de
  envoltura de bloques en línea. El modal nativo de rectificación ya no se envía: la
  sección de documentos tiene el suyo.
- Orden de bloques: avales, «Sin programas asignados», aviso y región/proyectos de
  Abordaje sin línea, rendiciones generales, franja y pestañas del programa, información
  o rendiciones del programa, documentación y el bloque «Sin programa asignado».

## Verificación

Pruebas nuevas de backend (`test_web_organizaciones_legajo_datos_api.py`) y de
frontend (`organizacionLegajoDatos.test.tsx`, `organizacionesLegajo.test.tsx`).
El detalle de las corridas está en el informe de entrega de la ola.

## Limitaciones

- El CSS del legajo sigue en la plantilla nativa (se lee de ella); al retirar la
  página nativa debe pasar a la aplicación.
- Una referente sin nombre se muestra como en la plantilla (`None`), por paridad.
