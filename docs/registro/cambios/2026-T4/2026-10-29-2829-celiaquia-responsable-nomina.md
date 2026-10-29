# Cambio: aprobación del responsable en la nómina de Celiaquía (#2829)

## Alcance y causa

La nómina ya filtraba beneficiarios `APROBADO` + `MATCH`, pero resolvía sus
responsables desde vínculos familiares globales, sin limitar el expediente ni
verificar la aprobación técnica del responsable. Ahora se filtran los vínculos
por pertenencia al expediente antes de elegir el responsable y se excluye al
dependiente si ese responsable no está aprobado.

Guía canónica: `docs/implementaciones/celiaquia_nomina_aprobados.md`.
Código: `src/backends/celiaquia/celiaquia/services/padron_final_service/impl.py`.

## Compatibilidad y límites

Se conserva el criterio Sintys del cruce: `MATCH` pertenece al dependiente,
no al responsable puro. No hay migraciones, escrituras de datos, dependencias,
cambios de permisos ni cambios del helper familiar compartido. Se conserva la
selección alfabética ante responsables múltiples dentro del expediente.
La consulta de disponibilidad usa las mismas reglas que la exportación.
No se modifica el cruce ni la asignación de cupos, ni se revalida el archivo
Sintys al descargar.

## Verificación

- Base: 13 tests de exportación aprobados.
- RED: 8 fallos y 1 éxito en los nuevos casos de aprobación y vínculos externos,
  antes de modificar el servicio.
- GREEN: 25 tests de exportación y flujo completo aprobados. Incluye cruce real
  con archivos sintéticos con/sin responsable en Sintys, aunque el hijo sí figure.
- Suite de Celiaquía: 632 tests aprobados; cobertura del servicio completo 95%.
- Ejecución con la imagen local `sisoc-2789-django:latest`, `--network none`,
  SQLite sintético y sin acceder a bases o proveedores reales.
- Black en modo check: los tres archivos Python quedan sin cambios.
- Pylint de los tres archivos: 10/10. Validación de rutas de documentación:
  86 documentos vigentes, sin referencias obsoletas ni rotas.
- Sin verificación en navegador ni aceptación humana: este worktree no tiene
  entorno de aplicación configurado. Se comprobó el endpoint con el cliente
  Django y se leyó el XLSX generado en pruebas, sin modificar templates o CSS.
- CI, aceptación humana, merge y despliegue son estados independientes y no
  quedan acreditados por estas pruebas locales.

Rollback: revertir el cambio del servicio y sus pruebas; no requiere restaurar
datos ni esquema.
