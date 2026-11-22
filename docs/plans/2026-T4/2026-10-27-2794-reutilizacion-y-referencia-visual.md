# INET integrado: reutilización comprobada y referencia Django I1

Estado: **E2, planificación; I1 elegida**. Avanza el contraste
del punto 3 y evita cerrar contratos VAT o tareas visuales con una referencia
no elegida. Fuente fija: `59a8f797688c9e762d5a4e9eaa187698ffade8aa`.
El responsable eligió I1; [registro](../../registro/decisiones/2026-10-27-2794-inet-referencia-i1.md).
No se modificó INET, #2789, paquetes ni aplicación.

## Qué se comprobó realmente

El [índice de evidencia](2026-10-27-2794-reutilizacion-inet-evidencia.json)
expande estáticamente las rutas de `VAT.api_inet_urls` a partir de `RESOURCES`
y `FORM_CLASSES`, sin importar Django. Sus 63 nombres coinciden con las
63 entradas de namespace `inet_api` del registro versionado; no se ejecutó el resolver.
Cada ruta conserva
view, recurso y handlers HTTP definidos en su clase; no se presume que todo
handler permita cualquier recurso/rol o que eso pruebe paridad de campos.

Nueve recursos: centros, cursos, comisiones, horarios, contactos, ubicaciones,
planes, inscripciones y sesiones. Siete usan forms existentes de VAT. Servicios
de inscripción/sesión y helpers de scope/permiso se conservan en su dueño.
No reimplementar esas APIs/forms/services por iniciar otra parte de la migración.

## Cobertura localizada frente a cobertura aún no demostrada

«Presente» significa código identificado. No significa prueba funcional,
cumplimiento de todo el flujo, comparación visual o aceptación humana.

| Familia | Código React/API localizado | Qué queda por contrastar o planificar |
|---|---|---|
| V01 Vouchers/parametrías | No hay recurso directo entre los nueve | Gestión y acciones de crédito/parametrías no se consideran migradas porque otros bloques muestran créditos |
| V02 Asistencia/resultados | Vista React de asistencia y `InetAsistenciaView` GET/PUT | Reportes/resultados y recorridos legacy adicionales; comparar valores/alcance con servicio de asistencia |
| V03 Inscripciones/alumnos | Helpers de ciudadano, `InetInscribirView` POST, `InetEstadoView` GET/POST y recurso inscripciones | Estados, reglas, altas sin DNI y recorridos adicionales por rol; no confundir helper contextual con toda pantalla legacy |
| V04 Comisiones/horarios | Páginas de nueva/edición/ficha, recursos y helpers de horarios | Wizard, regeneración de sesiones, historial y permisos por estado contra los servicios actuales |
| V05 Cursos/ofertas | Recurso cursos y formulario contextual con `VAT.forms.CursoForm` | Listados/rutas independientes y otras acciones de ofertas; fijar diferencias de campos/orden por recorrido |
| V06 Centros/contacto/ubicación | Buscador/ficha CFP y tres recursos/forms de esos nombres | Generación de usuarios, identificadores y modalidad institucional no tienen recurso directo en ese registro; revisar sus recorridos sin asumir cobertura |
| V07 Planes/catálogos | Lista/ficha y form de planes | Catálogos curriculares restantes: opciones de un formulario no equivalen a pantallas de gestión |
| V08 Evaluación/reportes | Sin recurso directo entre los nueve | Evaluaciones y reportes restantes requieren contrato propio; no se completan por tener asistencia |

En V02–V07 hay reutilización confirmada de código, pero equivalencia funcional
y visual **parcial/no verificada**. V01/V08 son remanentes por investigar, sin
afirmar que todo su negocio carezca de API o service existente.

`InetSessionView` devuelve username, nombre, permisos VAT y permiso de planes;
hereda `check_read` del recurso centro. No es el contexto transversal de menú,
requisitos web y footer de #2798. Reutilizar el patrón de sesión/401, no sustituir
el contrato transversal por esta vista ni darle acceso a todos por comodidad.

## Diferencia visual concreta encontrada en código

### Contraste de operaciones integradas antes de derivar trabajo nuevo

Fuente adicional: `src/backends/vat/VAT/api_inet_views.py` en el mismo SHA;
lectura estática, sin importar Django ni ejecutar requests. La existencia del
handler genérico no implica permiso para todos los nueve recursos.

| Operación integrada | Semántica localizada que se reutiliza | Comparación requerida para cerrar su circuito M2 |
|---|---|---|
| Collection GET | `check_read`, resource_queryset/filter_resource_queryset y paginación INET 10 por defecto, máximo 200 | Comparar filtros/orden/páginas de cada pantalla legacy; no heredar 10 en Insumos que usa 20 |
| Collection POST | Solo recursos FORM_CLASSES, serializer de payload, authorize_create y Form actual; transacción DB | Campo/initial/opción/permiso por recurso; no copiar form.save omitiendo ramas especiales ni duplicar endpoint |
| Centros POST/PUT | crear_centro/actualizar_centro y contacto_formset; PUT sin sección contactos conserva existentes | Omitido frente a vacío, contacto principal, errores de formset y scope. No borrar contactos por normalizar payload ausente a [] |
| Comisiones POST | crear_comision y validate_horarios, con datos del curso del Form | Wizard completo, horarios y errores por paso contra recorrido legacy |
| Comisiones PUT | check_write; reemplazar_horarios exige Add y Change de comisionhorario; cambio de fechas regenera sesiones excluyendo no programadas | Horarios omitidos frente a lista enviada, clases realizadas/canceladas y cambio concurrente; no relajar permisos para hacer pasar UI |
| Planes POST | provincia desde usuario en servidor | No aceptar provincia de payload como autoridad; ámbito y rol existentes |
| Contactos POST/PUT | sync_responsable_principal después de guardar | Principal y representación en ficha/otras pestañas; no reemplazar por guardado genérico |
| Horarios POST/PUT | Generación/regeneración mediante SesionComisionService | Fechas/sesiones y conservación de historial, no solo feedback de formulario |
| Detail DELETE | check_read/check_write; inscripciones/sesiones rechazadas; horario con sesiones no programadas rechazado; demás item.delete(user=...) | Preview/confirmación y permiso/efectos propios; no inferir DELETE válido por URL genérica ni convertir borrado lógico en físico |
| Inscripciones/asistencia | Endpoints de workflow específicos, distintos de CRUD genérico | Transiciones/validaciones/scopes, respuestas de error y formulario consumidor, conservando servicios actuales |

Estos son controles concretos de reutilización, no una declaración de paridad con
todas las vistas Django. Para cada fila registrar la página/formulario legacy y
React, acción/campos/roles, resultado/efecto, caso positivo/negativo y diff I1.
Si un endpoint integrado exige View además de Change y una vista legacy difiere,
documentar el contraste antes de tocar permisos: la migración no concede ni
retira permisos por conveniencia. No se resuelve esa equivalencia solo con tabla.

Los campos exactos de recursos restantes se completan desde sus Forms/helpers
y pantallas al preparar su ficha, usando los 63 nombres ya indexados. Un recurso
API no equivale a una pantalla y opciones de catálogo no equivalen a su ABM.

| Elemento | Django de centros VAT | React INET integrado |
|---|---|---|
| URLs comparables | `/vat/centros/`, `/vat/centros/<pk>/` | `/v2/inet/centros/`, `/v2/inet/centros/<id>/` |
| Shell | Templates extienden `includes/main.html` → `includes/base.html` | `App.tsx` usa `V2Layout` de `@sisoc/ui` |
| Tema inicial | Base incluye `theme_force_dark_head.html`; esos dos templates no sobreescriben `script_tema` | `initialMode` devuelve claro salvo `localStorage['app.theme'] === 'dark'` |
| Control de tema | Shell legacy fuerza oscuro | `V2Layout` muestra botón para alternar claro/oscuro y guarda `app.theme` |
| Alcance probado | Herencia/defaults leídos en fuente | Estado/control leídos en fuente, sin ejecutar navegador |

Esto demuestra una diferencia de política de tema/controles si se renderizan
esas fuentes; no mide píxeles, aceptación ni cuál URL está desplegada. No se
consultó producción ni se hicieron capturas. Tampoco se decide que toda la UI
de INET sea incorrecta por esa diferencia: hay dos referencias posibles.

Fuentes exactas en el SHA: `src/backends/vat/VAT/templates/vat/centros/centro_list.html`,
`centro_detail.html` en ese directorio, `src/backends/kernel/templates/includes/main.html`,
`includes/base.html` y `includes/scripts/theme_force_dark_head.html` bajo templates
del kernel; `src/frontends/apps/inet/src/App.tsx` y
`src/frontends/packages/ui/src/layout.tsx`.

## Alternativas y elección de referencia I1

| Opción | Contrato visual de INET | Ganancia | Costo / consecuencia |
|---|---|---|---|
| I1. Mantener Django como referencia | Exigir paridad con las vistas Django de cada recorrido; reutilizar APIs/services y adaptar React solo donde un diff justificado lo requiera | Conserva literalmente el requisito original de no rediseñar y no descarta el backend integrado | Puede requerir ajustar presentación del INET recién integrado; esfuerzo desconocido hasta comparar, sin borrar su trabajo ni alterar otras apps |
| I2. Tomar INET React como referencia específica | Conservar su diseño como objetivo propio de INET; llevar remanentes relacionados a esa referencia, sin extenderla a otros módulos | Aprovecha su presentación integrada y evita forzar el shell Django sobre ella | Añade una excepción a la fidelidad al Django anterior de INET; debe elegirse expresamente y fijarse/aceptarse con capturas sintéticas después |

**Recomendación del agente: I1**, dado el requisito vigente de diseño idéntico.
Si INET React ya tiene aceptación de diseño del responsable fuera de esta
conversación, I2 permite registrarla como dirección específica sin fingir una
comparación visual que no hicimos. En ninguna opción se rehace automáticamente
INET ni se considera su merge aceptación de todas las pantallas/roles/estados.

Esta elección fija la referencia, no aprueba capturas todavía inexistentes.
I1 queda confirmada y no se vuelve a solicitar. I2 es alternativa descartada;
la planificación continúa con Django como referencia y reutilización backend.
G1/P1/C2/E2 siguen vigentes. C2 autoriza otro caso acotado (fallas de aportes 360)
y no decide I1/I2. No se cambia el paquete compartido `V2Layout` para todos los
consumidores como consecuencia automática de ninguna opción.

## Efecto sobre los cinco puntos pedidos

| Punto | Avance de esta continuación | Pendiente después de elegir |
|---|---|---|
| 1 Contratos | Precisión fuente de Insumos/identidad/encuesta y efectos; no se declaran cerrados los contratos de las 95 familias | Continuar por dominio y asignar rutas/métodos/campos a sus slices |
| 2 Fronteras | Prioridad y remediaciones sin deadlock funcional; IAM vs visibilidad y revocación de tokens documentados | Contratos operativos/exenciones exactas y G1, con pruebas diferidas según E2 |
| 3 Reutilización | 63 rutas INET expandidas y contrastadas con registro; tabla por V01–V08; I1 elegida | Contrastar equivalencia por campo/acción/rol, no solo presencia |
| 4 Visual | Identificada la incompatibilidad de referencias de INET; manifiestos existentes se preservan | Extender cobertura a todas las familias sin baseline ambiguo ni aceptar capturas por defecto |
| 5 Tareas | Criterios/negativos compartidos refinados; no se crean tareas «listas» con contrato visual sin elegir | Refinar issues acotados y dependencias con contratos suficientemente definidos; no generar 214 tickets |

La elección afecta experiencia y posible replanificación de presentación ya
integrada: corresponde al responsable. Se deja el trabajo concreto revisable
antes de solicitarla. No se detiene por una preferencia rutinaria de nombres.

Validación actual: expansión AST/nombres contra registro y referencias fuente.
Sin aplicación, endpoints HTTP, DB, browser, screenshots, CI, commit/push ni deploy.

## Decisión material localizada al contrastar autorización

[Edición de centros R1 elegida](2026-10-27-2794-permisos-edicion-centro.md): Django
usa View y predicado de centro; API INET añade Change. El grupo seed CFP tiene
View/rol referente sin Change. No afirmar impacto real sin permisos efectivos
del entorno. El responsable eligió R1: preservar regla Django de edición,
sin otorgar Change al grupo CFP ni retirarlo globalmente de otros recursos.
Implementación, revisión técnica y pruebas quedan para fase futura; I1 visual
es una decisión separada y E2 continúa.
