# #2785 — Seguimiento mensual por comedor en React

El enlace **Seguimiento Mensual** de Acompañamiento conserva la URL
`/rendicioncuentasmensual/rendicioncuentasmensual/<comedor_id>/`. Con el
vertical de Comedores activo y su build disponible, Django entrega el shell
de React. Si falta el build o se desactiva el vertical, la vista Django
anterior sigue respondiendo en la misma URL.

| Contrato | Comportamiento |
| --- | --- |
| Listado | `GET /api/web/comedores/rendicioncuentasmensual/por-comedor/<comedor_id>/` proyecta la lista que arma la vista nativa. Conserva su alcance de proyecto, orden y validación de `page`; no aplica filtros propios del listado global. |
| Acceso | Conserva los permisos de lectura de la URL canónica tras el control de sesión y acceso web. La respuesta JSON no se cachea. |
| Navegación | Incluye el regreso a Acompañamiento y los enlaces canónicos de alta, detalle, edición y baja. La interfaz no muestra acciones que su destino nativo rechazaría. Sus permisos, métodos y escrituras no cambian. |
| Límites | No cambia el listado global, los procesos de auditoría ni los documentos. No introduce una política nueva de alcance por usuario. |

## Verificación

- Pytest: URL canónica con shell activo y fallback nativo, denegaciones,
  conservación del alcance de proyecto y enlaces, exclusión de bajas, errores
  de página y recurso inexistente, y contrato de solo lectura.
- Vitest: coincidencia exacta de la URL, query `page`, datos y navegación,
  acciones autorizadas, estado vacío y foco por teclado en la tabla.
- El smoke autenticado en un navegador real y mediante el proxy del core
  corresponde a la integración del router y registro de URLs.
