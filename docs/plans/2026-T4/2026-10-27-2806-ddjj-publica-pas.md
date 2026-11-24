# DDJJ pública PAS: contrato de migración y decisión de acceso (#2806)

Fecha: 2026-10-27. Estado: **P1 elegida; contrato ejecutable y pruebas pendientes**.
La elección explícita «p1» queda en el
[registro de decisión](../../registro/decisiones/2026-10-27-2806-ddjj-pas-p1.md).
Inspección estática en checkout `13d367f81d6da879f1fc3e43532a894e034dc557`;
no representa revisión desplegada ni aceptación humana de la UI actual.
Continúa el [plan integral](2026-10-27-2785-migracion-integral-react.md).

## Resultado que se conserva

Migrar a React el formulario público, sus cinco pasos, validaciones visibles,
modales y confirmación. Conservar enlaces emitidos, diseño propio PAS, permisos
administrativos y reglas de presentación backend. No migrar PDF al navegador,
no reconstruir PWA ni agregar requisitos de login al visitante anónimo.

Fuentes revisadas: `src/backends/pas/pas/urls.py`, `views.py`, `forms.py`,
`models.py`, `services/ddjj_service.py`, `tests/test_ddjj.py`,
`templates/pas/ddjj_formulario.html`, `templates/pas/ddjj_confirmacion.html`,
`static/custom/js/pas_ddjj.js` y `static/custom/css/pas_ddjj.css`, todas relativas
a `src/backends/pas/pas/` salvo el prefijo completo indicado para urls.

## Contrato actual de rutas

Los resultados de la tabla corresponden a las vistas una vez atravesados los
middleware; una cookie con restricciones puede impedir llegar a ellas.

| Ruta | Método y comportamiento fuente |
|---|---|
| `/pas/ddjj/formulario/<uuid:token>` | GET disponible 200; inexistente 404; utilizada/revocada/vencida 410 con texto actual |
| Misma ruta | POST inválido 400 y formulario con errores; válido llama `presentar_ddjj` y redirige a confirmación; no disponible 410, incluso si perdió disponibilidad durante el envío |
| Misma ruta + `/municipios` | GET: invitación primero; no disponible 410 JSON; provincia ausente/no numérica devuelve `[]`; consulta ordenada por nombre y filtrada por provincia |
| `/pas/ddjj/confirmacion` | Confirmación pública genérica, sin ID de declaración, contador ni redirect automático |
| `/pas/ddjj/<int:pk>/descargar` | Sesión y `pas.view_paspersona` en URL; descarga del PDF almacenado. No pasa a ser accesible por token público |
| `/media/pas/ddjj/<path>` | Vista rechaza con 404; no cambiar almacenamiento privado por assets públicos |

Conservar ausencia de slash final de estas declaraciones y comprobar redirects
reales de slash/idioma en entorno de prueba; no corregir enlaces por intuición.

## Validación y estado del formulario

- Cinco pasos con indicador, avance/retroceso, desplazamiento y resumen final.
  Ante errores de servidor se muestra el primer paso con errores. No convertir
  un 400 en éxito ni perder campos completados después de una respuesta inválida.
- `PasDeclaracionJuradaForm` sigue siendo autoridad: datos existentes al confirmar,
  campos faltantes, longitud de domicilio, pertenencia municipio/provincia y
  respuestas dependientes. Ocultar un control no reemplaza limpiar su valor.
- Las preguntas visibles sobre gastos y divisas tienen opciones invertidas en
  JS respecto a los nombres de campos. Escribir React desde los nombres solos
  podría invertir una respuesta guardada. Probar etiqueta visible → valor enviado
  → dato/PDF con una tabla explícita para ambas respuestas antes de portar.
- Resumen y texto legal deben reproducir el contenido actual, sin reinterpretar
  requisitos del programa ni modernizar redacción por esta migración.
- `presentar_ddjj` conserva transacción y bloqueo de invitación, revalida
  disponibilidad y genera/guarda el PDF en servidor. Versionado, impacto en datos
  de persona y consumo de invitación siguen en ese servicio; React no los replica.
- El bloqueo de una invitación no demuestra por sí solo toda concurrencia entre
  invitaciones distintas de la misma persona ni atomicidad entre DB y storage.
  No se cambian esas reglas en esta migración; registrar y probar escenarios
  relevantes antes de afirmar integridad o capacidad no demostradas.
- Un envío con respuesta de red perdida queda incierto: no reintentar POST
  automáticamente ni convertir la confirmación genérica en una consulta privada.

## Entrada React y datos: propuesta del agente

Conservar la URL canónica de invitación y entregar desde ella el entry del flujo,
con validación PAS y assets públicos exactos. El router genérico
`src/backends/kernel/core/v2_frontend.py` tiene `login_required`; no sirve sin
cambios para visitantes públicos y no se debe abrir globalmente.

Reutilizar el transporte de assets donde alcance, sin enviar token/cookie a un
servidor estático para obtener un index. El servidor estático no consulta PAS.
El acceso a datos y el POST pertenecen al backend PAS, con invitación y CSRF.
El token es la capacidad de acceso, no un permiso administrativo. No mostrarlo
en logs, analytics, reportes de error, fixtures publicadas o capturas reales.

El contrato JSON y sus rutas se concretarán después de resolver la política de
sesión siguiente. No proponer una API bajo `/api/` como equivalente automático:
los middleware actuales eximen ese prefijo. La excepción de invitados de G1
tampoco determina qué hacer con una sesión web ya bloqueada.

## Decisión material: invitación válida y sesión web restringida

Fuentes: `src/backends/kernel/users/middleware.py` y
`src/backends/sisoc_core/encuestas/middleware.py`, en el orden de
`src/backends/config/settings.py`. Las rutas HTML PAS anteriores no aparecen
exentas. De la lectura se infiere este comportamiento antes de entrar a PAS:

| Estado del navegador | Resultado previsto por middleware actual |
|---|---|
| Sin sesión | Continúa a la validación de invitación, sin login obligatorio |
| Sesión sin acceso web/perfil ausente | 403 de acceso web |
| Sesión con cambio de contraseña forzado | Redirect a cambio de contraseña |
| Sesión con confirmación de perfil pendiente | Redirect a confirmación de datos |
| Sesión con encuesta obligatoria pendiente | Redirect a inicio para completar encuesta |
| Sesión sin restricciones anteriores | Continúa a la validación de invitación |

Son consecuencias estáticas de las condiciones del código, no pruebas HTTP.
Reproducirlas con sesiones y tokens sintéticos antes de establecer baseline.

| Alternativa | Resultado deseado | Ganancia | Costo / consecuencia |
|---|---|---|---|
| P1. Preservar la política actual | Visitante anónimo usa invitación; sesión restringida conserva bloqueo/remediación, tanto en entry como en datos y POST | Mantiene comportamiento durante una migración de tecnología, sin ampliar exenciones | El mismo enlace puede funcionar sin sesión y quedar bloqueado en un navegador con sesión pendiente; exige que la nueva API reproduzca el gate condicional |
| P2. Invitación independiente de la sesión | Invitación válida permite formulario/datos/POST aunque haya cookie con requisitos pendientes | Recorrido público coherente y sin interferencia de una cuenta web ajena a la invitación | Cambio funcional de acceso: excepción exacta de requisitos web, revisada en core y PAS. No elimina CSRF, validez/consumo del token ni permisos de descarga/administración |

**Recomendación del agente: P1 para esta migración**, porque conserva lo actual.
P2 es válida si el responsable confirma que el enlace debe funcionar siempre
por invitación, aceptando esa excepción acotada. No se presume que «público»
autorice P2 ni que G1 ya haya elegido esta política. La apariencia sigue idéntica
en ambas opciones; el cambio está en quién llega al formulario y al envío.

El responsable eligió P1. La elección de política queda resuelta y no se vuelve
a solicitar. El contrato público debe conservarla en entry, datos y POST;
sus rutas y adaptación JSON quedan por concretar antes de implementar.
No se agrega una exención global PAS, `/v2/` o `/api/web/` como atajo.

## Plan visual y evidencia posterior

El [manifiesto PAS](2026-10-27-2806-pas-manifiesto-visual.json) enumera casos
sintéticos en escritorio/móvil, todos `not_run`. No existe baseline aceptado,
fixtures en DB, tokens emitidos ni capturas de este flujo en esta tarea.

Conservar CSS PAS, marca y fuentes Montserrat/Lora; no sustituirlas por tema MUI,
Roboto o verde institucional. Incluir los cinco pasos, ambas ramas condicionales,
resumen, modales, errores, 404/410 y confirmación. Comparar banners, scroll móvil,
foco, inputs y texto; las pruebas funcionales complementan el diff de cada URL.
Las URLs administrativas/media entran como regresión de permisos y, si cambia
su presentación, también como diff visual. No equiparar prueba unitaria a foto.

Fuentes de tests existentes: `src/backends/pas/pas/tests/test_ddjj.py` cubre casos
de un solo uso, PDF/impacto de datos, confirmación genérica, descarga/media,
validaciones y municipio. No se ejecutó; el cliente Django normal no demuestra
CSRF real ni concurrencia. Faltan casos de sesión restringida y contratos
de entrada/API según P1, CSRF con enforcement, POST concurrentes con
DB autorizada, pérdida de respuesta y recepción real de rutas/headers.

Validación de esta definición: rutas documentales y referencias fuente. No se
ejecutaron servidores, red de aplicación, DB, suites, builds ni comparaciones
visuales. No se cambió código, configuración, #2789 ni contrato operativo alguno.
