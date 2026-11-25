# CDF: circuitos React y decisión de alcance de autorización

Estado: E2, planificación. D1 elegida explícitamente por el responsable («d1»); sin implementación.
G1/P1/C2/I1/W1/M2/R1/S1/J2/L2 permanecen vigentes. Admin/Unfold #2789 excluido.

## Circuitos identificados

| Circuito propuesto | Operaciones y retorno | Dependencia y comportamiento que conservar |
|---|---|---|
| CDF-A centros | Listado/AJAX, alta, ficha, edición y baja lógica; alta/baja retornan listado, edición retorna ficha | CentroForm; permisos distintos para ficha y edición/baja; alta FARO desde query. No convertir View en permiso universal de escritura |
| CDF-B actividades | Listado, alta, edición, ficha y opciones categoría | ActividadCentroForm; alta/edición retornan centro_detail, por eso dependen de CDF-A según M2. J2/L2 no cubren todo el formulario; precio FARO conserva validación existente |
| CDF-C participantes y espera | Buscar documento, seleccionar/crear ciudadano, inscribir/espera, baja y promoción; retorno a actividad | ParticipanteActividadForm y ParticipanteService. W1 mantiene espera dentro de ficha. Promoción usa primero por fecha, no necesariamente la fila del botón. Baja también intenta promoción automática; no modificar reglas de cola |
| CDF-D asistencia | Planilla por fecha, registro y retorno con fecha | Predicado puede_tomar_asistencia_cdf y AsistenciaActividadService; no reutilizar ese predicado como autorización universal de operaciones |
| CDF-E usuarios/CABAL | Generación de usuario y procesamiento/archivos vinculados a ficha | Contratos sensibles todavía requieren profundización; no declararlos preparados ni incluir credenciales/datos reales en fixtures |

Particiones propuestas, no tickets listos ni APIs creadas. Campos, efectos y casos
visuales deben completarse antes de declarar cada circuito preparado.

## Evidencia y límite de la conclusión

En fuente local, contrastada por exploración con snapshot
`59a8f797688c9e762d5a4e9eaa187698ffade8aa` para URLs, actividades,
participantes, asistencia, Forms y servicio de participantes:

- `src/backends/cdf/centrodefamilia/urls.py:116–184`: actividades y participantes
  usan decorador general `centrodefamilia.view_centro`.
- `src/backends/cdf/centrodefamilia/views/actividad.py:19–57`: listado sin filtro
  obligatorio por actor; alta obtiene centro por ID. Esas ramas no aplican el
  predicado de acceso específico al centro.
- `src/backends/cdf/centrodefamilia/views/participante.py:25–62`: creación usa
  actividad_id; la vista no contrasta su pertenencia con centro_id de la URL.
- `src/backends/cdf/centrodefamilia/views/centro.py:194–209,363–390`: ficha y
  edición/baja tienen condiciones diferentes; no uniformarlas por comodidad.
- `src/backends/cdf/centrodefamilia/services/participante/impl.py:167–207`:
  baja y promoción tienen efectos de cola que el contrato debe describir.

Es una asimetría observada estáticamente, no una explotación reproducida ni una
conclusión sobre autorización efectiva en producción. Faltan pruebas de gates,
middleware y comportamiento real. No se ejecutó ninguna operación de datos.

## Decisión resuelta: D1 elegida, D2 descartada en esta migración

| Alternativa | Alcance | Costo y riesgo residual |
|---|---|---|
| D1 — Paridad estricta de autorización | Migrar sin incorporar nuevas restricciones por centro en este trabajo; describir reglas observadas y registrar el hallazgo de seguridad por separado | Menor alcance de migración, pero puede conservar acceso transversal no deseado; no equivale a certificar que sea seguro |
| D2 — Planificar endurecimiento acotado y coordinado (recomendación del agente) | Incluir como prerrequisito de estos circuitos la definición explícita de actores/centros permitidos y validación centro↔actividad↔participante, aplicada coherentemente al backend legacy y nueva API | Amplía alcance y puede restringir accesos hoy posibles; exige una matriz por acción y aprobación de reglas antes de implementarla. No basta con ocultar botones en React |

D1 conserva las reglas actuales: no agregar restricciones por centro ni quitar
controles existentes, conceder permisos o eludir gates. El hallazgo se mantiene
separado como riesgo documentado, sin declarar mitigación ni crear otro issue.
D2 no es prerrequisito aprobado para esta migración. No inventar roles nuevos. Conservar FIFO, efectos de baja, apariencia,
retornos, W1 y L2 en ambas opciones. No cambiar permisos globales ni extender R1
INET a CDF por analogía.

## Verificación pendiente para implementación futura

- Actores propios/ajenos, rol mixto y sin permiso, además de requisitos web.
- IDs de centro/actividad/participante compatibles e incompatibles y acceso directo:
  contrastar comportamiento previo y candidato, sin imponer una nueva denegación por D1.
- Cuando la política existente deniega, misma denegación sin mutación, historial
  ni promoción secundaria. Documentar diferencias de fuente/runtime antes de decidir.
- Circuito positivo completo, efectos y mensajes; comparación visual por URL,
  estado, rol y viewport, incluyendo retornos y diferencia acotada L2.

## Verificación de esta planificación

Exploración estática y contraste puntual del padre; CodeGraph inicializado y
sincronizado en este worktree antes de búsquedas estructurales. Sin código de
aplicación modificado, tests, DB, servidor, navegador, capturas, CI o despliegue.
La elección D1 está registrada localmente; sin actualización GitHub de esta decisión.

Registro: [D1 aceptada](../../registro/decisiones/2026-10-28-2785-cdf-autorizacion-d1.md).

## Referencias

- [Orden y preparación de circuitos](2026-10-27-2785-cierre-progresivo-de-contratos.md).
- [Lectura CDF](2026-10-27-2805-contrato-lectura-cdf.md).
- [Selectores J2](2026-10-27-2787-selectores-contratos-j2.md).
