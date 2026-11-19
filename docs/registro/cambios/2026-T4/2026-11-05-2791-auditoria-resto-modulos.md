# Cambio: el resto de los módulos con datos de gestión entran al log de auditoría

## Alcance

Issue #2791, última parte (antes: VAT, Celiaquía, PAS, VPSL y fondos de
comedores, en `docs/registro/cambios/2026-T4/`). Se suman 30 modelos a la
lista única de `src/backends/kernel/audittrail/constants.py`. Con esto la
lista queda en 73 modelos. No hay modelos, migraciones ni permisos nuevos.

| Módulo | Modelos | Qué no se registra |
|---|---|---|
| Admisiones | `Admision`, `ArchivoAdmision`, `InformeTecnico`, `InformeComplementario` | fechas automáticas; el snapshot JSON de la organización; del informe técnico solo se registran `estado`, `estado_formulario`, `tipo`, `monto_total_conveniado`, `total_acreditaciones` y `plazo_ejecucion` |
| Acompañamientos | `Acompanamiento`, `InformacionRelevante`, `Prestacion`, `Hitos` | fechas de alta |
| Duplas | `Dupla` | fecha de alta |
| Comedores | `ComedorDatosConvenioPnud`, `CapacitacionComedorCertificado`, `PrestacionAlimentariaConformidad`, `ValorComida` | fechas automáticas y el DNI de quien certifica la conformidad |
| Relevamientos | `PrimerSeguimiento`, `SeguimientoPnud`, `ActaComplementaria` | fechas automáticas y el JSON del formulario PNUD |
| Comunicados | `Comunicado` | fechas automáticas y último usuario que modificó |
| Organizaciones | `ProyectoOrganizacion`, `ArchivoOrganizacion` | fechas automáticas y último usuario que modificó |
| Centros de Familia | `Centro`, `ActividadCentro`, `ParticipanteActividad` | fechas automáticas |
| Dispositivos | `Dispositivo` | fechas automáticas |
| Configuración | `Programa`, `MontoPrestacionPrograma`, `TipoIntervencion`, `SubIntervencion`, `InsumoCategoria`, `Insumo`, `Tablero` | fechas automáticas y último usuario que modificó |

## Criterio

- Se registra lo que es decisión de gestión o dinero: estado de admisiones y
  sus documentos, convenios, montos por prestación, validación de
  seguimientos por coordinación, hitos de acompañamiento, publicación de
  comunicados y configuración que cambia el comportamiento (programas,
  montos, catálogos de intervenciones, tableros con sus permisos).
- El informe técnico copia DNI y datos del representante y del responsable
  de la tarjeta: usa lista de campos permitidos, como en Celiaquía y VPSL.
- Quedan afuera a propósito, con su motivo:
  - historiales y logs propios (`AdmisionHistorial`,
    `HistorialEstadosAdmision`, `EstadoHistorial`, `AuditComedorPrograma`,
    `AuditColaboradorEspacio`, `HistorialValidacion`,
    `ParticipanteActividadHistorial`, `NominaDerivacion`, `TerritorialSyncLog`,
    la app `historial`);
  - registros de procesos (`importarexpediente`, `ocr`, `MailingJob*`,
    `CabalArchivo`, `InformeCabalRegistro`);
  - padrones con datos personales de beneficiarios y responsables de Centros
    de Familia (`Beneficiario`, `Responsable`, `PadronBeneficiarios`,
    `BeneficiariosResponsablesRenaper`): si se quieren auditar, conviene
    decidir antes qué campos;
  - las secciones del formulario de relevamiento y de seguimiento (decenas de
    tablas que se guardan junto con su cabecera, que sí se audita);
  - catálogos geográficos y de referencia de `core` y `organizaciones`,
    preferencias de usuario (`FiltroFavorito`, `PreferenciaColumnas`) y
    contadores (`dashboard.Dashboard`).

## Ajustes de la lista

- La definición de `Comedor` excluía `fecha_actualizacion`, un campo que ya
  no existe. auditlog lo ignoraba en silencio; se quita.
- Se agrega un test que recorre las 73 definiciones y falla si un modelo no
  se puede importar, si su clave no coincide con el modelo real o si un campo
  excluido o permitido no existe. Así un error de tipeo no deja un modelo sin
  auditar sin que nadie se entere.

## Pendiente, fuera de este cambio

- **Papelera:** el borrado lógico y la restauración no dejan evento en el
  visor para ningún modelo auditado (se hacen con `.update()`).
- **Relaciones M2M:** técnicos de una dupla, avisos PAS, referentes de un
  centro VAT, vehículos VPSL. auditlog 3.2.1 las soporta (`m2m_fields`), pero
  el visor (`src/backends/kernel/audittrail/views.py`) hoy mostraría esos
  cambios como "No cargado": hay que adaptarlo primero.
- **Actualizaciones en lote:** importaciones, cruce SINTYS, subsanación
  masiva y similares necesitan un evento resumen con `registrar_evento`.

## Verificación

- `pytest src/backends/kernel/tests/test_audittrail_registry_unit.py`: las 73
  definiciones apuntan a modelos y campos reales, y las etiquetas del visor no
  se repiten.
- `pytest src/backends/comedores/tests/test_auditoria_circuito_comedores.py`:
  el cambio de una admisión queda sin el snapshot; el informe técnico registra
  su cambio de estado y nunca un DNI; los cambios de dupla y comunicado
  quedan con `[viejo, nuevo]`.
- Suites de CDF, dispositivos, `sisoc_core` y CDI: fallan solo tests que
  fallan igual sin este cambio (`*_sin_n_mas_1` y dos contratos HTTP de
  `test_issue_2641_http_contracts.py`).
