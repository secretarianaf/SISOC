# Cambio: bloques de datos del legajo de organización en React (#2785, O05.01)

## Alcance

Los bloques de datos del legajo que eran includes nativos pasan a React, uno por
entrega y con el mismo marcado, clases y textos que el parcial:

| Entrega | Parcial | Sección |
|---|---|---|
| O2-U2 | `legajo/region.html` | `region` |
| O2-U3 | `legajo/proyectos.html` | `proyectos` |
| O2-U4 | `legajo/comedores.html` | `comedores` |

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

## Verificación

Pruebas nuevas de backend (`test_web_organizaciones_legajo_datos_api.py`) y de
frontend (`organizacionLegajoDatos.test.tsx`, `organizacionesLegajo.test.tsx`).
El detalle de las corridas está en el informe de entrega de la ola.

## Limitaciones

- Cabecera, selector de programa, datos de la organización, pestañas y avisos del
  legajo siguen como HTML nativo.
- Una referente sin nombre se muestra como en la plantilla (`None`), por paridad.
