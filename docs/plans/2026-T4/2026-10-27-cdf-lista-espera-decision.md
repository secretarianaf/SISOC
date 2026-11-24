# Lista de espera CDF: decidir recorrido antes de planificar una pantalla nueva

Estado: **E2, W1 elegida; contrato de alias para implementación futura**. Afecta CDF02 y
la URL independiente de lista de espera; no cambia todas las actividades CDF.
Fuente: `59a8f797688c9e762d5a4e9eaa187698ffade8aa`.
El responsable eligió W1; [registro](../../registro/decisiones/2026-10-27-cdf-espera-w1.md).

## Hechos, hipótesis y límite de evidencia

| Punto | Evidencia fuente |
|---|---|
| URL declarada/registrada | `/centrodefamilia/centros/<centro_id>/actividades/<actividad_id>/lista-espera/`, nombre `actividadcentro_lista_espera` |
| Vista | `ParticipanteActividadListEsperaView`, ListView con sesión, permiso `centrodefamilia.view_centro` aplicado desde urls |
| Consulta | ParticipanteActividad por actividad y estado `lista_espera`; agrega centro_id/actividad_id al contexto |
| Template declarado | `centros/participanteactividad_lista_espera.html`, sin archivo localizado en el árbol versionado revisado |
| Loaders fuente | Kernel/templates y APP_DIRS; settings CDF aplica ajustes comunes, sin declarar otra ubicación para ese template |
| Experiencia que sí tiene template | Ficha `actividadcentro_detail`: `/centrodefamilia/centros/actividades/<pk>/detalle/`, con sección Lista de Espera que usa el servicio existente |
| Enlaces encontrados | No se localizaron referencias literales a la ruta independiente en Python/HTML/JS de CDF/kernel fuera de su declaración/template_name; no prueba ausencia de bookmarks o consumidores dinámicos |

La configuración/listado fuente sugiere que una petición que llegue al render
de esa vista puede fallar por template ausente. **No se ejecutó esa petición**,
no se inspeccionaron mounts externos ni se acredita incidencia en producción.
No se propone un parche definitivo basándose solo en la hipótesis.

La incertidumbre de producto es qué recorrido debe existir después: la fuente
no ofrece una pantalla independiente visible para copiar, pero sí una sección
equivalente dentro de una ficha. No se necesita cambiar reglas de participación
para decidir dónde se presenta esa lista.

## Opciones preparadas

| Opción | Recorrido que se planifica | Ganancia | Costo / consecuencia |
|---|---|---|---|
| W1. Usar sección de la ficha de actividad | Lista de espera vive en la ficha existente. Conservar la URL independiente como acceso compatible hacia esa ficha/sección, con comportamiento de alias definido y validado | Reutiliza presentación existente, evita inventar una pantalla y preserva enlaces externos mediante compatibilidad | Cambia el comportamiento previsto de la URL independiente; hay que definir destino/foco, validar IDs/permisos y probar el alias. No declararlo una migración de una página que hoy no tiene baseline |
| W2. Mantener pantalla independiente | Definir una página separada, tomando como referencia la tabla/tema de la ficha y aprobando su composición antes de migrarla | Conserva intención de tener un acceso dedicado | Agrega trabajo de definición/corrección y una referencia nueva que no puede acreditarse con el template ausente; necesita aceptación expresa de esa pantalla |

**Recomendación del agente: W1**, por ser la opción más pequeña que reutiliza
una experiencia existente. No elimina la URL ni copia reglas de negocio. El
tipo exacto de alias/redirect y compatibilidad se especifican tras elegir;
no se emite un redirect ni se modifica la app en esta fase.

W2 también es posible si hay una necesidad funcional de página independiente.
En esta migración W1 queda confirmada y W2 descartada. No se vuelve a solicitar
esa elección ni se planifica una nueva pantalla por el template ausente.
No se marca el caso como migrado conservando un supuesto error 500 ni se
elimina la ruta por no haber encontrado un enlace en el menú.

## Contrato y aceptación después de elegir

- Conservar services de participación/espera/promoción y autorizaciones fuente;
  revisar alcance de objeto y relación centro/actividad antes de la entrega.
  La elección visual W1/W2 no aprueba un scope nuevo ni una ampliación de datos.
- Cubrir lista con/sin participantes, usuario autorizado/denegado, actividad o
  centro inexistentes/incongruentes y acceso directo al path antiguo.
- Separar GET de consulta de POST de promoción. No modificar la política de
  cupo, orden o qué persona se promueve por resolver esta pantalla.
- Probar reload, enlaces, query/foco y retorno, escritorio/móvil, y comparar
  visualmente la sección/pantalla aprobada. El alias debe quedar en el manifiesto.
- En fase futura autorizada, reproducir el render actual y verificar cómo llega
  el runtime a los templates antes de afirmar causa/corrección. Registrar fuente,
  resultado y límites si un entorno real usa recursos externos distintos.

Fuentes: `src/backends/cdf/centrodefamilia/urls.py`,
`src/backends/cdf/centrodefamilia/views/participante.py`,
`src/backends/cdf/centrodefamilia/views/actividad.py`,
`src/backends/cdf/centrodefamilia/templates/centros/actividadcentro_detail.html`,
`src/backends/cdf/cdf_runtime/settings.py` y `src/backends/config/settings.py`.

Las decisiones G1/P1/C2/E2/I1 permanecen. Esta elección es de experiencia/alcance,
no de una preferencia interna de implementación. Validación actual documental
y estática, sin código de aplicación, DB, servidor, capturas ni despliegue.
