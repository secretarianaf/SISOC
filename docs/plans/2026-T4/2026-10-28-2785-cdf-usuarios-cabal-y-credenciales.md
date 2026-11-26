# CDF-E: generación de usuarios, credenciales y CABAL

E2: planificación basada en fuente local; no implementación, secretos reales,
API sensible publicada o validación runtime. D1 mantiene autorización existente;
no autoriza serializar User/Profile ni ampliar exposición de contraseñas.

## Generación de usuarios: circuito y resultado

Ruta cdf_centro_generar_usuario: centros/<pk>/generar-usuario/. Permiso URL
view_centro, login y puede_generar_usuario_cdf: delegación, territorio y cupo.
Form: first_name/last_name requeridos, strip, máximo150; email requerido/strip;
grupo fijo no editable. Primer acceso del centro precarga referente; cualquier
AccesoCDF histórico evita esa precarga. Cupo visible, cancelar a centro_detail.

Servicio compartido valida grupo/delegación/límite/email y crea User activo/staff,
grupo y vínculo AccesoCDF transaccionalmente. Luego intenta email best-effort:
fallo no revierte creación. Repetir POST puede crear otro usuario si hay cupo;
no reintentar por pérdida de respuesta ni prometer idempotencia no implementada.

ValidationError retorna Form con errores globales. Éxito renderiza resultado en
respuesta POST, no redirect: username/email/contraseña temporal readonly, aviso
email enviado o fallo con entrega segura, Generar otro si queda cupo. El resultado
interno user/password/email_enviado no es un DTO público existente.

Ficha centro también muestra credenciales bajo puede_ver_usuarios_cdf; superusuario
ve registros, otros solo acceso propio activo. Poder generar no concede ese panel.
Las condiciones se deben conservar por separado, no unificar creador/lector.

Ciclo compartido de temporal: generación marca cambio obligatorio/expiración,
guarda plaintext y limpia tokens; cambio/reset limpian temporal y flags. Expirar
no prueba borrado automático del plaintext. No modificar almacenamiento ni ciclo
compartido dentro de esta migración.

## Decisión resuelta: CR1 elegida, CR2 descartada

| Alternativa | Alcance y beneficio | Riesgo o costo |
|---|---|---|
| CR1 — Proyección privada mínima para React (recomendación del agente) | Conservar resultado y panel actuales mediante contratos sensibles separados: resultado de creación para actor autorizado y lectura de ficha con su propio predicado/filtrado. Solo campos necesarios; sin serializar User/Profile completos | Se transporta una credencial en una nueva representación. Exige controles por request, no-store, exclusión de logs/telemetría/contexto global/cache persistente/URL/almacenamiento navegador y pruebas de fuga/revocación. No elimina exposición ya existente en servidor/pantalla |
| CR2 — No mostrar contraseña en React y definir otro mecanismo de entrega | Evita transportar/exhibir ese secreto en la UI nueva | Cambia diseño y operación actuales, especialmente si email falla. Necesita definir entrega/recuperación antes de activar; email solo no es sustituto equivalente |

El responsable eligió «cr1» el 2026-10-28. Esto autoriza planificar el contrato
sensible acotado, no implementarlo ni
ampliar actores/filas, modificar permisos o persistencia. La credencial necesaria
para renderizar vive solo en memoria efímera del circuito; no exigir borrado seguro
de memoria JavaScript como garantía imposible. No guardar en cliente para soportar
refresh ni repetir creación al recargar. Comportamiento de navegación, revocación y
reingreso se concreta con pruebas futuras, sin atribuir semántica de uso único.

La elección es explícita, no inferida de M2/D1. CR2 habría requerido
excepción expresa a apariencia/operación idénticas. Sin datos o secretos reales
para capturas: fixtures totalmente sintéticas y evidencias de acceso restringido.

## CABAL: contrato fuente de carga local

CABAL aquí no es consulta a proveedor: XLSX/openpyxl y persistencia local.
Email de credenciales sí es integración externa; futuro test con backend simulado.

| Ruta nombrada | Fuente/resultado |
|---|---|
| informecabal_list | GET historia,10 por página, -fecha_subida |
| informecabal_preview | POST multipart file/page;25 filas, no persiste; paginar reenvía archivo |
| informecabal_process | POST multipart file/force; nombre repetido409 duplicate_name:true; confirmación manual force=true |
| informecabal_archivo_detail | GET archivo y registros por id |
| informecabal_registro_detail | GET archivo/resumen total |
| informecabal_reprocess_center | POST codigo strip; reasigna no coincidentes en todos los archivos afectados, no solo archivo actual |
| informecabal_archivo_centro_detail | GET archivo/centro;50 por página, fila_numero |

Login + view_centro, CSRF en mutaciones; D1 conserva controles, no inventar owner
por centro que estas vistas no comprueban. Input XLSX/FormData y modal actuales,
no Form Django nuevo, staging/job/token o servicio externo por intuición.

Preview:14 encabezados en orden, hoja activa/data_only; NroComercio string strip
contra Centro.codigo. Respuesta ok/rows(fila,no_coincidente,data)/not_matching/total.
Proceso atomic crea archivo y todas las filas, incluidas no coincidentes, bulk2000;
válida significa coincidencia de centro, no validación financiera completa.
Numérico/fecha inválidos pueden quedar None. Carga completa en memoria, sin
prometer streaming/límite seguro o rollback del archivo físico por transacción DB.

Falta archivo400texto; formato400JSON genérico; inesperado500. Preview convierte
page a int fuera del try: no declarar todos los errores JSON homogéneos. Proceso
éxito archivo_id/totales y message.success; JS recarga historia tras800ms.
Reproceso bloquea pendientes por código y actualiza contadores multiarchivo;
repetido sin pendientes devuelve0. UI muestra procesados/impactados/desglose.

## Evidencias futuras, sin ejecución

Usuarios: primer/siguiente Form, histórico inactivo, inválidos, delegación/territorio/
cupo/grupo, email éxito/fallo sin rollback, Generar otro, panel propio/superusuario/
generador sin panel; distinguir cambio/reset/expiración, refresh y POST repetido.
Si CR1: positivos y negativos por representación, no secretos en respuestas de
actores no habilitados, cachés/logs/telemetría/URLs/client storage; no datos reales.

CABAL: historia vacía/paginada, modal/preview25, headers/archivo dañado/faltante,
no coincidencia, duplicado cancelar/forzar, éxito/400/409/500/red, detalles/página50,
reproceso vacío/desconocido/cero/multiarchivo/repetido, CSRF y política D1.
Referencia/candidato/diff desktop/móvil, foco/teclado, estados/avisos/retornos y
comparación acumulada. Capturas, fixtures y aceptación siguen pendientes.

## Fuente y límite

Prefijo src/backends/cdf/centrodefamilia/:
views/generar_usuario.py:26–100; forms_generar_usuario.py:4–34; access.py:56–90;
templates/centros/usuario_cdf_generado.html:17–63; views/centro.py:315–322,394–440;
templates/centros/centro_detail.html:450–496; urls.py:186–236;
views/informecabal.py:47–51; services/informe_cabal_service/impl.py:14–203;
services/informe_cabal_reprocess/impl.py:13–59;
static/custom/js/informecabal.js:146–188,234–300.
Compartido: src/backends/kernel/users/services_generate_user.py:205–262;
src/backends/kernel/users/services_auth.py:111–198.

CodeGraph sincronizado y exploración estática; padre contrastó resultado POST y
ambos templates de credenciales. Estos archivos nuevos no se contrastaron con
snapshot congelado: no atribuir ese SHA a esta evidencia. Sin app, DB, email,
archivos reales, tests, navegador, capturas, CI, commit/push o despliegue.

- [Particiones CDF y D1](2026-10-28-2785-cdf-circuitos-y-alcance-autorizacion.md).
- [Participantes y asistencia](2026-10-28-2785-cdf-participantes-asistencia-m2.md).

Registro: [CR1 aceptada](../../registro/decisiones/2026-10-28-2785-cdf-credenciales-cr1.md).
