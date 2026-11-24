# Cambio: API de formularios y mutaciones de Insumos (#2785)

## Alcance

Se agregan rutas privadas de sesión para metadatos de formulario, creación,
edición y confirmación/eliminación de INS-A. Las vistas Django, `InsumoForm` y
los servicios de dominio siguen siendo la autoridad. No se modifica la
implementación de la UI ni las vistas heredadas.

## Comportamiento

- `GET /api/web/insumos/crear/` requiere readiness y `insumos.add_insumo`, sin
  exigir permiso de lectura. `GET /<id>/editar/` usa `insumos.change_insumo` y
  `GET /<id>/eliminar/` usa `insumos.delete_insumo`; cada ruta permite su permiso
  específico sin otorgar los otros permisos ni `insumos.view_insumo`.
- Los metadatos de alta/edición se construyen desde `InsumoForm`: valores
  iniciales explícitos, opciones y choices reales. Edición conserva las opciones
  inactivas seleccionadas. Se expone solo el nombre del archivo existente; su
  enlace protegido se incluye únicamente cuando el usuario además puede ver.
- Alta y edición aceptan `multipart/form-data`, validan con el ModelForm y
  persisten mediante `save_insumo_from_form`. Los errores se proyectan con
  `form.errors.get_json_data()` y no guardan el registro si el formulario es
  inválido. La casilla `activo` ausente se interpreta según el ModelForm.
- Eliminación confirma sin mutar mediante GET y usa `delete_insumo` en POST.
  Mensajes y destino de éxito coinciden con las vistas heredadas. Los requests
  privados llevan `no-store` y `Vary: Cookie`; los POST conservan CSRF de sesión.
- OpenAPI describe cookie auth, DTOs tipados de éxito/error y confirmación. Alta
  y edición declaran `multipart/form-data` con archivo binario; el reemplazo de
  archivo y `activo` son opcionales al editar. La omisión del checkbox conserva
  la semántica del formulario; JSON/base64 se rechaza.
- XView omite el metadato solo para HEAD `/api/web/insumos/crear/` y los IDs
  numéricos en edición/eliminación, además de excepciones previamente aprobadas.
  El upstream mantiene su comportamiento en las demás rutas y métodos.

## Verificación

La prueba de metadatos observó RED (404 antes de agregar la ruta); otra de
OpenAPI detectó request/success/error sin esquemas. Ambas quedaron GREEN con
DTOs explícitos, multipart binario y archivo sintético. La suite focal combinada
(mutaciones y lectura T5) pasó con 50 pruebas, incluyendo checkbox omitido,
permisos independientes, choices inactivas, confirmación no mutante, CSRF,
archivo no persistido en rechazo y error de almacenamiento sin falso éxito.
Cobertura
de las vistas 97% y serializadores 100%. Black dejó sin cambios los cuatro
módulos Python propiedad de esta unidad. Pylint calificó los cinco módulos con
10/10 usando `HOME=/root`, `PYLINTHOME` en tmpfs y
`DJANGO_SETTINGS_MODULE=config.settings_all`. Se regeneró `url_registry.json`
con 2807 nombres (tres rutas nuevas). El chequeo documental halló 0 referencias
rotas.

La regresión acotada de integración pasó con 1002 pruebas en 430,02 segundos,
en ejecución serial y con 23 advertencias existentes. No es una repetición de
la suite histórica de 1044 pruebas ni evidencia de CI. Los destinos exactos fueron:

```text
src/backends/sisoc_core/insumos/tests/
src/backends/sisoc_core/tests/test_web_session_readiness.py
src/backends/sisoc_core/tests/test_web_session_api.py
src/backends/sisoc_core/tests/test_urls_pr1400_fixes.py
src/backends/kernel/tests/test_urls_no_500.py
```

XView dio RED en las nuevas rutas (HEAD interno devolvía
`X-View`/200 antes de resolver el API) y GREEN después de una excepción acotada
a la ruta literal de alta y IDs numéricos de edición/eliminación. La regresión
independiente verificó esos HEADs, autenticación anónima/denegada y
compatibilidad del middleware. La verificación independiente del esquema real
y su correspondencia con respuestas multipart pasó cuatro pruebas dirigidas.
Los recorridos de los formularios React, el diff visual completo y la aceptación
humana siguen pendientes; este registro no acredita esas etapas.

Las pruebas observadas usaron imagen local aislada, sin red, SQLite sintético y
almacenamiento temporal; no se usaron datos ni proveedores reales.
