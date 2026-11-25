# Cambio: aclaración del Formulario I en la PWA (#2875)

## Alcance

El issue #2875 pide reemplazar la aclaración del documento Formulario I,
Certificación de Cuenta Bancaria, por «Presentar solo si cambió la cuenta o los
firmantes» y actualizar los datos de convenio de la PWA.

El solicitante confirmó que los cambios de Datos de Convenio se limitan a
PNUD / Abordaje Comunitario; Alimentar Comunidad conserva su presentación.

## Implementación

En SISOC se modifica únicamente la descripción del catálogo existente
`DocumentacionAdjunta.CATEGORIAS_CONFIG`, en
`src/backends/comedores/rendicioncuentasmensual/models.py`. Se sigue el patrón
de `categorias_mobile` que ya consume la API de rendiciones. El Formulario I
sigue siendo opcional, admite varios archivos y conserva su posición.

La API de Comedores ya expone los campos de convenio pedidos en
`datos_convenio_mobile`. No se cambian serializers, permisos, endpoints, modelos
de datos ni migraciones. La selección y presentación de esos campos se realiza
en el repositorio `secretarianaf/Espacios-Comunitarios`, en la rama
`fix/2875-datos-convenio`, desde el último `origin/development`.
También se actualiza allí la descripción local del Formulario I para offline.

## Base y entornos al comenzar

- SISOC: rama `fix/2875-datos-convenio-pwa` desde `origin/development`
  `6836d7d54`; la rama local anterior estaba 198 commits detrás y se conserva.
- PWA: base `891a2ce`, último `origin/development` al comenzar.
- Según GitHub Actions, QA y homologación tienen un despliegue exitoso del
  2026-11-16. El último despliegue exitoso registrado de PRD es del 2026-11-05;
  el intento posterior de 2026-11-16 fue bloqueado por el gate de autorización.
  `main` contiene el código de ese intento, aunque el deploy no se ejecutó.

## Verificación

- Contrato API móvil y reglas de rendición: **86 tests aprobados**.
  Incluyen la descripción devuelta en el detalle y el catálogo de ambas líneas.
- Black sobre los tres archivos Python modificados: aprobado.
- Pylint del modelo: **10/10**.
- `makemigrations --check --dry-run`: sin cambios pendientes.
- Validación de rutas documentadas: sin referencias obsoletas ni rotas.
- El solicitante pidió abrir los PR después de recibir la vista local y los
  resultados. No se afirma una aceptación visual humana; CI queda pendiente
  de la publicación. No se autoriza merge ni despliegue.

La corrección no requiere una secuencia de migraciones ni cambia la compatibilidad
del JSON. Para revertir basta restaurar la descripción del catálogo; no se alteran
documentos, estados de rendición ni respuestas existentes.
