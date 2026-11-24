# 2026-11-10 - Brechas de acceso que la migración a React conserva (#2785)

## Estado

- aceptada (agente, 2026-11-10), aplicando el criterio que el responsable fijó
  para T05:

> "sobre los t05, dejalo como esta, se arreglara en otro momento, documentalo"

y su indicación de preguntar solo lo estrictamente humano. Conservar el acceso
actual no cambia quién puede hacer qué; corregirlo sí, y queda para otro
trabajo.

## Contexto

Al escribir los contratos M2 de admisiones, expedientes, relevamientos y
rendiciones se encontraron reglas de acceso más abiertas que lo esperable en
las vistas Django actuales. La migración a React necesita decidir si las APIs
web nuevas las copian o las cierran.

Brechas encontradas (detalle y fuentes en cada contrato):

- **Admisiones (AD02, AD03):** cualquier usuario autenticado puede resincronizar
  un convenio, subir archivos de catálogo a cualquier admisión, marcar un
  informe técnico como "Validado" o "A subsanar" con un POST directo (con uno de
  los tres permisos de lectura) y editar "personas conveniadas" sin verificar la
  admisión. El chequeo de expediente duplicado revela admisión, comedor y
  organización antes de verificar permisos. El editor técnico y el detalle legal
  se abren por id global y la mayoría de las acciones no revalidan rol ni estado.
- **Expedientes de pago (EX01, EX02):** cualquier usuario autenticado puede leer
  expedientes y subir, importar o borrar datos importados, sin permiso ni
  alcance por comedor.
- **Relevamientos, seguimientos y actas (R01-R03):** con `view_relevamiento` se
  abren registros de cualquier comedor por URL, sin alcance.
- **Rendición final (RF01):** Nginx sirve `/media/rendicion_cuentas_final/` a
  cualquiera con la URL; la pantalla no tiene enlace vivo (entrada de sidebar
  comentada, la ficha no la enlaza).
- **Organizaciones (O01-O05):** alta, edición y baja de organizaciones,
  firmantes, avales y convenios solo exigen `view_organizacion` y no se limitan
  a la dupla; el CSV tampoco; documentos y auditorías se abren por URL de media.

## Decisión

Las APIs web y las pantallas React de estas familias aplican las mismas reglas
de acceso que las vistas Django actuales. Los tests de las APIs fijan ese
comportamiento para que el arreglo posterior tenga que cambiarlos de forma
explícita.

Única excepción: las acciones nuevas de la API web de rendición final exigen
`view_rendicioncuentasfinal`. Hoy solo piden sesión, pero sus únicos botones
están en pantallas que ya exigen ese permiso, así que ningún usuario pierde
acceso y la API nueva no agrega una superficie más abierta. Las rutas Django no
cambian.

## Consecuencias

- Las brechas siguen abiertas y se corrigen en trabajos separados, cada uno
  cubriendo a la vez las vistas Django y la API web, para no dejar dos reglas
  distintas.
- Cerrar la exposición pública de `/media/rendicion_cuentas_final/` rompe URLs
  que usan la API de la PWA y el detalle de admisión; requiere coordinar ese
  cambio.

## Referencias

- Decisión T05: [2026-11-10-2785-t05-programas-acceso-actual.md](2026-11-10-2785-t05-programas-acceso-actual.md).
- Épica de migración a React #2785.
