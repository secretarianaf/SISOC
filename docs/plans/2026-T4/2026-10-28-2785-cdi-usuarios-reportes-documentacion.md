# CDI01/CDI08: usuarios, reportes y decisión de descarga documental

E2: planificación basada en fuente, sin implementación, serving verificado o
conexión remota. Catálogo CDI01–CDI09, no CDI10 ni nuevo ABMcatálogos inventado.
CDI-A2/A3 ya aceptadas, no se reabren; no incluyen serving de documentación.

## CDI01.01/02/03: consulta, gestión y regresión de integración

GenerarUsuarioCDIForm: first_name/last_name≤150, email, DNI string≤16 solo dígitos
mínimo6, CUIL validado; identidad RENAPER protegida/email editable. No reutilizar
regla DNI7/8 del trabajador. Resultado/panel se rigen por CDI-CR1.

centrodeinfancia_usuario_estado soloPOST: ViewCentro URL + vetoauditor +
puede_administrar_usuarios_cdi, acceso pertenece centroURL. Body accion/motivo:
activo→suspendido requiere motivo; suspendido→activo no; activo/suspendido→baja
requiere motivo. Acción/motivo inválidos, propia cuenta, responsable u origen
incorrecto rechazan. Atomic bloqueaAcceso y actualiza estado/motivo/fecha_baja;
no borrar User global ni prometer revocación de todas sus sesiones/tokens.
Mensaje «Usuario «…» suspendido/reactivado/dado de baja.»; errores concatenados;
retorno fichaCDI#usuarios. Repetición origen inválido error, no replay automático.

simepi_egp_generar_usuario es RedirectView temporal a usuario_crear, solo actor con
delegaciónEGP. Dependencia M2 del ABM general usuarios; no nuevo FormEGP ni bypass
de permisos del destino. Pantallas/mensajes/acciones de usuario general requieren
su propio contrato, no copiar reglas CDI para todos los usuarios.

## CDI08.01/02: reportes y tres exportaciones distintas

### CSV centros

centrodeinfancia_exportar usa OR ViewCentro/role_exportar_a_csv en fuente, no AND.
Mismo scope/advancedfilters/busqueda nombre-organización/ordennombre del listado,
queryset completo no página10. Preferencia columnas centrodeinfancia_list y
whitelist export nombre/organización/provincia/departamento/municipio/localidad/
calle/número/teléfono/nombre-apellido referente; tiene_nómina UI no implica columna
export. Mantener backend CSV, no descargar datos masivos para generarlo en React.

### Pantalla resumen y XLSX

centrodeinfancia_reportes/_reportes_descargar: auth.role_reportes_cdi, no globalCSV.
Provincia dentro del alcance, filtro solo reduce. Resumen coincide primera hoja
seccion/detalle/cantidad. Variante completo/reducido; completo solo superusuario,
SIMEPIAdministrador o EquipoNacional. Query inválida/no permitida cae a disponible
por defecto, no amplía acceso. Workbook backend write_only hojas Resumen/CDI/
Trabajadores/Nomina/Diccionario/Metadatos; columnas/indicadoresRENAPER y filas reales
por variante. React solo resumen/selectores/descarga, no duplicar cálculos/formulas.
XLSX private,no-store/nocache con nombrefecha/variante.

### PDF provincial de niños

centrodeinfancia_nomina_ninos_pdf: login + regla propia, no wrapperreportes.
Superusuario provinciaexistente (inválida400texto); EGP requiere alcanceprovincial
completo y provincia dentro de ese conjunto, no municipio/localidad parcial ni
ViewCentro genérico. Fallo generación503texto. PDF attachment porprovincia,
private/no-store/nocache. Mantener selector modal actual, no PDFde páginaactual o
XLSX por sustitución. Uso de estadoRENAPER no demuestra consulta externa por export;
no añadir llamadas nuevas.

## Documentación CDI06: evidencia local de serving

Template usa FileField.url; modelo upload_to documentacion/. Settings MEDIA_URL
/media/, MEDIA_ROOT media, default FileSystemStorage en ambas ramas revisadas;
urls_dev helper sirve media según configuración desarrollo. Receta versionada
Nginx tiene bloqueos explícitos PAS/Inspecciones y alias general /media/ con try_files,
sin guard documentacion. Si se aplica tal cual, sirve ese prefijo directamente.

No se inspeccionó servidor/configuración efectiva, deploy, archivo real ni URL.
No afirmar acceso público actual confirmado ni protección por permiso de ficha.
No hallado X-Accel/serving privado CDI en ubicaciones inspeccionadas. documentacion/
puede tener consumidores compartidos, cuyo inventario es prerrequisito de cambios.

## Decisión resuelta: CDI-F2 elegida, CDI-F1 descartada

| Alternativa | Alcance/beneficio | Costo/riesgo |
|---|---|---|
| CDI-F1 — Conservar enlace y serving actuales | Migración mantiene enlace directo y aspecto sin tocar entrega de archivos; hallazgo separado | Menor alcance, pero puede conservar descarga sin controles de ficha según serving efectivo. No declarar privado o seguro |
| CDI-F2 — Planificar descarga autenticada y cierre del acceso directo de esos adjuntos (recomendación) | Contrato backend por intervención/scope y bytes servidos bajo autorización, mismo botón/aspecto. Coordinar legacy/API/storage/serving para que enlace antiguo no eluda control | Amplía seguridad/entorno y cambia acceso directo/anónimo; requiere inventario de consumidores de prefijo, compatibilidad de archivos existentes, pruebas y autorización futura del entorno. Un endpoint nuevo solo no basta si alias directo sigue abierto |

El responsable eligió «CDI-F2» el 2026-10-28. La decisión no permite bloquear
globalmente documentacion/ sin inventario ni mover/borrar
archivos. No nuevos grants, storage/proveedor por rutina o despliegue autorizado.
Selección explícita independiente de A3: A3 cubre diez mutaciones nombradas, no serving.

## Casos y evidencia futura

Usuarios: propio/responsable/motivo/origenrepetido/objetoajeno/auditor/excepciones,
return#usuarios, EGPredirect y permiso destino. Reportes: actor/variante manipulado/
provinciaajena, filtros-columnas/CSVcompleto vs página, XLSXhojas/diccionario/filas,
PDFalcancecompleto/400/403/503, modal/feedbackdescarga. Sintéticos, sin capturas.

Archivos: autorizado/sesión vencida/objetoajeno, enlace histórico/anónimo directo,
cache/cabeceras y consumidores compartidos según opción. Comparar aspecto y descarga
real autorizada, no solo enlace visible. Sin archivos personales ni credenciales
reales en evidencias. Entorno/integración requieren autorización futura explícita.

## Fuente

Prefijo src/backends/cdi/centrodeinfancia/: forms_generar_usuario.py:8–68;
views_usuario_cdi.py:178–208; services_accesos_cdi.py:18–72;
views_usuario_egp.py:7–15; urls.py:62–96; views_export.py:28–180;
views_reportes.py:23–83; services_reportes.py:334–338,551–564,620–700.
Views_reportes/export/accesos/usuario_cdi contrastados con
59a8f797688c9e762d5a4e9eaa187698ffade8aa; otros archivos/config source checkout:
src/backends/config/settings.py:272–273,729–755; urls_dev.py:20;
docs/operacion/nginx/sisoc-produccion.conf:55–67. Parent spot-check Nginx y wrappers
exportaciones. CodeGraph sync, sin app/tests/DB/servidor/navegador/remoto o deploy.

- [Intervenciones y archivos](2026-10-28-2785-cdi-intervenciones-observaciones-m2.md).
- [CDI-CR1](../../registro/decisiones/2026-10-28-2785-cdi-credenciales-cr1.md).
- [CDI-A3](../../registro/decisiones/2026-10-28-2785-cdi-auditoria-a3.md).

Registro: [CDI-F2 aceptada](../../registro/decisiones/2026-10-28-2785-cdi-documentacion-f2.md).
