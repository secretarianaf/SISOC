# CDF: decisión sobre fallo de carga del selector de actividades

Estado **E2, L2 elegida explícitamente por el responsable («l2»), 2026-10-28**.
J2 fija selectores con comportamiento React; L2 aprueba separadamente esta
presentación de fallo. C2 sigue limitada a aportes de Ciudadano 360.
Ver [decisión registrada](../../registro/decisiones/2026-10-28-2787-carga-actividades-l2.md).

## Causa y evidencia disponible

Fuente `59a8f797688c9e762d5a4e9eaa187698ffade8aa`, coincidente con checkout:
`src/backends/cdf/centrodefamilia/static/custom/js/centro_familia_categoria.js`.
El evento change pone un option vacío «Cargando...», llama fetch y parsea JSON.
Solo el siguiente then reemplaza el contenido por placeholder y actividades;
no hay catch, comprobación HTTP explícita o recuperación en ese script.

Si fetch o el parseo JSON rechaza, ese then no se ejecuta: según ese flujo de
fuente, el placeholder de carga no se repone. Si se recibe JSON con formato
incorrecto, puede mostrarse primero «Seleccione una actividad» y después fallar
forEach; no generalizar todos los fallos a un único resultado. La búsqueda
estática en JS de esta app ubicó la referencia de id_actividad en ese archivo.

Esto acredita una rama sin manejo y su mecanismo, no frecuencia/afectación en
producción ni una reproducción en navegador. No se ejecutó script, HTTP, DB o
inyección de fallos bajo E2. Se usó systematic-debugging para distinguir causa
de código, hipótesis de resultado y pruebas pendientes, sin parchear al azar.

## Alternativas evaluadas: L2 elegida, L1 descartada

| Opción | Presentación futura React ante fallo | Ganancia | Consecuencia |
|---|---|---|---|
| L1. Paridad estricta del fallo actual | Conservar presentación de carga/vacío que resulte de la rama actual, documentándola y verificándola en entorno; sin nuevo aviso/reintento | No introduce excepción visual adicional al alcance aprobado | Mantiene falta de recuperación de ese flujo; puede requerir cambiar categoría o recargar para volver a intentar. No declarar éxito ni lista vacía de negocio para ocultar el fallo |
| L2. Error y reintento acotados | Si falla la petición/HTTP/JSON esperado, salir de loading, mantener categoría y resto de campos, mostrar «No se pudieron cargar las actividades.» y acción «Reintentar» junto al selector; no habilitar selección inválida | Permite recuperar sin perder el formulario y distingue fallo de lista vacía válida | Diferencia visible expresamente aceptada solo en fallo de este selector. Happy path, diseño del formulario, datos y permisos permanecen iguales; requiere captura de ambos estados y prueba de recuperación |

**Recomendación del agente: L2**, como excepción de fallo limitada a
categoría→actividad CDF, no un cambio del sistema de notificaciones ni de todos
los selects. No introducir retry automático, timeout arbitrario, cache persistente
o nueva dependencia. Reintentar hace el mismo GET de opciones de la categoría
actual; no guarda actividad ni reenvía POST.

## Experimento futuro y aceptación

1. Fixture sintética con categorías A/B y actividades propias, mismo formulario
   abierto en referencia/candidato. Registrar valores iniciales sin datos reales.
2. Bloquear/rechazar GET, devolver HTML no JSON y respuesta no-200; observar el
   estado real de referencia antes de fijar baseline. No aceptar como demostrado
   el resultado inferido únicamente por inspección.
3. Caso control 200 array vacío: vacío válido, sin mensaje de fallo. Caso válido:
   opciones correctas con el mismo aspecto, sin preselección de otra categoría.
4. Con L2 elegida, un clic Reintentar recupera opciones cuando vuelve el GET; resto del
   formulario sigue intacto. Una respuesta tardía de A no reemplaza B ni su error.
5. Sin sesión/permiso: conservar autenticación/denegación real, no interpretarla
   como vacío o dar acceso por botón Reintentar. Ningún caso ejecuta mutación.
6. Captura/diff desktop/móvil con nueva diferencia de fallo documentada por URL,
   estado y decisión humana. No rebaselinar el formulario entero ni ocultar el
   mensaje con máscara. Probar teclado/foco sobre Reintentar y errores de Form.

L2 queda elegida; su implementación requiere reproducir el comportamiento en
fase autorizada. No se ofrece como arreglo definitivo de un incidente no investigado.
Admin/Unfold #2789 aparte; E2 y elecciones anteriores siguen vigentes.
