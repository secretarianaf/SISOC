# U08 y U06: regresión token y esquema compuesto de usuario

E2: definición estática, no reescritura PWA/SIIS, pruebas ejecutadas o nuevo API.
U08.01 Regresión identidad PWA/SIIS, perfilK del catálogo. U-CR1 ya aceptada;
no copiar contexto móvil amplio a proyección web ni reabrir transporte de secretos.

## U08: contratos a preservar separados de sesión web

Bajo /api/users/: loginPOST AllowAny; logoutPOST y meGET TokenAuthentication +
IsAuthenticated; password-change-requiredPOST autenticado; password-reset/request
/confirmPOST AllowAny con reglas propias; siis/admin-tokenPOST APIkey+credenciales
admin; siisPOST APIkey+X-SIIS-Admin-Token. AllowAny no significa sin controles de dominio.
No cambiar Token por cookie, logoutToken no es logout sesiónweb.

Login body noobjeto400; app=siis deriva contratoSIIS, otro app explícito400.
DataCalle/Inspecciones/territorial pueden autenticar sin depender éxitoComedores;
rama token/token_type=Token/user_id/username; Espacios conserva rama propia.
me pide contribución interna /interno/espacios/contexto/; caída mantiene identidad,
defaults y espacios_comunitarios_disponibleFalse, no pierde toda identidad.

Raíz read-only actual id,username,email,first_name,last_name,is_superuser,is_staff,
groups,profile,scope,pwa,roles,permissions,espacios_comunitarios_disponible.
Profile scope/flags/roles y pwa fallback is_pwa_user,roles,comedores_representados,
comedor_operador_id,tipo_asociacion,organizaciones_ids,read_only,must_change_password.
No temporal. Nueva web necesita mínimos por consumidor, no exportar todo Profile.
Logout elimina token/registra evento. Consumidores externos fuera checkout no
verificados: tests fuentes no acreditan integración viva ni frontendReact externo.

## SIIS: contrato externo inalterado

Authorization Api-Key y tokenadmin firmado3600s. Cuenta activa/acceso_siis;
admin además AddUser, revalidación al resolver token. Alta acepta solo username,
password,first_name,last_name,email,dni; rechaza extras, validadoresDjango, password
write-only, DNI7–8normalizado. Resultado id/username/first_name/last_name/email/dni/
acceso_siis; nunca password. Duplicado409 account_exists, no actualiza existente;
otros400/401/403/429 segúnfuente. Nuevo no staff/superusuario, auditoría actor/sourceSIIS.
No llamar SIIS real ni inspeccionar APIkeys bajo E2.

## U06: secciones y campos Comedores

Permisos sección role_usuarios_seccion_mobile_comedores, _territorial_comedor,
_equipos_tecnicos y propios DataCalle/Inspecciones/admin. Actor ausente en helper
es uso interno irrestricto, no valor para requests API. Servidor deshabilita campos
no autorizados, no solo ocultarUI; superusuario todas segúnfuente.

Mobile: es_representante_pwa,es_coordinador_equipo_tecnico_pwa,
duplas_coordinador_pwa,comedores_adicionales_coordinador_pwa,
puede_gestionar_rendiciones_mobile,tipo_asociacion_pwa,organizaciones_pwa,
comedores_pwa,puede_gestionar_colaboradores_pwa,puede_gestionar_usuarios_pwa,
puede_gestionar_nomina_pwa,puede_gestionar_prestaciones_mensuales_pwa. Los cuatro
últimos mapean pwa.manage_colaboradores_pwa/manage_usuarios_pwa/manage_nomina_pwa/
manage_prestaciones_mensuales_pwa. No nuevos grants por checkboxReact.

Territorial: es_territorial_comedor/provincias_territorial ordennombre, activo≥1;
incompatible representante/coordinadorPWA, desactivado limpia selección efectiva.
Equipo técnico es_coordinador/duplas_asignadas, activo requieredupla.

Mobile conserva selecciones Profile.configuracion_mobile al suspender y restaura
iniciales en edición, normaliza permisos al desactivar/coordinadorread-only. No
perder configuración suspendida ni recrear operadoractivo como representante.
Passwordeditvacía preserva hash; nueva cambia/requierecambio/limpiatemporal. Alta
representante/coordinador genera temporal12/no staff; editar no genera otra por rutina.
Operación compuesta y bloqueo/dueño ya definidos, no separar en submits.

U-CR1 reemplaza mensaje con secreto por proyección privada separada sin alterar
alerta/campo. Comedores edición actual ChangeUser+scope, temporal sesiónporusuario
luegoProfile, contextooperador/creados. No plantillaHTML como contratoReact nuevo.

## Casos propuestos y dependencias

Token válido-inválido/logout; me con Comedores disponible-caído, appsiis/otro,
tokenadminvencido/revocado, altaextracampo/duplicado, temporal ausente en contexto.
Secciónnoautorizada+POSTforjado, suspendermobile/restaurar, operador/coordinador,
passwordvacía/nueva, organización extiende comedoresfuturos, iniciales/errores y
scope. Caso a través interfazpública, sintéticos, sin calls externas o email.

Capturas web porsección/rol/estado/error desktop/móvil/foco, referencia/candidato/
diff acumulado; no capturas ni aceptaciónejecutadas. DU01 equipos/asignaciones es
siguiente dependencia, no ticket nuevo ni prioridad de negocio decidida.

## Fuente

src/backends/sisoc_core/usuarios/api_urls.py:14–39;
api_views.py:54–56,98–160,217–368; api_serializers.py:20–115;
siis_api_views.py:45–55,109–210; services_siis.py:24–180.
Estos cinco archivosapi/views/serializers/siis contrastados con
59a8f797688c9e762d5a4e9eaa187698ffade8aa normalizandoCRLF.
src/backends/kernel/users/secciones_usuario.py:26–94; form_sections.py:195–214;
src/backends/comedores/pwa/user_forms.py:46–75,140–273,315–425,486–542,631–647,
677–737,889–956; pwa/user_admin_views.py:35–153; Forms ya contrastados previamente,
otros checkout. Padre leyó exposición serializers; CodeGraphsync, sin runtime/tests.

- [ABM y U-CR1](2026-10-28-2785-usuarios-grupos-y-credenciales.md).
- [U04/U05](2026-10-28-2785-usuarios-lotes-importacion-m2.md).
