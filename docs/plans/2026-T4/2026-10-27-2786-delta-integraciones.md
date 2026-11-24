# Delta tras integrar Unfold e INET (#2786–#2788)

Fecha: 2026-10-27. Fuente congelada:
`59a8f797688c9e762d5a4e9eaa187698ffade8aa` de `origin/development`, recuperado
por fetch sin cambiar checkout, rama ni archivos ajenos. No representa revisión
desplegada ni referencia visual aceptada.

## Trabajo paralelo verificado

| Trabajo | Estado consultado | Consecuencia |
|---|---|---|
| #2789 / PR #2793 Unfold | MERGED, merge `f6a9a411e2c9787f95fe15aaa7466ce119258d91` | Conservar admin/settings/CSP integrados; no aplicar propuestas sobre sus versiones anteriores |
| PR #2794 INET | MERGED, merge `59a8f797688c9e762d5a4e9eaa187698ffade8aa` | No duplicar app/API/formularios ni configuración; comparar flujos e implementar solo remanente |

Heads consultados: #2793 `ef0f1b0c5ae394bd0c240f24409fa0767ed47a08`;
#2794 `94412ef66a36bd530df2d5d57f7c20fd0ece8675`. Merge, CI, despliegue y
aceptación son evidencias distintas; las últimas tres no se verificaron aquí.

## Delta del registro de URLs

El inventario de 770 declaraciones y 95 familias conserva su snapshot
`ae0b0da01c546d801f18237c3c6dab29a5496790`. No se presenta como extracción
completa del nuevo HEAD. El [delta exacto](2026-10-27-2786-delta-integraciones.json)
compara 2227 → 2801 entradas del registro: 575 altas y una baja, neto 574.

| Clasificación de altas | Cantidad | Tratamiento |
|---|---:|---|
| Admin, con/sin namespace | 500 | Apoyo/exclusión del nuevo frontend; conservar #2789 |
| API INET | 63 | Contrato de app integrada, no 63 pantallas |
| Alias de reenvío de vertical | 5 | Transporte CDF existente, no flujos duplicados |
| Transporte de contribución Ciudadano | 1 | Soporte de #2807 |
| Contratos internos | 3 | Usuarios/Espacios; no reconstrucción PWA |
| Previsualización de ubicación | 2 | Soporte core/Dispositivos, coordinar mapa |
| Health de URLs | 1 | Operación, fuera de UI de negocio |

La baja es la antigua expresión `admin:app_list`, sustituida en el registro del
admin. La partición cubre todas las altas; no prueba resolver activo, permisos,
disponibilidad ni número de pantallas. Refrescar inventario completo antes de
declarar terminada la auditoría final; no borrar snapshots para aparentar vigencia.

## INET integrado: reutilización concreta

Se leyeron blobs Git del SHA objetivo: `src/backends/vat/VAT/api_inet_urls.py`,
`api_inet_views.py`, `services/inet_queries.py`, `services/inet_forms.py`,
`src/frontends/apps/inet/src/App.tsx` y configuración/manifests de frontend.
Pueden no existir todavía en el checkout local anterior; no se importó Django.

- Nueve recursos en `RESOURCES`: centros, cursos, comisiones, horarios, contactos,
  ubicaciones, planes, inscripciones y sesiones. Siete tienen `FORM_CLASSES`;
  inscripciones/sesiones disponen de operaciones específicas. Nombres no prueban
  cobertura de todos sus recorridos ni equivalencia con las vistas legacy.
- Nueve rutas React concretas más catch-all: buscador/ficha CFP, nueva/edición/
  ficha de comisión, asistencia y listado/ficha de planes. Otros formularios son
  contextuales; no declararlos ausentes por no tener ruta independiente.
- `InetSessionAuthentication` extiende SessionAuthentication y declara challenge
  `Session` para 401. Reutilizar el patrón en la API web si la comprobación real
  confirma el contrato, sin cambiar defaults globales o mezclar token/PWA.
- `InetAPIView` exige autenticación y usa helpers de permisos/scopes. Inspección
  no demuestra autorización; `/api/inet/` sigue siendo contrato existente y no
  pasa a G1 automáticamente.
- Vitest ya registra VPSL/INET/Celiaquía y Playwright tiene preview INET separado.
  Scripts incluyen `inet:types`. Añadir el piloto a esos mecanismos, conservando
  proyectos y tipos integrados. No reponer configs anteriores a #2794.
- Tema/layout compartidos cambiaron. Reconciliar exports/props/estilos antes de
  usarlos. Insumos conserva shell Django y oscuro forzado, no adopta la apariencia
  de INET por disponer de un layout común.

V02–V07 son familias con implementación integrada por contrastar por campo,
acción/rol/estado. V01/V08 y otros remanentes no quedan completados por asociación.
Ni un README ni el merge sustituyen baseline o aceptación visual.

## Próximo paso y validación

Preparar piloto en rama aislada desde esta base o una posterior reconciliada,
preservando documentos y trabajo ajeno. Config/paquetes requieren revisión técnica;
no copiar settings previos a Unfold ni regenerar archivos ajenos por rutina.

Validación: comparación JSON/partición de 575 altas, lectura AST de recursos,
fuentes y estados de PR. Sin suites/build/servidores/DB/capturas/CI/deploy. Fetch
solo actualizó refs remotas; no se modificó aplicación ni #2789.
