# Cambio: la nómina CDI corta el día que el niño cumple 4 años

Issue #2925 ("Evolutivos en descargas de Datos CDI"), rama `evolutivoCDI`.

## Alcance

El issue pide dos cosas:

1. **Nómina de menores de 4 años.** La descarga "Descargar nómina de niños"
   incluía a quien cumplía 4 años ese mismo día. Además, al cumplir 4 años la
   ficha tiene que pasar sola de Activo a Pendiente.

   Definición posterior de Producto (CDI): con 4 años o más el estado es
   automático y ningún perfil puede cambiarlo a mano. La fecha de nacimiento
   cargada a mano sí se puede corregir y el estado se recalcula con la fecha
   corregida.
2. **Reportes según rol.** `SIMEPI - Auditoría` solo debe ver el Reporte
   Reducido. Ya estaba resuelto en `development`
   (`GRUPOS_REPORTE_COMPLETO` en
   `src/backends/cdi/centrodeinfancia/services_reportes.py`, con tests en
   `src/backends/cdi/centrodeinfancia/tests/test_reportes.py`). No se cambia.

## Implementado

- `fecha_nacimiento_limite_nomina` y `pasar_nomina_a_pendiente_por_edad` en
  `src/backends/cdi/centrodeinfancia/services.py`: un único corte de 48 meses
  (nacidos en esa fecha o antes ya cumplieron 4 años) y el pase en bloque de
  Activo a Pendiente.
- Nuevo campo `NominaCentroInfancia.pendiente_por_edad_desde` (migración
  `0055_nomina_pendiente_por_edad_desde`): día en que el sistema pasó la ficha
  a Pendiente por edad. Distingue ese Pendiente del que tiene otro motivo.
- El PDF provincial (`services_nomina_ninos_pdf.py`) usa ese corte con `<=`:
  el día del cumpleaños el niño ya no figura.
- El formulario de la ficha (`forms.py`) aplica el mismo corte para todos los
  perfiles, incluidos `SIMEPI - Administrador` y superusuario, y también la
  edición rápida y el admin de Django:
  - con 4 años o más, el campo Estado de una ficha existente queda bloqueado;
  - en un alta, o si se cambia la fecha a una de 4 años o más, guardar en
    Activo da error;
  - si se corrige la fecha y deja de tener 4 años, la ficha que el sistema
    había pasado a Pendiente por edad vuelve a Activo.
- El pase se ejecuta al abrir el detalle del CDI, la nómina, la asistencia,
  la pantalla y la descarga de reportes y el PDF provincial.
- Comando `pasar_nomina_cdi_a_pendiente_por_edad [--fecha AAAA-MM-DD]` para
  correrlo una vez por día por cron.

## Comportamiento

- Nacido el 16/11/2022: el 15/11/2026 figura en la nómina y sigue Activo; el
  16/11/2026 ya no figura y su ficha pasa a Pendiente.
- Las fichas en Baja o Pendiente no cambian.
- Si la ficha no tiene fecha de nacimiento, se usa la del ciudadano, como en
  el PDF.
- La fecha de nacimiento verificada por RENAPER sigue bloqueada; la cargada a
  mano se puede corregir. Si con la fecha corregida sigue teniendo 4 años o
  más, queda en Pendiente.
- Una ficha que estaba en Pendiente por otro motivo no pasa a Activo al
  corregir la fecha: solo vuelve la que pasó el sistema por edad.
- El PDF excluye siempre a quien tiene 4 años o más, aunque la ficha haya
  quedado Activa por fuera de los formularios.
- El pase en bloque no pasa por `save()`: no dispara señales. El estado de la
  ficha no está en el registro de auditoría (`audittrail` solo registra
  teléfonos), así que no se pierde historial.

## Corrección incluida

La pantalla de nómina de un CDI daba error 500 cuando ni la ficha ni el
ciudadano tenían sexo cargado. `nomina_detail.html` ahora usa `{% firstof %}`
y muestra "-".

## Riesgos y operación

- Migración aditiva (columna nula); no cambia datos existentes al migrar. El
  primer acceso a una pantalla de CDI pasa a Pendiente a todas las fichas
  activas que ya tienen 4 años o más.
- Las pantallas de consulta escriben en la base (un `UPDATE` acotado y sin
  efecto cuando no hay fichas para pasar). Se eligió así para no depender de
  infraestructura nueva: CDI no tiene worker de Celery.
- Cron recomendado (opcional, lo agrega infraestructura): una vez por día
  `python manage.py pasar_nomina_cdi_a_pendiente_por_edad` en el servicio del
  backend CDI.
