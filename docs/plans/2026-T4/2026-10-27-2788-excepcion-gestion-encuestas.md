# Control web: excepción de gestión de encuestas con respuesta pendiente

Estado **E2, S1 elegida explícitamente por el responsable («s1»)**. No modificar ahora controles, permisos,
formularios ni endpoints. Esta administración de encuestas pertenece a la
aplicación; no es Django admin/Unfold #2789, que continúa excluido.

## Evidencia concreta

Fuente `59a8f797688c9e762d5a4e9eaa187698ffade8aa`, coincidente con checkout para
los middleware revisados:

- `src/backends/sisoc_core/encuestas/middleware.py`: `_is_exempt_path` permite
  paths `/encuestas/` cuando `request.user.has_perm('encuestas.change_encuesta')`.
- FirstLoginPasswordChangeMiddleware y ProfileConfirmationMiddleware corren
  antes: la excepción no resuelve contraseña, perfil o acceso web denegado.
- Responder/posponer/descartar e inicio tienen sus exenciones propias. Responder
  una encuesta segmentada no requiere Change; esas reglas no están en discusión.
- Las rutas administrativas de encuestas siguen sus decoradores de permiso de
  cada acción. La excepción quita un bloqueo previo de encuesta, no autoriza
  publicar, importar, exportar o editar sin el permiso de la acción.
- El modal pendiente puede seguir apareciendo en HTML de gestión vía context
  processor. Una exención de middleware no prueba que su overlay deje operar
  cómodamente en navegador. No se ejecutaron UI/HTTP ni se leyó DB real.

La propuesta anterior de gate API exige ready a toda operación de negocio;
traducida literalmente eliminaría esa excepción. Eso cambia comportamiento de
acceso y no queda aprobado por pedir React, por elegir G1 o por R1 de centros.

Caso concreto: persona con acceso web, contraseña/perfil resueltos y Change de
encuesta, tiene ronda obligatoria pendiente y pide una operación de gestión para
la que posee permiso. Hoy el middleware de encuesta la exceptúa; un gate nuevo
ready-universal la bloquearía. No se afirma que haya un incidente desplegado.

Ver [decisión registrada](../../registro/decisiones/2026-10-27-2788-gestion-encuestas-s1.md).

## Alternativas evaluadas: S1 elegida, S2 descartada

| Opción | Regla de gate para nuevas APIs de gestión de encuestas | Ganancia | Consecuencia |
|---|---|---|---|
| S1. Conservar excepción acotada | Permitir atravesar solo el bloqueo de encuesta pendiente cuando el permiso efectivo has_perm Change y la operación corresponda a gestión actual de encuestas; después aplicar permiso/objeto de la acción | Preserva contrato origen y permite gestionar sin responder previamente; mantiene prioridad de acceso web/contraseña/perfil | El gate debe evaluar operación y estado, además de ready. Mapear endpoints/métodos explícitos, sin prefijo API libre ni excepción de otros dominios; probar todos los negativos |
| S2. Exigir responder antes de gestionar | Bloquear también gestión hasta resolver la encuesta, incluso con Change; conservar respuesta/logout/remediaciones propias | Regla uniforme para gestión y negocio | Quita la excepción vigente y puede impedir corregir/gestionar una ronda antes de responderla. Es cambio funcional de acceso que debe aceptarse expresamente |

**Recomendación del agente: S1**, dado el objetivo de preservar comportamiento
actual. No significa que Change otorgue publicar/importar/exportar todo ni que
habilite omitir contraseña/perfil. S2 queda descartada tras la elección explícita.

## Contrato de aceptación futuro con S1

1. Con encuesta pendiente y requisitos superiores resueltos: gestor con Change,
   permiso de acción válido y ámbito correcto atraviesa ese bloqueo y accede
   a la operación; las validaciones y efectos de negocio siguen vigentes.
2. Mismo usuario sin permiso específico de publicar/exportar/etc.: rechazado sin
   efectos. No asumir que el permiso habilitante de excepción concede la acción.
3. Falta acceso web, contraseña o perfil: no atraviesa esos bloqueos por Change.
4. Sin Change: solo respuesta/remediaciones propias disponibles según su contrato;
   no ampliar excepción a catálogos, Insumos, VAT, usuarios o PAS.
5. UI de modal/gestión y API directa coherentes; no marcar ready cuando sigue
   pendiente encuesta ni vaciar los requisitos para permitir la gestión.
6. Con S1, revisar allowlist de endpoints/métodos de gestión desde urls.py y
   contratos de sus acciones, conservando has_perm para este chequeo específico.
   No crear bypass por un header, rol enviado por React o URL arbitraria.

S1 resuelve la dirección de autorización del gate para este caso. La
implementación y su revisión técnica/evidencia siguen pendientes; no se afirma
que el acceso esté probado. El mapa de rutas/métodos equivalente se conserva en
[política fuente de encuestas](2026-10-27-2788-encuestas-politica-fuente.json),
sin activar rutas nuevas ni generar un bypass por prefijo.

## Precisión operativa del mapa

El mapa fuente registra veinte rutas: diecisiete de gestión/descarga y tres de
respuesta/remediación. Métodos GET/HEAD/POST propuestos según handlers y vistas
genéricas leídos, no prueba de dispatch. Vincular cada API nueva a su operación
y método fuente antes de activar; un prefijo no la incorpora automáticamente.

Change habilita la excepción al bloqueo de encuesta, no es requisito universal:
Approve sin Change conserva su permiso cuando ready, pero con encuesta pendiente
no recibe la excepción histórica Change. No asignar privilegios por seed para
alterar esa combinación. Change no permite posponer/descartar una obligatoria.
Contexto sigue mandatory_survey; no crear un ready ficticio ni cerrar el modal
silenciosamente. Revisar menú/botones/modal contra referencia visual.
