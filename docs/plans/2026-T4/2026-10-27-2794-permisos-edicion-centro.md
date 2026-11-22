# INET: decisión sobre edición de centros durante migración

Estado **E2, R1 elegida explícitamente por el responsable («r1»)**. No cambiar
ahora permisos, grupos, predicados, endpoints ni pantallas. I1 fijó referencia
visual Django; R1 resuelve separadamente la autorización futura de edición.
Ver [decisión registrada](../../registro/decisiones/2026-10-27-2794-edicion-centros-r1.md).

## Diferencia confirmada en fuente

Fuente congelada `59a8f797688c9e762d5a4e9eaa187698ffade8aa`, leída con git show:

| Camino | Controles encontrados |
|---|---|
| Django `/vat/centros/<pk>/editar/` | `VAT/urls.py` exige `VAT.view_centro`; `CentroUpdateView.dispatch` en `VAT/views/centro.py` exige `can_user_edit_centro(user, centro)` |
| Regla de dueño de centro | `VAT/services/access_scope.py`: SSE puede editar; provincial necesita scope y change_centro; referente asociado a ese centro puede editar por asociación/rol. No basta View para cualquier centro |
| API React, PUT de recurso centros | `InetDetailView.put` llama get_item (check_read y queryset), luego check_write → `inet_queries.can_mutate`: exige `VAT.change_centro` además de can_user_edit_centro |
| Seed de grupo CFP | `src/backends/kernel/users/bootstrap/groups_seed.py`: role_referentecentrovat y view_centro; no change_centro en ese grupo. Otros grupos administrativos sí lo incluyen |
| Evaluación IAM | `src/backends/kernel/iam/services.py`: user_has_permission_code normaliza y consulta has_perm; no convierte por sí solo rol referente en Change |

Caso de contrato: usuario activo referente del propio centro, View efectivo,
sin Change efectivo ni otro grupo que lo conceda. La vista Django no añade ese
Change para su rama referente; API INET sí. Son condiciones distintas demostradas
por código. No se consultó DB ni se reprodujo HTTP: no se afirma cuántos usuarios
reales están afectados ni que el seed describa todos sus permisos efectivos.

Fuente API: `src/backends/vat/VAT/api_inet_views.py` y
`src/backends/vat/VAT/services/inet_queries.py` en ese SHA. Revisar también menú,
schema de formulario y submit: ocultar un botón no resuelve el contrato backend.

## Alternativas evaluadas: R1 elegida, R2 descartada

| Opción | Regla de edición de centros React | Ganancia | Consecuencia aceptada |
|---|---|---|---|
| R1. Preservar regla de negocio Django | Reutilizar predicado del dueño para editar centro, conservando View y alcance real, sin exigir un Change adicional a la rama referente que hoy no lo exige | Mantiene capacidad del referente de su centro y la migración conserva el comportamiento origen | Adaptación acotada de autorización INET ya integrada; revisar fuente/receptor/UI y demostrar que nadie edita otro centro. No quitar Change global de otros recursos ni dar permisos masivos al grupo CFP |
| R2. Conservar regla más restrictiva de INET | Mantener View + Change + predicado de centro como requisito de edición | Conserva contrato del endpoint integrado y permiso de acción explícito | El referente con View pero sin Change no edita desde React; es una diferencia funcional que debe aceptarse y comunicarse. Si requiere reasignar permisos, sería otra acción expresamente autorizada, nunca un seed automático de esta planificación |

**Recomendación del agente: R1**, porque el objetivo es migrar conservando reglas
y presentación del origen. Eso no significa conceder edición con solo View: la
asociación al centro y el predicado de dominio siguen siendo obligatorios.
R2 queda descartada por la elección explícita de R1.
No se decide que el contrato Django sea el correcto de seguridad solo por ser
anterior, ni que el contrato INET haya sido aceptado por estar mergeado.

## Aceptación futura con R1

- Referente propio con View sin Change: GET de formulario y submit permitidos
  según predicado Django, validaciones y datos válidos; confirmar persistencia.
- Referente de otro centro con mismos permisos: nunca edita; asegurar scope de
  get_item y el predicado de dominio, tanto por UI como por request directo.
- Provincial en scope y fuera de scope, con/sin Change; SSE y admin visualizador
  read-only, superusuario y usuario anónimo según contrato vigente.
- Mantener controles específicos de campos/formset, provincia y contactos;
  autorización a editar centro no concede gestionar cualquier recurso VAT.
- Sin cambios silenciosos de grupos ni privilegios de otros backends. Pruebas
  con permisos efectivos reales en fixture, sin mockear siempre can_mutate=True.
- Diff de ficha/formulario/denegación por rol y viewport, con baseline I1 y
  aceptación humana. Un test del predicado no prueba persistencia ni UI.

Reversión: desactivar circuito nuevo ante fallo, conservar versión previa
compatible; no conceder permisos como fallback. R1 no autoriza activar ahora.

R1 resuelve la dirección del contrato de edición de centros INET. Implementación,
revisión técnica y pruebas siguen pendientes; la autorización no está demostrada
por este documento. Admin/Unfold #2789 sigue aparte y no se toca.
G1/P1/C2/E2/I1/W1/M2 no se reabren.

## Matriz mínima de fixtures de autorización

Cada fila usa sesión con requisitos web resueltos y roles/permisos efectivos,
sin mockear el predicado para que siempre permita. Los roles son puros salvo
indicación explícita; un doble rol requiere caso adicional según fuente.

| Perfil sintético | View | Change | Relación/alcance | Resultado de edición R1 |
|---|---|---|---|---|
| Referente | Sí | No | Asociado al centro propio | Permitido por rama referente |
| Referente | Sí | Sí | Otro centro sin asociación ni otro rol | Denegado, ningún cambio |
| Consulta sin rol de gestión | Sí | No | Sin asociación | Denegado, View no concede edición |
| Referente propio | No | No | Asociado, sin otros permisos que concedan View | Denegado por guard de lectura |
| Provincial | Sí | Sí | Scope territorial válido del centro | Permitido según rama provincial |
| Provincial | Sí | No | Scope válido, sin rama referente/SSE | Denegado por requisito de Change vigente |
| Provincial | Sí | Sí | Fuera de scope, sin otra rama habilitante | Denegado, ningún cambio |
| SSE | Sí | Según permiso efectivo de fixture | Rama SSE vigente | Mismo resultado del predicado Django |
| Admin visualizador puro | Sí | No | Lectura global, sin rol habilitante | Denegado, conserva solo lectura |
| Anónimo | No | No | Ninguna | Rechazo por autenticación/guard vigente |

Comprobar formulario, request directo de submit y botón/entrada de ficha;
revisar contactos y datos del centro antes/después. Estos resultados son
criterios esperados del contrato elegido, no tests ejecutados. No generalizar
la excepción de la rama referente a DELETE, alta u otros recursos del API.
