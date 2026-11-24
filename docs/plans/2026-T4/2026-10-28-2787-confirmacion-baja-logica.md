# Confirmación React: preview de baja lógica y efectos técnicos

E2: contrato fuente compartido para confirmaciones ya inventariadas, sin ejecutar
bajas/restauraciones. No ampliar reescritura a Celiaquía/VPSL/admin excluidos por
usar el mismo helper. Cada vista conserva permiso/objeto/mensaje/retorno propios.

## Representación existente que debe proyectarse explícitamente

cascade_preview: total_afectados,total_baja_logica,total_borrado_fisico,
desglose_por_modelo[] con modelo_key/modelo/cantidad/modo(baja_logica|borrado_fisico)/
ejemplos, ejemplos_por_modelo y operacion(delete|restore). Hasta cinco ejemplos por
grupo por defecto. Mantener distinción visual «Borrados físicos técnicos», no
contador genérico ni DTO completo de objetos relacionados con campos privados.

## Semántica y límites

Plan recorre reversasFK/one-to-one CASCADE, no PROTECT/SET_NULL/M2M automáticamente.
Hijos con contrato softdelete se marcan; sin contrato pueden borrarse físicamente
según exclusiones. POSTreconstruye plan desde objeto, no aplica IDs propuestos por
cliente ni snapshotGET; sin tokencongelado/select_for_update acreditado en recorrido.
Cambios entreGET/POST pueden cambiar afectados; no prometer snapshotestable.

EjecuciónDB transaccional procesa físicos, deleted_at/deleted_by, actualizaciones
operativas por modelo y señales; no DELETEfísico general. No limpieza manual de
relaciones React. Vista obtiene objeto autorizado y pasa actor, motor no reemplaza
autorización. Mixin instance.delete(user,cascade=True); retorno y feedback de dueño.
No nuevo motor/APIglobal por comodidad: proyección mínima de cada confirmación.

DU01 Comedor.dupla PROTECT no se recorre CASCADE: no inventar desasignación automática.
Consecuencias de acceso necesitan observar señales/relaciones, no inferirlas de FK.
La aprobación de confirmación no autoriza operaciones que el usuario no puede hacer.

## Casos futuros

Sin hijos/solo soft/soft+hard, cinco ejemplos truncados, actor/objetoajeno/campos
permitidos en muestras, cancelar sin efectos, hijos añadidos trasGET, objetoyaoculto,
error con rollbackDB y actor correcto. Comparar efectos completos, no solo mensaje.
Formulario/preview/botones/foco/desktop-móvil y paresreferencia-candidato-diff porURL
más acumulado. Todo sintético, sin DB/app/tests/navegador o capturas ejecutados.

## Fuente

src/backends/kernel/core/soft_delete/preview.py:10–23;
cascade.py:81–108,170–219,289–319,447–490; base.py:159–174;
state_sync.py:14–23; view_helpers.py:90–117;
src/backends/kernel/templates/components/delete_confirm.html:21–39.
Cascade/preview contrastados con59a8f797688c9e762d5a4e9eaa187698ffade8aa,
otroscheckout; padre leyó preview. CodeGraphsync; sin mutación, CI o deploy.

- [DU01](2026-10-28-2785-duplas-equipo-asignaciones-m2.md).
- [Aceptación/retiro](2026-10-27-2785-aceptacion-riesgos-y-retiro.md).
