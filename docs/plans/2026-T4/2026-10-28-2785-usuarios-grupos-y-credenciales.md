# U06/U07: usuarios y grupos de aplicación, credenciales y operación compuesta

E2: planificación estática. /usuarios/ y /grupos/ son aplicación y deben migrar;
no Django Admin/Unfold #2789, aunque Forms se llamen admin_forms. U01–03 identidad
no se reabren. IDs U06.01 consulta, .02 gestión/estado, .03 export; U07.01 consulta,
.02 asignaciones. U04/U05 jobs/import y U08PWA/SIIS mantienen contratos separados.

## Rutas y alcance

usuarios ViewUser25/página; usuario_crear AddUser; usuario_editar ChangeUser;
usuario_borrar y usuario_activar DeleteUser. usuarios_exportar ViewUser Y rolCSV.
grupo listado/crear/editar View/Add/ChangeGroup; export ViewGroup Y rolCSV. No ruta
usuario_detalle individual identificada; edición sirve consulta/operación.
AdminRequiredMixin exige sesión/permisos, no staff por nombre, superusuario bypass.

Listado puede ser visible global por roles nacionales, pero editar/estado usa
get_usuarios_en_alcance y delegación, no queryset de listado. No-super sin delegación
solo propio; ramas grupos/roles/subconjuntos/identidadesCDI/DataCalle deben conservarse.
No suponer permiso para administrar cada fila que se puede listar.

## Operación compuesta core/Comedores

UserDomainOperationMixin puede reenviar GETcompleto a Comedores por secciones,
valida objeto antes y dueño revalida. FalloGET5xx permite Formindependiente con
warning sin borrar accesos. POST preserva body antes de leer y si requiere espacios
reenvía operación completa, no guardado parcial core. React debe proyectar contrato
compuesto/dueño sin dos submits identidad+accesos, sin reintento ante timeout.
No imports cruzados ni endpoint HTML tomado como schemaForm/API.

## Form y persistencia

IdentityFieldsForm: username,email,password,dni,acceso_web,acceso_siis,cuil,
tipo_usuario,groups,user_permissions,es_usuario_provincial,provincia,
territorial_scopes,last_name,first_name,rol. IdentityAdminForm agrega secciones
DataCalle/Inspecciones/delegación/scope. Detalle final Comedores pendiente propio.

Password requerida alta/opcional edición, initial siemprevacía, no devolver hash
ni passwordreal. Email opcional en varianteindependiente, no reglaCDI. Grupos/roles/
secciones limitados actor, servidor trata POST manipulado según Form; disabledUI
no autorización. En edición omitido no revoca: disabled/no-required salvopassword,
distinguir ausente de limpieza explícita y múltiplevacío. Inspector/entrevistador
soloapp alta acceso_webFalse; SIMEPIEGP/provincia y coordinadorDataCalle propios.
user_permissions representa auth.role_* actuales, no crear roles por serialización.

Form.save exige commitTrue, atomic/lockUser y revalida dueño si cambian asignaciones.
Con passwordvacía preserva hash. Identidad/permisos/Profile/scopes solochanged_data,
limpia cachéspermiso. Passwordnueva/creación marca cambioobligatorio/expiración y
limpia temporalplaintext/resetflag. No sustituir Profilecompleto con defaults.

Borrar desactiva is_activeFalse, mensaje «Usuario desactivado correctamente.»;
activarTrue «Usuario activado correctamente.», scopeadministrable→listado.
No harddelete ni promesa logoutglobal/revocacióntokens no mostrada. Altaindependiente
→listado «Usuario creado correctamente.»; branchmobile passwordgenerada→editar.
Editar→listado, erroresForm conservados, passwordeditada limpia temporalsesión.
EGPlegacyredirige usuario_crear, dependenciaM2 para no dejar FormDjango residual.

## Grupos: propagación de permisos

GroupForm name requerido/strip/único case-insensitive; permissions múltiple opcional
Permission orden app_label/name, widget FilteredSelectMultiple. Modifica permisos
de todos los miembros, no equivale a grupos_asignables/roles_asignables Profile.
Create/edit permisos propios→grupos con «Grupo creado/actualizado correctamente.».
J2Select2 no resuelve este widget; conservar interfaz, no imponer diseño MUI genérico.

## Decisión resuelta: U-CR1 elegida, U-CR2 descartada

Alta mobile actual coloca contraseña generada dentro de message.success antes de
redirect editar. Edición toma temporal de sesión poruser_id y fallbackProfile.
Comedores replica presentación con contextoaccesos. Autoridad lectura es ChangeUser
+scopeadministrable, distinta de CDI/CDF. Los avisos M2 genéricos no deben transportar
secretos. CR1 y CDI-CR1 no constituyen aprobación general del nuevo contrato.

| Alternativa | Beneficio | Costo/riesgo |
|---|---|---|
| U-CR1 — Proyección sensible mínima separada (recomendación) | Conservar alerta/campo actuales mediante resultado privado de creación y lectura de edición autorizada por reglasABM. Separar credencial de avisos genéricos/contexto global; no-store/sin logs-URL-storage-caché persistente; sin User/Profile completo | Nuevo transporte sensible compuesto core/Comedores exige pruebas por actor/objeto/dueño y retorno. No conceder ChangeUser para evitar error tras redirect ni copiar scopeCDI |
| U-CR2 — Retirar temporal visible y definir otra entrega | Reduce exposición en UI nueva | Cambia diseño/operación y exige resolver entrega/recuperación cuando no hay email; no sustituye por envío supuesto |

El responsable eligió «U-CR1» el 2026-10-28. Mantener ausencia/cambio/expiración
fuente, no semántica usoúnico nueva,
replay creación o cambioalmacenamientoBackend. Actor soloAdd no obtiene acceso de
edición sinChange; visibilidad del resultado se limita a operación propia ya
permitida, no endpointgeneral deconsulta. No bypass para cumplir navegación.
Solo planificación, no secreto real, implementación o envíoemail autorizado.

## Casos y brechas

Viewglobal/ChangefueraScope, AddsinChange/redirectmobile, delegación manipulada,
omitir vs clear, passwordvacía/nueva, coreindependiente/Comedores disponible-caído,
POSTincierto sin retry, estado repetido, EGPredirect, grupopropagación, secretos por
actor/scope/dueño/limpieza. Desktop/móvil/foco/Formerrores/feedback/retorno y diff
acumulado, sintéticos, ninguno ejecutado. ExportCSVcampos/U04/U05/jobs/import,
formscore/Comedores esquema completo y U08compatibilidad requieren profundización.

## Fuente

src/backends/sisoc_core/usuarios/urls.py:59–167; views.py:79–229,401–436;
src/backends/kernel/users/view_mixins.py:6–26; services.py:90–169;
identity_fields.py:9–106; admin_forms.py:28–221; form_sections.py:894–922;
src/backends/comedores/pwa/user_admin_views.py:47–58,90–147.
Vistascore/Formsidentity-admin/services/formsections y vistasComedores contrastados
con59a8f797688c9e762d5a4e9eaa187698ffade8aa; mixin/URLs evidencia checkout adicional.
Padre contrastó mensajealta, redirect y ediciónscope/temporal. CodeGraph sync,
sin app/tests/DB/navegador/remoto/CI/commit/push/deploy.

- [Identidad y remediaciones](2026-10-27-2788-identidad-remediaciones-m2.md).
- [Catálogo](2026-10-27-2785-entregas-por-flujo.json).

Registro: [U-CR1 aceptada](../../registro/decisiones/2026-10-28-2785-usuarios-credenciales-u-cr1.md).
